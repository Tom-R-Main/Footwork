"""Model-free restart qualification through real MCP and the scoped native route.

Without --execute this prints a plan only. The caller supplies an owned fixture.
Trial-only entry wrappers hold original calls at declared boundaries; an
independent observer kills owned processes. Hooks add no product execution API.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from capability_host_trial import OracleError, ax_document_text, ax_reset_text
from capability_interrupt_trial import Server, destination_target

CASES = (
    "prepared",
    "started",
    "delivered",
    "receipt",
    "final",
    "delayed",
    "worker_death",
    "late_identical",
    "later_edit",
    "corrupt_receipt",
    "file_replacement",
    "delayed_identical",
)
TIMEOUT_S = 30


def _write(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as out:
        os.chmod(path, 0o600)
        json.dump(value, out, indent=2, ensure_ascii=False)
        out.write("\n")


def _hold(out: Path, name: str) -> None:
    _write(out / "hook.json", {"name": name, "pid": os.getpid(), "monotonic": time.monotonic()})
    deadline = time.monotonic() + TIMEOUT_S
    while not (out / "release").exists():
        if time.monotonic() >= deadline:
            raise TimeoutError("trial boundary was not released")
        time.sleep(0.01)


def entry_main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry", choices=("server", "worker"), required=True)
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--case", choices=CASES, required=True)
    parser.add_argument("--scope", type=Path)
    parser.add_argument("--journal", type=Path)
    parser.add_argument("--packet", type=Path)
    args = parser.parse_args()
    from jevdual.capability.backend import ScopedBackend
    from jevdual.capability.execution_worker import run
    from jevdual.capability.journal import Journal
    from jevdual.capability.mcp_server import serve
    from jevdual.capability.recovery import ExecutionStore

    case, out = args.case, args.case_dir
    if args.entry == "server":
        original_launch = ExecutionStore._launch

        def launch(store, op):
            if case in ("prepared", "started", "final"):
                return original_launch(store, op)
            return subprocess.Popen(
                [
                    sys.executable,
                    str(out / "entry.py"),
                    "--entry",
                    "worker",
                    "--case",
                    case,
                    "--case-dir",
                    str(out),
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
        if case in ("prepared", "started", "final"):
            name = {"prepared": "begin", "started": "start", "final": "finish"}[case]
            original = getattr(Journal, name)

            def held(journal, *pos, **kw):
                result = original(journal, *pos, **kw)
                _hold(out, case)
                return result

            setattr(Journal, name, held)
        asyncio.run(serve(json.loads(args.scope.read_text()), args.journal))
    else:
        if case == "file_replacement":
            from jevdual.capability import execution_worker

            original_identity = execution_worker.native_identity
            first_identity = True

            def held_identity(scope):
                nonlocal first_identity
                if first_identity:
                    first_identity = False
                    _hold(out, "before_native_identity")
                return original_identity(scope)

            execution_worker.native_identity = held_identity
        elif case in ("delivered", "delayed", "delayed_identical", "worker_death", "late_identical"):
            original_dispatch = ScopedBackend.dispatch

            async def held_dispatch(backend, validated):
                if case != "delivered":
                    await asyncio.to_thread(_hold, out, "before_native_dispatch")
                outcome = await original_dispatch(backend, validated)
                if case == "delivered":
                    await asyncio.to_thread(_hold, out, "native_dispatch_return_held")
                return outcome

            ScopedBackend.dispatch = held_dispatch
        else:
            original_write = ExecutionStore.write_record

            def held_result(store, op_id, name, value):
                original_write(store, op_id, name, value)
                if name == "result":
                    _hold(out, "durable_result_held")

            ExecutionStore.write_record = held_result
        return asyncio.run(run(args.packet))
    return 0


class TrialServer(Server):
    """The existing RPC client with a private trial entry replacing launch only."""

    def __init__(self, scope: Path, journal: Path, out: Path, case: str) -> None:
        self.log = (out / "server-stderr.log").open("a")
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
                    "clientInfo": {"name": "footwork-r1", "version": "1"},
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

    def stop(self) -> None:
        try:
            super().stop()
        finally:
            self.log.close()


def _rows(journal: Path) -> list[dict[str, Any]]:
    try:
        with sqlite3.connect(f"file:{journal}?mode=ro", uri=True, timeout=0.1) as db:
            db.row_factory = sqlite3.Row
            return [
                dict(row)
                for row in db.execute("SELECT id,state,disposition,phase,execution_stage FROM operations")
            ]
    except sqlite3.OperationalError:
        return []


def _operation_artifacts(journal: Path) -> tuple[dict, dict] | None:
    from jevdual.capability.recovery import read_private, validate_packet

    rows = _rows(journal)
    if len(rows) != 1:
        return None
    directory = Path(str(journal) + ".executions") / rows[0]["id"]
    try:
        packet = validate_packet(read_private(directory / "packet.json"))
        registration = read_private(directory / "registration.json")
    except FileNotFoundError:
        return None
    return packet, registration


def _worker(journal: Path) -> dict | None:
    from jevdual.capability.recovery import binding, process_identity

    records = _operation_artifacts(journal)
    if records is None:
        return None
    packet, registration = records
    if any(registration.get(k) != v for k, v in binding(packet).items()):
        raise RuntimeError("worker registration binding mismatch")
    pid = registration["pid"]
    try:
        identity = process_identity(pid)
        pgid = os.getpgid(pid)
    except ProcessLookupError:
        return None
    except Exception as exc:
        import psutil

        if isinstance(exc, psutil.NoSuchProcess):
            return None
        raise
    if identity["start"] != registration["start"] or pgid != registration["pgid"] or pgid != pid:
        raise RuntimeError("worker process identity/ownership changed")
    return registration


def _retire_worker(journal: Path) -> bool:
    import psutil

    if _operation_artifacts(journal) is None:
        return False  # missing registration cannot prove a launch-gap child is stopped
    registration = _worker(journal)
    if registration is None:
        return True
    os.killpg(registration["pid"], signal.SIGKILL)
    try:
        psutil.Process(registration["pid"]).wait(timeout=5)
    except psutil.NoSuchProcess:
        pass
    return _worker(journal) is None


def _wait_no_worker(journal: Path, *, never_launched: bool = False) -> bool:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if _operation_artifacts(journal) is None:
            if never_launched:
                return True  # the trial's prepared/start hook is strictly before launch
        elif _worker(journal) is None:
            return True
        time.sleep(0.025)
    return False


def run_case(case: str, scope_path: Path, out: Path, prefix: str, payload: str) -> dict:
    scope = json.loads(scope_path.read_text())
    pid, document = scope["destination"]["pid"], scope["destination"]["document"]
    separator = "" if not prefix or prefix.endswith("\n") else "\n"
    expected = prefix + separator + payload
    journal = out / "operations.sqlite"
    out.mkdir(mode=0o700)
    entry = out / "entry.py"
    entry.write_text(
        "import sys\nsys.path.insert(0,"
        + repr(str(Path(__file__).parent.resolve()))
        + ")\nfrom capability_restart_trial import entry_main\nraise SystemExit(entry_main())\n"
    )
    entry.chmod(0o600)
    rec: dict[str, Any] = {"case": case, "expected": expected, "steps": [], "valid": False}
    first = restarted = None

    def oracle(label):
        actual = ax_document_text(pid, document)
        rec["steps"].append({"oracle": label, "actual": actual})
        return actual

    def release():
        (out / "release").touch(mode=0o600, exist_ok=True)

    try:
        ax_reset_text(pid, document, prefix)
        if oracle("reset") != prefix:
            raise OracleError("fixture reset did not read back exactly")
        first = TrialServer(scope_path, journal, out, case)
        observed = first.tool("bind", {"name": "destination"})
        arguments = {"target": destination_target(observed), "text": payload, "client_token": "r1-" + case}
        first.send("tools/call", {"name": "act", "arguments": arguments})
        rec["act_submitted"] = True
        deadline = time.monotonic() + TIMEOUT_S
        while not (out / "hook.json").exists():
            if time.monotonic() >= deadline or first.proc.poll() is not None:
                raise RuntimeError("required boundary was not reached")
            time.sleep(0.005)
        rec["hook"] = json.loads((out / "hook.json").read_text())
        rec["journal_at_boundary"] = _rows(journal)
        rows = rec["journal_at_boundary"]
        if len(rows) != 1:
            raise RuntimeError("the boundary did not retain exactly one admitted operation")
        if case == "prepared" and rows[0]["execution_stage"] != "prepared":
            raise RuntimeError("prepared boundary landed after execution admission")
        if case == "final" and rows[0]["state"] != "final":
            raise RuntimeError("final boundary did not retain a final commit")
        if case not in ("prepared", "final") and rows[0]["execution_stage"] != "started":
            raise RuntimeError("started boundary was not durable")
        rec["registration_at_boundary"] = _worker(journal)
        rec["unread_reply"] = first.kill().decode(errors="replace")[:4000]
        first.log.close()
        oracle("after_parent_kill")
        if case in ("worker_death", "late_identical"):
            if rec["registration_at_boundary"] is None:
                raise RuntimeError("worker death case has no attested owner")
            rec["worker_retired"] = _retire_worker(journal)
        elif case not in ("delayed", "delayed_identical"):
            if case == "file_replacement":
                document_path = Path(document).resolve()
                output_root = Path(__file__).resolve().parents[2] / "output"
                if not document_path.is_relative_to(output_root):
                    raise RuntimeError("file replacement may target only the owned project-output fixture")
                replacement = out / "replacement.txt"
                replacement.write_text(prefix)
                replacement.chmod(0o600)
                os.replace(replacement, document_path)
                rec["file_replaced"] = True
            release()
            rec["worker_finished"] = _wait_no_worker(journal, never_launched=case in ("prepared", "started"))
        if case in ("late_identical", "delayed_identical"):
            ax_reset_text(pid, document, expected)
        elif case == "later_edit":
            ax_reset_text(pid, document, expected + "\nExternal note: preserve this edit.")
        elif case == "corrupt_receipt":
            rows = _rows(journal)
            result_path = Path(str(journal) + ".executions") / rows[0]["id"] / "result.json"
            original = result_path.read_text()
            _write(out / "original-result.json", json.loads(original))
            corrupted = json.loads(original)
            corrupted["nonce"] = "0" * 32
            result_path.write_text(json.dumps(corrupted))  # explicit trial fault in owned storage only
            result_path.chmod(0o600)
        restarted = Server(scope_path, journal, out / "restart-stderr.log")
        (out / "restart-stderr.log").chmod(0o600)
        status = restarted.tool("status", {"client_token": arguments["client_token"], "reconcile": True})
        rec["status"] = status
        oracle("after_status")
        repeat = restarted.tool("act", arguments)
        rec["repeat"] = repeat
        oracle("after_same_token")
        if case in ("delayed", "delayed_identical"):
            rec["pending_custody"] = _worker(journal)
            if status.get("disposition") != "unknown" or rec["pending_custody"] is None:
                raise RuntimeError("delayed owner was not retained as unknown/active")
            if case == "delayed_identical" and status.get("current", {}).get("agreement") != "yes":
                raise RuntimeError("the matching external text counterexample was not reached")
            current = restarted.tool("bind", {"name": "destination"})
            blocked = restarted.tool("act", {"target": destination_target(current), "text": payload})
            rec["pending_conflict"] = blocked
            if (blocked.get("error") or {}).get("code") != "busy":
                raise RuntimeError("pending owner did not block conflicting input")
            release()
            rec["worker_finished"] = _wait_no_worker(journal)
            status = restarted.tool("status", {"client_token": arguments["client_token"], "reconcile": True})
            rec["status_after_release"] = status
        expected_disposition = (
            "not_sent"
            if case == "prepared"
            else "refused"
            if case in ("file_replacement", "delayed_identical")
            else "unknown"
            if case in ("started", "worker_death", "late_identical", "corrupt_receipt")
            else "applied"
        )
        actual = oracle("after_collection")
        expected_actual = (
            prefix if case in ("prepared", "started", "worker_death", "file_replacement") else expected
        )
        if case == "later_edit":
            expected_actual += "\nExternal note: preserve this edit."
        if expected_disposition == "unknown":
            current = restarted.tool("bind", {"name": "destination"})
            blocked = restarted.tool("act", {"target": destination_target(current), "text": payload})
            rec["conflicting_append"] = blocked
            if (blocked.get("error") or {}).get("code") != "busy":
                raise RuntimeError("unknown did not block conflicting input")
        rec["valid"] = (
            status.get("disposition") == expected_disposition
            and bool(repeat.get("repeat"))
            and actual == expected_actual
            and oracle("final") == expected_actual
            and rec.get("worker_finished", True)
            and rec.get("worker_retired", True)
        )
        if case == "later_edit":
            rec["valid"] = rec["valid"] and status.get("current", {}).get("agreement") == "no"
        if case == "late_identical":
            rec["valid"] = rec["valid"] and status.get("current", {}).get("agreement") == "yes"
    except Exception as exc:  # noqa: BLE001 - preserve invalid cases, no retry
        rec.update(error_type=type(exc).__name__, error=str(exc)[:400])
    finally:
        release()
        if first is not None and first.proc.poll() is None:
            first.stop()
        if restarted is not None:
            restarted.stop()
        try:
            never_launched = not rec.get("act_submitted") or (
                case in ("prepared", "started") and (out / "hook.json").exists()
            )
            rec["worker_cleanup"] = _wait_no_worker(journal, never_launched=never_launched) or _retire_worker(
                journal
            )
        except Exception as exc:  # noqa: BLE001 - cleanup requires positive ownership
            rec["worker_cleanup"] = False
            rec["cleanup_error"] = type(exc).__name__
        rec["valid"] = rec["valid"] and rec["worker_cleanup"]
        _write(out / "report.json", rec)
    return rec


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
    output_root = Path(__file__).resolve().parents[2] / "output"
    if not out.is_relative_to(output_root) or out == output_root:
        parser.error("run-dir must be inside project output")
    if not args.execute:
        print(json.dumps({"execute": False, "cases": args.cases, "scope": str(scope), "run_dir": str(out)}))
        return 0
    out.mkdir(mode=0o700)
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
