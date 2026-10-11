"""A1 developmental host acceptance. Plan-only unless --execute; no heldout access."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import hashlib
import json
import math
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from capability_comparison_relay import LOST, Relay, oracle_edit, oracle_read
from capability_comparison_trial import host_command, parse_transcript, prompt, retire_backends, run_host
from capability_host_trial import ax_document_text, ax_reset_text
from capability_interrupt_trial import Server, destination_target
from capability_restart_trial import _retire_worker, _rows, _wait_no_worker, _worker

CASES = ("clean", "receipt", "later_edit", "no_receipt")
PREFIX = "Invoice report\n"
VALUE = "17.25 USD"
NOTE = "\nExternal note: preserve this edit."
TOOLS = [f"mcp__footwork__{n}" for n in ("bind", "observe", "act", "status")]
PROJECT = Path(__file__).resolve().parents[2]


def write(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    path.chmod(0o600)


class AcceptanceRelay(Relay):
    cancelled_during_request = False

    async def handle(self, msg: dict) -> None:
        try:
            await super().handle(msg)
        except asyncio.CancelledError:
            self.cancelled_during_request = "method" in msg and msg.get("id") is not None
            raise

    async def spawn(self) -> None:
        # The first server alone uses the already-qualified private R1 boundary.
        original = self.cfg["argv"]
        if self.spawn_count == 0 and self.cfg["case"] != "clean":
            boundary = "late_identical" if self.cfg["case"] == "no_receipt" else "receipt"
            self.cfg["argv"] = [
                sys.executable,
                str(self.root / "entry.py"),
                "--entry",
                "server",
                "--case",
                boundary,
                "--case-dir",
                str(self.root),
                "--scope",
                self.cfg["scope"],
                "--journal",
                self.cfg["journal"],
            ]
        try:
            await super().spawn()
        finally:
            self.cfg["argv"] = original

    async def interrupted(self, msg: dict) -> dict:
        assert self.proc
        pending = asyncio.create_task(self.request(msg, forward_notifications=False))
        journal = Path(self.cfg["journal"])
        deadline = time.monotonic() + 30
        try:
            while not (self.root / "hook.json").exists():
                if pending.done():
                    response = await pending
                    self.event("invalid", reason="mutation_returned_before_required_boundary")
                    return response
                if time.monotonic() >= deadline:
                    raise RuntimeError("required R1 boundary not reached")
                await asyncio.sleep(0.01)
            hook = json.loads((self.root / "hook.json").read_text())
            rows = _rows(journal)
            worker = _worker(journal)
            want = "before_native_dispatch" if self.cfg["case"] == "no_receipt" else "durable_result_held"
            if (
                hook["name"] != want
                or len(rows) != 1
                or rows[0]["execution_stage"] != "started"
                or worker is None
            ):
                raise RuntimeError("unqualified boundary or execution custody")
            self.event("boundary", hook=hook, journal=rows, worker=worker)
            os.killpg(self.proc.pid, signal.SIGKILL)
            await self.proc.wait()
            with contextlib.suppress(EOFError):
                await pending
            if self.cfg["case"] == "no_receipt":
                if not await asyncio.to_thread(_retire_worker, journal):
                    raise RuntimeError("attested worker retirement failed")
                oracle_edit(self.cfg["oracle"], PREFIX + VALUE)
            else:
                (self.root / "release").touch(mode=0o600)
                if not await asyncio.to_thread(_wait_no_worker, journal):
                    raise RuntimeError("receipt writer did not finish")
                if oracle_read(self.cfg["oracle"]) != PREFIX + VALUE:
                    raise RuntimeError("original append did not independently read back")
                if self.cfg["case"] == "later_edit":
                    oracle_edit(self.cfg["oracle"], PREFIX + VALUE + NOTE)
            self.interfered = True
            self.event(
                "dropped",
                request_id=msg["id"],
                child_returncode=self.proc.returncode,
                case=self.cfg["case"],
                oracle_after=oracle_read(self.cfg["oracle"]),
                journal=self.journal_state(),
            )
            await self.restart()
            return {"jsonrpc": "2.0", "id": msg["id"], "error": LOST}
        finally:
            if not pending.done():
                pending.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await pending


def configuration(root: Path, scope: Path, case: str) -> tuple[dict, dict]:
    relay = root / "relay"
    relay.mkdir(mode=0o700)
    relay.joinpath("entry.py").write_text(
        "import sys\nsys.path.insert(0,"
        + repr(str(Path(__file__).parent))
        + ")\nfrom capability_restart_trial import entry_main\nraise SystemExit(entry_main())\n"
    )
    dst = json.loads(scope.read_text())["destination"]
    cfg = {
        "case": case,
        "mode": "clean" if case == "clean" else "interrupted",
        "prefix": PREFIX,
        "scope": str(scope),
        "journal": str(root / "operations.sqlite"),
        "argv": [
            sys.executable,
            "-m",
            "jevdual.capability.mcp_server",
            "--scope",
            str(scope),
            "--journal",
            str(root / "operations.sqlite"),
        ],
        "oracle": {"kind": "ax", **dst},
        "destination_resource": f"native:{dst['pid']}:{dst['window_id']}",
        "mutation_tools": ["act"],
        "observation_tools": ["observe"],
    }
    write(relay / "config.json", cfg)
    server = {
        "command": sys.executable,
        "args": [str(Path(__file__).resolve()), "--relay", str(relay / "config.json")],
        "env": {"PYTHONPATH": str(PROJECT / "jevdual/python")},
    }
    return cfg, {"mcpServers": {"footwork": server}}


def codex_command(server: dict, final: Path) -> list[str]:
    cmd = [
        "codex",
        "exec",
        "--ignore-user-config",
        "--ignore-rules",
        "--ephemeral",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--json",
        "-o",
        str(final),
    ]
    settings = {
        "approval_policy": "never",
        "project_doc_max_bytes": 0,
        "web_search": "disabled",
        "features.shell_tool": False,
        "features.unified_exec": False,
        "features.view_image": False,
        "features.memories": False,
        "features.hooks": False,
        "features.plugins": False,
        "features.multi_agent": False,
        "features.multi_agent_v2": False,
        "features.code_mode": False,
        "tools.update_plan.enabled": False,
        "skills.include_instructions": False,
        "mcp_servers.footwork.command": server["command"],
        "mcp_servers.footwork.args": server["args"],
        "mcp_servers.footwork.env.PYTHONPATH": server["env"]["PYTHONPATH"],
        "mcp_servers.footwork.startup_timeout_sec": 60,
        "mcp_servers.footwork.tool_timeout_sec": 90,
    }
    for key, val in settings.items():
        cmd += ["-c", key + "=" + json.dumps(val)]
    # The installed CLI does not support skip_host_skill_discovery. Disable
    # actual discovered skill identities using the supported skills config.
    paths = set()
    for base in (Path.home() / ".codex/skills", Path.home() / ".agents/skills"):
        if base.exists():
            for directory in base.iterdir():
                skill = directory / "SKILL.md"
                if skill.is_file():
                    paths.update((str(skill), str(skill.resolve())))
            paths.update(str(p) for p in base.rglob("SKILL.md"))
    cache = Path.home() / ".codex/plugins/cache"
    if cache.exists():
        paths.update(str(p) for p in cache.rglob("SKILL.md"))
    entries = ["{path=" + json.dumps(p) + ",enabled=false}" for p in sorted(paths)]
    cmd += ["-c", "skills.config=[" + ",".join(entries) + "]"]
    for tool in ("bind", "observe", "act", "status"):
        cmd += ["-c", f'mcp_servers.footwork.tools.{tool}.approval_mode="approve"']
    return cmd


def codex_receipt(root: Path) -> dict:
    events = [
        json.loads(line) for line in (root / "transcript.jsonl").read_text().splitlines() if line.strip()
    ]
    items = [e.get("item", {}) for e in events if e.get("type") == "item.completed"]
    calls = [i for i in items if i.get("type") == "mcp_tool_call"]
    outside = [
        i.get("type")
        for i in items
        if i.get("type") not in ("agent_message", "reasoning", "mcp_tool_call", "error")
    ]
    outside += [
        i.get("server")
        for i in calls
        if i.get("server") != "footwork" or i.get("tool") not in ("bind", "observe", "act", "status")
    ]
    usage = [e.get("usage") for e in events if e.get("type") == "turn.completed"]
    errors = [e for e in events if e.get("type") in ("error", "turn.failed")]
    stderr = (root / "host-stderr.log").read_text()
    isolation_errors = [i.get("message", "") for i in items if i.get("type") == "error"]
    isolation_errors += [
        line for line in stderr.splitlines() if "unknown feature key" in line or "patch rejected" in line
    ]
    return {
        "valid_environment": not outside and not isolation_errors and bool(calls) and bool(usage),
        "executed_non_footwork": outside,
        "isolation_errors": isolation_errors,
        "calls": [i.get("tool") for i in calls],
        "final": (root / "final.txt").read_text() if (root / "final.txt").exists() else None,
        "usage": usage,
        "result_is_error": bool(errors),
        "model_requested": "installed CLI default",
        "model_reported": None,
        "cost_usd": None,
        "isolation_limit": "Exec JSON does not attest complete offered tool inventory/model; actual executed calls are audited.",
    }


class RelayClient(Server):
    def __init__(self, root: Path):
        self.proc = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--relay", str(root / "relay/config.json")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=(root / "control-stderr.log").open("w"),
            start_new_session=True,
        )
        self.next_id, self._buf = 1, b""
        try:
            self.request(
                "initialize",
                {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "A1-control", "version": "1"},
                },
            )
            self.notify("notifications/initialized", {})
            self.request("tools/list", {})
        except BaseException:
            self.stop()
            raise


def independent_result(root: Path, scope: dict, case: str) -> dict:
    journal = root / "operations.sqlite"
    finished = _wait_no_worker(journal) if journal.exists() else False
    dst = scope["destination"]
    text = ax_document_text(dst["pid"], dst["document"])
    time.sleep(0.2)
    stable = ax_document_text(dst["pid"], dst["document"]) == text
    rows = _rows(journal) if journal.exists() else []
    events_file = root / "relay/events.jsonl"
    events = [json.loads(x) for x in events_file.read_text().splitlines()] if events_file.exists() else []
    expected = PREFIX + VALUE + (NOTE if case == "later_edit" else "")
    disposition = "unknown" if case == "no_receipt" else "applied"
    errors = [e for e in events if e["kind"] == "invalid"]
    drops = [e for e in events if e["kind"] == "dropped"]
    restarts = [e for e in events if e["kind"] == "restarted"]
    valid_injection = not errors and (not drops if case == "clean" else len(drops) == len(restarts) == 1)
    passed = (
        finished
        and stable
        and text == expected
        and len(rows) == 1
        and rows[0]["disposition"] == disposition
        and valid_injection
    )
    return {
        "oracle_actual": text,
        "oracle_expected": expected,
        "oracle_stable": stable,
        "journal": rows,
        "owned_worker_finished": finished,
        "valid_injection": valid_injection,
        "injection_errors": errors,
        "execution_pass": passed,
        "claim_review": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--relay", type=Path)
    parser.add_argument("--scope", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--controls-only", action="store_true")
    parser.add_argument("--prior-claude-cost", type=float, default=0.0)
    parser.add_argument("--hosts", choices=("both", "claude", "codex"), default="both")
    args = parser.parse_args()
    if args.relay:
        cfg = json.loads(args.relay.read_text())
        relay = AcceptanceRelay(cfg, args.relay.parent)
        try:
            asyncio.run(relay.run())
        except asyncio.CancelledError:
            if relay.cancelled_during_request or relay.proc is None or relay.proc.returncode is None:
                relay.event(
                    "invalid", reason="cancellation interrupted an active request or unqualified cleanup"
                )
                raise
            relay.event("idle_shutdown", owned_backend_stopped=True)
        except Exception as exc:
            relay.event("invalid", reason=str(exc)[:200])
            raise
        return 0
    if not args.execute:
        print(json.dumps({"hosts": ["claude", "codex"], "cases": CASES, "execute": False}))
        return 0
    if not args.scope or not args.run_dir:
        parser.error("execution requires scope and run directory")
    if not math.isfinite(args.prior_claude_cost) or not 0 <= args.prior_claude_cost < 8:
        parser.error("prior Claude cost must be finite and within the aggregate ceiling")
    from ApplicationServices import AXIsProcessTrusted
    from jevdual.posture import screen_locked

    if screen_locked() or not AXIsProcessTrusted():
        parser.error("existing Accessibility access and unlocked desktop required")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=PROJECT).strip():
        parser.error("commit source before execution")
    root, scope_path = args.run_dir.resolve(), args.scope.resolve()
    if not root.is_relative_to(PROJECT / "output"):
        parser.error("private run directory must stay in project output")
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    scope = json.loads(scope_path.read_text())
    source_files = sorted((PROJECT / "jevdual/python/jevdual/capability").glob("*.py"))
    source_files += [
        Path(__file__),
        *[
            Path(__file__).with_name(n)
            for n in (
                "capability_comparison_relay.py",
                "capability_restart_trial.py",
                "capability_host_trial.py",
            )
        ],
    ]
    source_files += [
        PROJECT / "jevdual/uv.lock",
        PROJECT / "jevdual/python/jevdual/native.py",
        PROJECT / "jevdual/python/jevdual/ax.py",
    ]
    summary = {
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True).strip(),
        "source_hashes": {
            str(p.relative_to(PROJECT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files
        },
        "scope_sha256": hashlib.sha256(scope_path.read_bytes()).hexdigest(),
        "sessions": [],
        "claude_cost_usd": 0.0,
        "prior_claude_cost_usd": args.prior_claude_cost,
        "stop_reason": None,
        "claim_review_pending": not args.controls_only,
    }
    hosts = (
        ["control"] if args.controls_only else (["claude", "codex"] if args.hosts == "both" else [args.hosts])
    )
    try:
        for host in hosts:
            for case in CASES:
                if host == "claude" and args.prior_claude_cost + summary["claude_cost_usd"] + 2 > 8:
                    raise RuntimeError("Claude aggregate scheduling reserve exhausted")
                session = root / (host + "-" + case)
                session.mkdir(mode=0o700)
                dst = scope["destination"]
                ax_reset_text(dst["pid"], dst["document"], PREFIX)
                if ax_document_text(dst["pid"], dst["document"]) != PREFIX or screen_locked():
                    raise RuntimeError("independent fixture reset not qualified")
                _, config = configuration(session, scope_path, case)
                write(session / "mcp.json", config)
                started = time.monotonic()
                if host == "control":
                    client = RelayClient(session)
                    try:
                        client.tool("bind", {"name": "source"})
                        dest = client.tool("bind", {"name": "destination"})
                        arguments = {
                            "target": destination_target(dest),
                            "text": VALUE,
                            "client_token": "A1-control-" + case,
                        }
                        try:
                            act = client.tool("act", arguments)
                        except RuntimeError as exc:
                            if case == "clean" or "backend process exited; restarted" not in str(exc):
                                raise
                            act = {"transport_error": str(exc)}
                        # The relay presents a transport error; collect only public status.
                        listing = client.tool("status", {})
                        recent = listing.get("recent", [])
                        if len(recent) != 1:
                            raise RuntimeError("public status did not identify one operation")
                        status = client.tool(
                            "status", {"operation": recent[0]["operation_id"], "reconcile": True}
                        )
                        repeat = client.tool("act", arguments)
                        if repeat.get("operation_id") != recent[0]["operation_id"]:
                            raise RuntimeError("token collection did not preserve operation identity")
                        write(
                            session / "public.json",
                            {"act": act, "listing": listing, "status": status, "repeat": repeat},
                        )
                    finally:
                        client.stop()
                    receipt = {"valid_environment": True, "host": "control"}
                else:
                    task = prompt(scope)
                    cmd = (
                        host_command(session / "mcp.json", TOOLS, [])
                        if host == "claude"
                        else codex_command(config["mcpServers"]["footwork"], session / "final.txt")
                    )
                    write(session / "command.json", cmd)
                    (session / "prompt.txt").write_text(task)
                    code, timeout = run_host(cmd, task, session)
                    if not retire_backends(session):
                        raise RuntimeError("owned backend retirement unqualified")
                    receipt = (
                        parse_transcript(session / "transcript.jsonl", TOOLS, ["footwork"])
                        if host == "claude"
                        else codex_receipt(session)
                    )
                    receipt.update(returncode=code, timed_out=timeout)
                    if host == "claude":
                        cost = receipt["cost_usd"]
                        if not isinstance(cost, (float, int)) or not math.isfinite(cost) or cost < 0:
                            summary["stop_reason"] = "Claude cost unavailable"
                        else:
                            summary["claude_cost_usd"] += cost
                receipt.update(
                    independent_result(session, scope, case),
                    host=host,
                    case=case,
                    elapsed_seconds=time.monotonic() - started,
                )
                write(session / "receipt.json", receipt)
                summary["sessions"].append(
                    {
                        "host": host,
                        "case": case,
                        "execution_pass": receipt["execution_pass"],
                        "valid_environment": receipt["valid_environment"],
                        "elapsed_seconds": receipt["elapsed_seconds"],
                    }
                )
                write(root / "summary.json", summary)
                print(json.dumps(summary["sessions"][-1]), flush=True)
                if (
                    summary["stop_reason"]
                    or not receipt["execution_pass"]
                    or not receipt["valid_environment"]
                    or receipt.get("result_is_error")
                ):
                    raise RuntimeError(summary["stop_reason"] or "session failed or invalid; no retry")
        if args.controls_only:
            negative = root / "control-missing-boundary"
            negative.mkdir(mode=0o700)
            ax_reset_text(dst["pid"], dst["document"], PREFIX)
            if ax_document_text(dst["pid"], dst["document"]) != PREFIX:
                raise RuntimeError("negative-control reset unqualified")
            configuration(negative, scope_path, "receipt")
            client = RelayClient(negative)
            try:
                result = client.tool("act", {"target": "not-an-offered-target", "text": VALUE})
            finally:
                client.stop()
            events = [json.loads(line) for line in (negative / "relay/events.jsonl").read_text().splitlines()]
            rejected = (
                result.get("is_error")
                and ax_document_text(dst["pid"], dst["document"]) == PREFIX
                and any(e.get("reason") == "mutation_returned_before_required_boundary" for e in events)
                and not any(e["kind"] == "dropped" for e in events)
            )
            write(negative / "receipt.json", {"missing_boundary_rejected": bool(rejected), "public": result})
            summary["missing_boundary_rejected"] = bool(rejected)
            if not rejected:
                raise RuntimeError("missing boundary was not rejected")
    except Exception as exc:
        summary["stop_reason"] = type(exc).__name__ + ": " + str(exc)[:200]
        raise
    finally:
        write(root / "summary.json", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
