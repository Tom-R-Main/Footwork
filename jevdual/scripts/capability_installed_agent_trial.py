"""One real Claude Code task through an installed, scoped Footwork MCP server.

No retries, relay, source product imports, permission changes or fixture writes.
The caller owns installation, permissions, fixture preparation and retirement.
Raw host prose is private; only the installed readonly adapter supplies a result.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import math
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

import psutil
from capability_clean_install import isolated_environment, source_commit
from capability_comparison_trial import SESSION_CAP, TIMEOUT, host_command, parse_transcript, prompt
from capability_host_trial import ax_document_text
from capability_restart_trial import _rows, _wait_no_worker

PROJECT = Path(__file__).resolve().parents[2]
TOOLS = [f"mcp__footwork__{name}" for name in ("bind", "observe", "act", "status", "report")]
PREFIX, VALUE = "Invoice report\n", "17.25 USD"
SCHEDULING_RESERVE_USD = 2.0
ISOLATION_KEYS = {
    "HOME",
    "XDG_CONFIG_HOME",
    "XDG_CACHE_HOME",
    "TMPDIR",
    "TMP",
    "TEMP",
    "BROWSER_USE_CONFIG_DIR",
    "PLAYWRIGHT_BROWSERS_PATH",
    "PYTHONNOUSERSITE",
    "ANONYMIZED_TELEMETRY",
    "BROWSER_USE_CLOUD_SYNC",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError("Qualification gate failed: " + message)


def write(path: Path, value: Any) -> None:
    with path.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
    path.chmod(0o600)


def installed_configuration(
    python: Path,
    scope_path: Path,
    journal: Path,
    host_path: Path,
    isolation_root: Path,
    audit: Path,
) -> tuple[dict, dict, dict]:
    """Check generated commands verbatim; add only public isolation overrides."""
    scope = json.loads(scope_path.read_text())
    config = json.loads(host_path.read_text())
    manifest = json.loads((host_path.parent / "run.json").read_text())
    require(set(config) == {"mcpServers"}, "unexpected host configuration")
    require(set(config["mcpServers"]) == {"footwork"}, "unexpected MCP server")
    server = config["mcpServers"]["footwork"]
    expected = [
        "-I",
        "-m",
        "jevdual.capability.cli",
        "server",
        "--scope",
        str(scope_path),
        "--journal",
        str(journal),
    ]
    require(set(server) == {"command", "args", "env"}, "unexpected server configuration")
    require(
        server["command"] == str(python) and server["args"] == expected,
        "server must directly use the installed generated command",
    )
    expected_env = {
        "PYTHONPATH": "",
        "PYTHONHOME": "",
        "PYTHONNOUSERSITE": "1",
        "ANONYMIZED_TELEMETRY": "false",
        "BROWSER_USE_CLOUD_SYNC": "false",
    }
    require(server["env"] == expected_env, "unexpected generated server environment")
    require(
        manifest["scope"] == str(scope_path)
        and manifest["host_config"] == str(host_path)
        and manifest["task"] == scope["task"],
        "generated task identity differs",
    )
    require(
        manifest["report_adapter"]
        == [
            str(python),
            "-I",
            "-m",
            "jevdual.capability.cli",
            "report",
            "--journal",
            str(journal),
            "--task",
            scope["task"],
        ],
        "report adapter must directly use the installed generated command",
    )
    require(
        manifest["report_schema"] == str(host_path.parent / "report-schema.json"),
        "unexpected report schema path",
    )
    schema = json.loads(Path(manifest["report_schema"]).read_text())
    env = isolated_environment(isolation_root)
    # Never serialize inherited PATH, authentication or any other ambient value.
    server["env"].update({key: env[key] for key in ISOLATION_KEYS})
    # Enumerate names only. MCP must not inherit ambient provider credentials;
    # the real agent host keeps its existing opaque authentication unchanged.
    server["env"].update({name: "" for name in os.environ if name.endswith(("_KEY", "_TOKEN", "_SECRET"))})
    server["env"]["FOOTWORK_RUNTIME_AUDIT_DIR"] = str(audit)
    return config, manifest, schema


def transcript_evidence(path: Path) -> tuple[dict, Any]:
    evidence = parse_transcript(path, TOOLS, ["footwork"])
    events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    init = next(
        (event for event in events if event.get("type") == "system" and event.get("subtype") == "init"), {}
    )
    # The schema finalizer is a host output mechanism, never an effect capability.
    offered = init.get("tools", [])
    evidence["schema_finalizer_offered"] = "StructuredOutput" in offered
    if sorted(offered) == sorted([*TOOLS, "StructuredOutput"]):
        evidence["valid_environment"] = init.get("model") == "claude-opus-5-5" and [
            server["name"] for server in init.get("mcp_servers", [])
        ] == ["footwork"]
    evidence["out_of_arm"] = [name for name in evidence["out_of_arm"] if name != "StructuredOutput"]
    evidence["effect_calls"] = [name for name in evidence["calls"] if name != "StructuredOutput"]
    result = next((event for event in reversed(events) if event.get("type") == "result"), {})
    claims = result.get("structured_output")
    evidence["structured_output_present"] = isinstance(claims, dict)
    evidence["budget"] = cost_evidence(evidence.get("cost_usd"))
    return evidence, claims


def cost_evidence(cost: Any) -> dict:
    """Unavailable or invalid accounting cannot qualify a bounded paid trial."""
    available = type(cost) in (int, float)
    finite = available and math.isfinite(cost)
    valid = finite and 0 <= cost <= SCHEDULING_RESERVE_USD
    return {
        "configured_softcap_usd": SESSION_CAP,
        "scheduling_reserve_usd": SCHEDULING_RESERVE_USD,
        "reported_cost_usd": cost if finite else None,
        "available": available,
        "finite": finite,
        "valid": valid,
    }


def run_host(command: list[str], task: str, root: Path, cwd: Path) -> tuple[int, bool]:
    """Host inherits opaque existing authentication; MCP receives separate overrides."""
    with (root / "transcript.jsonl").open("x") as out, (root / "host-stderr.log").open("x") as err:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=out,
            stderr=err,
            text=True,
            cwd=cwd,
            start_new_session=True,
        )
        timed_out = False
        try:
            process.communicate(task, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            timed_out = True
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGTERM)
            try:
                process.communicate(timeout=8)
            except subprocess.TimeoutExpired:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
        finally:
            # Retire only this owned host group, including any lingering server.
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGTERM)
        return process.returncode, timed_out


def validate_report(adapter: list[str], claims: Any, env: dict, cwd: Path, root: Path) -> dict:
    """Retain rejected claims and adapter output; never fall back to host prose."""
    write(root / "structured-output.json", claims)
    completed = subprocess.run(
        adapter,
        input=json.dumps(claims),
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    (root / "adapter-stdout.txt").write_text(completed.stdout)
    (root / "adapter-stderr.log").write_text(completed.stderr)
    write(root / "adapter-exit.json", {"returncode": completed.returncode})
    try:
        validated = json.loads(completed.stdout)
    except ValueError:
        validated = None
    write(root / "validated.json", validated)
    accepted = (
        completed.returncode == 0
        and isinstance(validated, dict)
        and validated.get("validation", {}).get("accepted") is True
        and validated.get("operation_completion") == "completed"
        and isinstance(validated.get("trusted_summary"), str)
    )
    if accepted:
        (root / "published.txt").write_text(validated["trusted_summary"] + "\n")
    return {"accepted": accepted, "returncode": completed.returncode, "validated": validated}


def runtime_evidence(audit: Path, python: Path, isolation_root: Path, journal: Path) -> dict:
    contexts = [json.loads(path.read_text()) for path in sorted(audit.glob("*.json"))]
    prefix = python.parent.parent
    failures = []
    for context in contexts:
        if (
            Path(context["prefix"]) != prefix
            or context["python"] != str(python)
            or context["home"] != str(isolation_root / "private-home")
            or not context["user_site_disabled"]
            or not context["browser_telemetry_disabled"]
            or not context["browser_cloud_sync_disabled"]
        ):
            failures.append("runtime isolation differs")
        origins = [path for paths in context["modules"].values() if paths for path in paths]
        if not origins or any(not Path(path).is_relative_to(prefix) for path in origins):
            failures.append("module outside installed prefix")
        if context["cua_library"] and not Path(context["cua_library"]).is_relative_to(prefix):
            failures.append("native library outside installed prefix")
    for role in ("server", "worker"):
        if not any(
            context["role"] == role
            and context["modules"].get("jevdual")
            and context["modules"].get("cua_driver")
            and context["modules"].get("ApplicationServices")
            and context["cua_library"]
            for context in contexts
        ):
            failures.append("loaded installed " + role + " audit missing")
    registrations = [
        json.loads(path.read_text())
        for path in Path(str(journal) + ".executions").glob("*/registration.json")
    ]
    if not registrations or not any(
        context["role"] == "worker" and context["pid"] == registration["pid"]
        for context in contexts
        for registration in registrations
    ):
        failures.append("worker audit does not match registration")
    return {"contexts": contexts, "registrations": registrations, "failures": failures}


def server_absent(contexts: list[dict]) -> bool:
    """A still-live audited PID conservatively fails, including possible PID reuse."""
    return all(not psutil.pid_exists(context["pid"]) for context in contexts if context["role"] == "server")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("python", "scope", "host-config", "journal", "isolation-root", "run-dir"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    root = args.run_dir.resolve()
    isolation = args.isolation_root.resolve()
    python = Path(os.path.abspath(args.python))  # Preserve venv executable symlink.
    scope_path, host_path, journal = args.scope.resolve(), args.host_config.resolve(), args.journal.resolve()
    for path in (root, isolation, scope_path, host_path, journal):
        if not path.is_relative_to(PROJECT / "output"):
            parser.error("all state must be in owned project output")
    if journal.exists() or Path(str(journal) + ".executions").exists():
        parser.error("a fresh job journal is required; no effect retries")
    root.mkdir(mode=0o700, exist_ok=False)
    cwd, audit = root / "empty-agent-cwd", root / "runtime-context"
    cwd.mkdir(mode=0o700)
    audit.mkdir(mode=0o700)
    receipt: dict[str, Any] = {
        "passed": False,
        "source_commit": source_commit(PROJECT),
        "effect_retry": False,
        "configured_softcap_usd": SESSION_CAP,
        "scheduling_reserve_usd": SCHEDULING_RESERVE_USD,
        "limits": "One Claude Code host, existing authenticated account and existing macOS permissions. "
        "No general host, clean OS or disk persistence qualification.",
    }
    started = time.monotonic()
    try:
        config, manifest, schema = installed_configuration(
            python,
            scope_path,
            journal,
            host_path,
            isolation,
            audit,
        )
        emitted = root / "host.json"
        write(emitted, config)
        write(root / "report-schema.json", schema)
        write(root / "run.json", manifest)
        scope = json.loads(scope_path.read_text())
        destination = scope["destination"]
        initial = ax_document_text(destination["pid"], destination["document"])
        receipt["oracle_before"] = initial
        require(initial == PREFIX, "fixture starting text differs")
        command = host_command(emitted, TOOLS, []) + ["--json-schema", json.dumps(schema)]
        task = prompt(scope) + (
            "\nReturn a structured final report matching the supplied JSON schema: completion, "
            "operations with their operation IDs and dispositions, and persistence. Include the full "
            "operation ledger for this task. Do not claim disk persistence without evidence. "
            "The host will validate this report against durable operation state before publishing it."
        )
        write(root / "command.json", command)
        (root / "prompt.txt").write_text(task)
        code, timed_out = run_host(command, task, root, cwd)
        receipt.update(returncode=code, timed_out=timed_out)
        evidence, claims = transcript_evidence(root / "transcript.jsonl")
        receipt["host"] = evidence
        # Run the readonly installed adapter even if the host rejected/omitted its output.
        product_env = isolated_environment(isolation)
        product_env.update(config["mcpServers"]["footwork"]["env"])
        receipt["report"] = validate_report(manifest["report_adapter"], claims, product_env, cwd, root)
        receipt["worker_absent"] = _wait_no_worker(journal)
        receipt["journal_rows"] = _rows(journal)
        receipt["runtime"] = runtime_evidence(audit, python, isolation, journal)
        # Allow the host's group retirement to finish; this performs no effect dispatch.
        deadline = time.monotonic() + 5
        while not server_absent(receipt["runtime"]["contexts"]) and time.monotonic() < deadline:
            time.sleep(0.05)
        receipt["server_absent"] = server_absent(receipt["runtime"]["contexts"])
        receipt["oracle_actual"] = ax_document_text(destination["pid"], destination["document"])
        require(code == 0 and not timed_out and not evidence["result_is_error"], "host failed")
        require(evidence["budget"]["valid"], "host cost missing, invalid or beyond scheduling reserve")
        require(
            evidence["valid_environment"] and not evidence["out_of_arm"] and evidence["effect_calls"],
            "host catalog/model/calls differ from qualification scope",
        )
        require(receipt["oracle_actual"] == PREFIX + VALUE, "independent final AX text differs")
        rows = receipt["journal_rows"]
        require(
            len(rows) == 1
            and rows[0]["state"] == "final"
            and rows[0]["disposition"] == "applied"
            and rows[0]["phase"] == "sent",
            "durable operation is not one final applied sent row",
        )
        require(not receipt["runtime"]["failures"], "installed runtime provenance failed")
        require(receipt["worker_absent"] and receipt["server_absent"], "owned processes remain")
        require(receipt["report"]["accepted"], "structured completion rejected")
        receipt["passed"] = True
    except (OSError, ValueError, KeyError, RuntimeError, psutil.Error, subprocess.SubprocessError) as exc:
        receipt["failure"] = f"{type(exc).__name__}: {exc}"
    finally:
        receipt["elapsed_seconds"] = time.monotonic() - started
        write(root / "receipt.json", receipt)
    print(json.dumps({"passed": receipt["passed"], "failure": receipt.get("failure")}), flush=True)
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
