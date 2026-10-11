"""Bounded image-only Codex CLI policy; it never dispatches bench actions."""

import contextlib
import hashlib
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import agent_bench
import order_protocol as protocol

BASE = Path(__file__).resolve().parent
TIMEOUT_S = 100
MAX_TRACE_BYTES = 1024 * 1024
MAX_RESULT_BYTES = 8192
EXPECTED_CLI = "codex-cli 0.147.0"


class PolicyUnavailable(RuntimeError):
    """Safe failure code; provider output and credentials stay private."""


class PolicyCancelled(PolicyUnavailable):
    pass


def preflight():
    executable = shutil.which("codex")
    if not executable:
        return {"available": False, "reason": "Codex CLI is not installed", "provider": "codex_cli"}
    try:
        version = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=5, check=False)
        auth = subprocess.run([executable, "login", "status"], capture_output=True, text=True, timeout=5, check=False)
        cli_version = version.stdout.strip()
        available = version.returncode == auth.returncode == 0 and cli_version == EXPECTED_CLI
        return {"available": available, "provider": "codex_cli", "cli_version": cli_version,
                "auth_mode": "saved_cli_authentication", "reason": None if available else "CLI version or sign-in is unavailable"}
    except (OSError, subprocess.TimeoutExpired):
        return {"available": False, "reason": "Codex CLI readiness could not be checked", "provider": "codex_cli"}


def validate_action(value):
    protocol.fields(value, ("action", "target_x", "target_y", "intent"), "model action")
    action = value["action"]
    if action not in agent_bench.ACTIONS | {"stop"} or not isinstance(value["intent"], str) or not 1 <= len(value["intent"].strip()) <= 500:
        raise PolicyUnavailable("model_action_schema")
    if action == "move":
        x, y = protocol.finite(value["target_x"]), protocol.finite(value["target_y"])
        if not -.32 <= x <= .18 or not -.15 <= y <= .15:
            raise PolicyUnavailable("model_target_outside_bounds")
    elif value["target_x"] is not None or value["target_y"] is not None:
        raise PolicyUnavailable("nonmotion_targets_must_be_null")
    return value


def terminate(process):
    if process.poll() is not None:
        return
    with contextlib.suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=3)


