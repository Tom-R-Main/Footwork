"""Three actual MCP/native freshness guards with an independent fixture actor.

Dry run by default. --execute requires an existing owned TextEdit fixture under
project output. Trial entry wrappers replace only process launch and introduce
the declared interference immediately before the ORIGINAL NativeBridge._live.
No capability reply, outcome, readback or receipt is fabricated.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from capability_host_trial import (
    OracleError,
    _document_path,
    _scoped_text_area,
    ax_document_text,
    ax_reset_text,
)
from capability_interrupt_trial import Server, destination_target
from capability_restart_trial import _operation_artifacts, _retire_worker, _wait_no_worker

CASES = ("suffix_space", "suffix_newline", "window_move")
PROJECT = Path(__file__).resolve().parents[2]


def _write(path: Path, value: Any) -> None:
    data = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    if len(data.encode()) > 1048576:
        raise ValueError("trial record exceeds the fixed one-MiB bound")
    with path.open("x", encoding="utf-8") as out:
        os.chmod(path, 0o600)
        out.write(data)


def _point(element: Any) -> tuple[float, float]:
    from ApplicationServices import (
        AXUIElementCopyAttributeValue,
        AXValueGetValue,
        kAXValueCGPointType,
    )

    error, value = AXUIElementCopyAttributeValue(element, "AXPosition", None)
    if error:
        raise OracleError(f"AXPosition read failed ({error})")
    ok, point = AXValueGetValue(value, kAXValueCGPointType, None)
    if not ok:
        raise OracleError("AXPosition did not expose a CGPoint")
    return float(point.x), float(point.y)


def _actor(case: str, scope: dict, packet: dict, out: Path, bridge: Any, snapshot: Any, cid: int) -> None:
    """One independent interference, using observed field/position and the owned scope."""
    from jevdual import ax
    from jevdual.capability.recovery import fingerprint

    destination = scope["destination"]
    pid, window_id, document = destination["pid"], destination["window_id"], destination["document"]
    record: dict[str, Any] = {
        "case": case,
        "pid": pid,
        "window_id": window_id,
        "document": document,
        "worker_pid": os.getpid(),
        "injected_monotonic": time.monotonic(),
        "valid": False,
        "stage": "after_validation_before_original_NativeBridge_live_observation",
    }
    try:
        if (bridge.pid, bridge.window_id) != (pid, window_id):
            raise OracleError("actor was invoked outside its exact scoped window")
        window = ax.window_element(pid, window_id)
        actual_document = _document_path(window)
        record["document_before"] = actual_document
        if not actual_document or Path(actual_document).resolve() != Path(document).resolve():
            raise OracleError("actor window does not name the owned document")
        before = ax_document_text(pid, document)
        record["before"] = before
        if fingerprint(before) != packet["recovery"]["before"]:
            raise OracleError("actor field no longer equals the admitted exact prefix")
        body = _scoped_text_area(pid, document)
        frame = ax.frame_of(body)
        record["offered_frame"] = snapshot.frames.get(cid)
        record["field_frame_before"] = None if frame is None else [frame.x, frame.y, frame.w, frame.h]
        if case in ("suffix_space", "suffix_newline"):
            expected = before + (" " if case == "suffix_space" else "\n")
            ax_reset_text(pid, document, expected)
            record["actor_write"] = {"attribute": "AXValue", "error": 0}
        else:
            from ApplicationServices import (
                AXUIElementSetAttributeValue,
                AXValueCreate,
                kAXValueCGPointType,
            )

            observed = _point(window)
            desired = (observed[0] + 20.0, observed[1])
            point = AXValueCreate(kAXValueCGPointType, desired)
            if point is None:
                raise OracleError("new observed-offset AXPosition could not be encoded")
            error = AXUIElementSetAttributeValue(window, "AXPosition", point)
            record["actor_write"] = {"attribute": "AXPosition", "error": int(error)}
            record["window_position_before"] = observed
            record["window_position_requested"] = desired
            if error:
                raise OracleError(f"AXPosition mutation failed ({error})")
            moved = _point(window)
            record["window_position_after"] = moved
            if moved != desired:
                raise OracleError("the observed window did not move to the requested offset")
            expected = before
        after_frame = ax.frame_of(_scoped_text_area(pid, document))
        record["field_frame_after"] = (
            None if after_frame is None else [after_frame.x, after_frame.y, after_frame.w, after_frame.h]
        )
        record["actual_after_actor"] = ax_document_text(pid, document)
        record["expected_after_actor"] = expected
        record["document_after"] = _document_path(ax.window_element(pid, window_id))
        if record["actual_after_actor"] != expected:
            raise OracleError("actor interference did not read back exactly")
        if record["document_after"] != record["document_before"]:
            raise OracleError("actor window document identity changed")
        if case == "window_move" and record["field_frame_after"] == record["field_frame_before"]:
            raise OracleError("window mutation did not change the actual field geometry")
        record["valid"] = True
    except Exception as exc:  # actor errors invalidate the case, never retry
        record.update(error_type=type(exc).__name__, error=str(exc)[:400])
        raise
    finally:
        _write(out / "actor.json", record)


def entry_main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry", choices=("server", "worker"), required=True)
    parser.add_argument("--case", choices=CASES, required=True)
    parser.add_argument("--case-dir", required=True, type=Path)
    parser.add_argument("--scope", type=Path)
    parser.add_argument("--journal", type=Path)
    parser.add_argument("--packet", type=Path)
    args = parser.parse_args()
    from jevdual.capability.execution_worker import run
    from jevdual.capability.mcp_server import serve
    from jevdual.capability.recovery import ExecutionStore, read_private, validate_packet
    from jevdual.native import NativeBridge

    if args.entry == "server":

        def launch(store, op):
            return subprocess.Popen(
                [
                    sys.executable,
                    str(args.case_dir / "entry.py"),
                    "--entry",
                    "worker",
                    "--case",
                    args.case,
                    "--case-dir",
                    str(args.case_dir),
                    "--packet",
                    str(store.directory(op.id) / "packet.json"),
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                start_new_session=True,
            )

        ExecutionStore._launch = launch
        asyncio.run(serve(json.loads(args.scope.read_text()), args.journal))
        return 0
    packet = validate_packet(read_private(args.packet))
    original_live = NativeBridge._live
    injected = False

    async def live(bridge, snapshot, cid, operation):
        nonlocal injected
        if operation == "append":
            if injected:
                raise RuntimeError("a second live append guard was reached")
            injected = True
            await asyncio.to_thread(
                _actor, args.case, packet["recovery"]["scope"], packet, args.case_dir, bridge, snapshot, cid
            )
        return await original_live(bridge, snapshot, cid, operation)

    NativeBridge._live = live
    return asyncio.run(run(args.packet))


class GuardServer(Server):
    def __init__(self, scope: Path, journal: Path, out: Path, case: str) -> None:
        self.log = (out / "server-stderr.log").open("x")
        os.chmod(out / "server-stderr.log", 0o600)
        self.proc = subprocess.Popen(
            [
                sys.executable,
                str(out / "entry.py"),
                "--entry",
                "server",
                "--case",
                case,
                "--case-dir",
                str(out),
                "--scope",
                str(scope),
                "--journal",
                str(journal),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.log,
            start_new_session=True,
        )
        self.next_id, self._buf = 1, b""
        try:
            result = self.request(
                "initialize",
                {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "footwork-guard", "version": "1"},
                },
            )
            if result.get("serverInfo", {}).get("name") != "footwork-capability":
                raise RuntimeError("unexpected MCP server identity")
            self.notify("notifications/initialized", {})
        except BaseException:
            if self.proc.poll() is None:
                self.kill()
            self.log.close()
            raise

    def read(self, rid: int, timeout: float = 45) -> dict[str, Any]:
        return super().read(rid, timeout=timeout)

    def stop(self) -> None:
        try:
            super().stop()
        finally:
            self.log.close()


def run_case(case: str, scope_path: Path, out: Path, prefix: str, payload: str) -> dict:
    scope = json.loads(scope_path.read_text())
    destination = scope["destination"]
    pid, document = destination["pid"], destination["document"]
    out.mkdir(mode=0o700)
    entry = out / "entry.py"
    entry.write_text(
        "import sys\nsys.path.insert(0,"
        + repr(str(Path(__file__).parent.resolve()))
        + ")\nfrom capability_dispatch_guard_trial import entry_main\nraise SystemExit(entry_main())\n"
    )
    entry.chmod(0o600)
    journal = out / "operations.sqlite"
    record: dict[str, Any] = {
        "case": case,
        "prefix": prefix,
        "payload": payload,
        "destination": destination,
        "steps": [],
        "valid": False,
    }
    server = None

    def oracle(label):
        actual = ax_document_text(pid, document)
        record["steps"].append({"oracle": label, "actual": actual})
        return actual

    try:
        ax_reset_text(pid, document, prefix)
        if oracle("reset") != prefix:
            raise OracleError("owned fixture reset did not read back exactly")
        server = GuardServer(scope_path, journal, out, case)
        observed = server.tool("bind", {"name": "destination"})
        arguments = {"target": destination_target(observed), "text": payload, "client_token": "guard-" + case}
        record["act_submitted"] = True
        result = server.tool("act", arguments)
        record["act"] = result
        actor = json.loads((out / "actor.json").read_text())
        record["actor"] = actor
        expected = prefix + (" " if case == "suffix_space" else "\n" if case == "suffix_newline" else "")
        after_act = oracle("after_act")
        status = server.tool("status", {"operation": result["operation_id"], "reconcile": True})
        record["status"] = status
        after_status = oracle("after_status")
        repeated = server.tool("act", arguments)
        record["repeat"] = repeated
        after_repeat = oracle("after_same_token")
        artifacts = _operation_artifacts(journal)
        record["execution_artifacts"] = (
            None if artifacts is None else {"packet": artifacts[0], "registration": artifacts[1]}
        )
        record["valid"] = (
            actor.get("valid") is True
            and actor.get("expected_after_actor") == expected
            and result.get("disposition") in ("not_sent", "refused")
            and result.get("phase") == "not_sent"
            and status.get("disposition") == result.get("disposition")
            and repeated.get("repeat") is True
            and repeated.get("operation_id") == result.get("operation_id")
            and after_act == after_status == after_repeat == expected
            and artifacts is not None
        )
    except Exception as exc:  # noqa: BLE001 - no retries or fabricated successful guards
        record.update(error_type=type(exc).__name__, error=str(exc)[:400])
    finally:
        if server is not None:
            try:
                server.stop()
            except Exception as exc:  # noqa: BLE001 - still attest the independent worker
                record.update(valid=False, server_cleanup_error=type(exc).__name__)
        never_launched = not record.get("act_submitted")
        try:
            record["worker_cleanup"] = _wait_no_worker(
                journal, never_launched=never_launched
            ) or _retire_worker(journal)
        except Exception as exc:  # noqa: BLE001 - unattested workers cannot be killed
            record.update(worker_cleanup=False, cleanup_error=type(exc).__name__)
        record["valid"] = record["valid"] and record["worker_cleanup"]
        _write(out / "report.json", record)
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--start-text", default="Invoice report\n")
    parser.add_argument("--text", default="17.25 USD")
    parser.add_argument("--cases", nargs="+", choices=CASES, default=list(CASES))
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    scope, out = args.scope.resolve(), args.run_dir.resolve()
    if not out.is_relative_to(PROJECT / "output") or out == PROJECT / "output":
        parser.error("run-dir must be a new directory inside project output")
    if not args.execute:
        print(json.dumps({"execute": False, "cases": args.cases, "scope": str(scope), "run_dir": str(out)}))
        return 0
    if scope.stat().st_size > 131072:
        parser.error("scope exceeds the bounded private packet size")
    scope_data = json.loads(scope.read_text())
    from jevdual.capability.backend import ScopedBackend

    ScopedBackend._check_scope(scope_data)
    if not Path(scope_data["destination"]["document"]).resolve().is_relative_to(PROJECT / "output"):
        parser.error("actor may change only the owned project-output TextEdit fixture")
    if not args.text.strip() or len(args.text) > 4096:
        parser.error("text must contain 1 to 4096 characters")
    if len(args.start_text) > 4096:
        parser.error("fixture start-text exceeds 4096 characters")
    out.mkdir(mode=0o700)
    paths = [
        Path(__file__),
        PROJECT / "jevdual/python/jevdual/native.py",
        *(PROJECT / "jevdual/python/jevdual/capability").glob("*.py"),
    ]
    freeze = {
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True).strip(),
        "source_sha256": {
            str(p.relative_to(PROJECT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths
        },
        "scope": scope_data,
        "cases": args.cases,
    }
    _write(out / "source-freeze.json", freeze)
    records = []
    for case in args.cases:
        record = run_case(case, scope, out / case, args.start_text, args.text)
        records.append(record)
        print(json.dumps({"case": case, "valid": record["valid"], "error": record.get("error")}), flush=True)
        if not record["valid"]:
            break
    valid = len(records) == len(args.cases) and all(r["valid"] for r in records)
    _write(out / "summary.json", {"valid": valid, "cases_requested": args.cases, "cases": records})
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