def usage_from_events(content):
    reported = None
    for line in content.decode("utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except (ValueError, TypeError):
            continue
        if not isinstance(event, dict):
            continue
        item = event.get("item", {})
        if isinstance(item, dict) and item.get("type") == "error":
            message = item.get("message", "")
            known = ("Code Mode is unavailable because code-mode host is disabled.",
                     "Skill descriptions were shortened to fit the skills context budget.")
            if not isinstance(message, str) or not message.startswith(known):
                raise PolicyUnavailable("codex_reported_error")
        elif isinstance(item, dict) and item.get("type") not in {None, "agent_message", "reasoning"}:
            raise PolicyUnavailable("unexpected_model_tool_use")
        if event.get("type") == "turn.completed":
            data = event.get("usage", {})
            if isinstance(data, dict) and all(type(data.get(k)) is int and 0 <= data[k] <= 1000000 for k in ("input_tokens", "output_tokens")):
                reported = {k: data[k] for k in ("input_tokens", "output_tokens", "cached_input_tokens") if type(data.get(k)) is int}
    return reported


def decide(challenge, history, call_dir, cancel_event):
    root = protocol.directory(call_dir, create=True)
    if any(path.name != "reservation.json" for path in root.iterdir()):
        raise PolicyUnavailable("model_call_directory_already_used")
    packet = challenge["observation"]
    image = protocol.read_bytes(Path(challenge["image_path"]), maximum=1024 * 1024)
    if protocol.sha(image) != packet["image_sha256"]:
        raise PolicyUnavailable("model_image_digest_changed")
    readiness = preflight()
    if not readiness["available"]:
        raise PolicyUnavailable("codex_cli_unavailable")
    if cancel_event.is_set():
        raise PolicyCancelled("operator_pause_requested")
    data = agent_bench.public_response({"current": {"job_id": packet["job_id"], "phase": packet["phase"],
             "generation": packet["generation"], "calibration": packet["calibration"], "task": challenge["task"]},
             "recent_actions": history[-12:]})
    prompt = "Choose one next action from this current attached image and task data.\n" + protocol.encoded(data).decode()
    instructions = protocol.read_bytes(BASE / "codex-policy.md")
    schema = protocol.read_bytes(BASE / "codex-action.schema.json")
    for name, content in (("input.png", image), ("instructions.md", instructions), ("schema.json", schema), ("prompt.txt", prompt.encode())):
        agent_bench.bench.body.create_file(root / name, content)
    request_sha = hashlib.sha256(prompt.encode() + image + instructions + schema).hexdigest()
    flags = ["--ignore-user-config", "--ignore-rules", "--ephemeral", "--skip-git-repo-check", "--sandbox", "read-only",
             "--disable", "shell_tool", "--disable", "unified_exec", "--disable", "hooks", "--disable", "multi_agent",
             "--disable", "apps", "--disable", "image_generation", "--disable", "view_image", "--disable", "code_mode_host",
             "-c", "tools.view_image=false", "-c", 'web_search="disabled"', "-c", "project_doc_max_bytes=0",
             "-c", "approval_policy=\"never\"", "-c", 'model_reasoning_effort="low"',
             "-c", "model_instructions_file=" + json.dumps(str(root / "instructions.md")),
             "--cd", str(root), "--image", str(root / "input.png"), "--output-schema", str(root / "schema.json"),
             "--output-last-message", str(root / "result.json"), "--json", "-"]
    executable = shutil.which("codex")
    environment = {k: v for k, v in os.environ.items() if not any(word in k.upper() for word in ("API_KEY", "TOKEN", "SECRET", "PASSWORD"))}
    metadata = {"provider": "codex_cli", "cli_version": readiness["cli_version"], "request_sha256": request_sha,
                "image_sha256": packet["image_sha256"], "started_at": time.time(), "usage": None}
    agent_bench.bench.body.create_file(root / "request.json", protocol.encoded({**metadata, "flags": flags, "tools_enabled": False}))
    started = time.monotonic()
    with (root / "events.jsonl").open("xb") as stdout, (root / "stderr.log").open("xb") as stderr:
        try:
            process = subprocess.Popen([executable, "exec", *flags], stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
                                       env=environment, start_new_session=True)
        except OSError as exc:
            raise PolicyUnavailable("codex_cli_launch_failed") from exc
        metadata["pid"] = process.pid
        try:
            process.stdin.write(prompt.encode())
            process.stdin.close()
            while process.poll() is None:
                if cancel_event.wait(.15):
                    raise PolicyCancelled("operator_pause_requested")
                if time.monotonic() - started > TIMEOUT_S:
                    raise PolicyUnavailable("model_call_timeout")
                if max((root / "events.jsonl").stat().st_size, (root / "stderr.log").stat().st_size) > MAX_TRACE_BYTES:
                    raise PolicyUnavailable("model_trace_exceeds_bound")
            if cancel_event.is_set():
                raise PolicyCancelled("operator_pause_requested")
            if process.returncode != 0:
                raise PolicyUnavailable("codex_cli_exit_" + str(process.returncode))
            content = protocol.read_bytes(root / "result.json", maximum=MAX_RESULT_BYTES)
            value = validate_action(protocol.decode(content))
            metadata["usage"] = usage_from_events(protocol.read_bytes(root / "events.jsonl", maximum=MAX_TRACE_BYTES))
        except (PolicyUnavailable, OSError, ValueError, TypeError, KeyError) as exc:
            terminate(process)
            metadata.update(outcome="cancelled" if isinstance(exc, PolicyCancelled) else "unavailable",
                            reason=str(exc) if isinstance(exc, PolicyUnavailable) else "invalid_or_unavailable_model_result")
            if isinstance(exc, PolicyUnavailable):
                raise
            raise PolicyUnavailable("invalid_or_unavailable_model_result") from exc
        finally:
            terminate(process)
            metadata.update(elapsed_s=time.monotonic() - started, process_exit_observed=process.poll() is not None,
                            exit_code=process.poll())
            protocol.persist(root / "outcome.json", metadata)
    metadata["outcome"] = "decision"
    protocol.persist(root / "outcome.json", metadata)
    return value, metadata
