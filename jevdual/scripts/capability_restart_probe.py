"""Model-free feasibility probe for one detached destination-only append.

Default is a dry run. --execute uses an already-owned/open fixture; it never
creates, resets, or closes a UI surface. The child uses the existing scoped
backend. The parent verifies the effect independently through the host oracle.
This measures detached execution feasibility, not durable restart recovery.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

TIMEOUT_S = 30


def _write(path: Path, value: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8") as out:
        os.chmod(path, 0o600)
        json.dump(value, out, indent=2, ensure_ascii=False)
        out.write("\n")


async def _child(scope_path: Path, run_dir: Path, text: str) -> int:
    started = time.monotonic()
    report: dict[str, Any] = {"child_started_monotonic": started, "pid": os.getpid()}
    backend = None
    try:
        from jevdual.capability.backend import ScopedBackend

        imported = time.monotonic()
        report.update(imported_monotonic=imported, imports_s=imported - started)
        start_identity = await asyncio.to_thread(
            subprocess.check_output, ["ps", "-p", str(os.getpid()), "-o", "lstart="], text=True, timeout=2
        )
        report["process_identity"] = {
            "pid": os.getpid(),
            "pgid": os.getpgid(0),
            "start_lstart": start_identity.strip(),
        }
        backend = ScopedBackend(json.loads(scope_path.read_text()))
        observed = await backend.bind("destination")
        report["bound_monotonic"] = time.monotonic()
        rows = [row for row in observed["elements"] if "append" in row["moves"]]
        if len(rows) != 1:
            raise RuntimeError("the scoped destination must offer exactly one append target")
        row = rows[0]
        validated = await backend.validate(
            observed["resource"], observed["observation"], row["target"], "append", {"text": text}
        )
        report["validated_monotonic"] = time.monotonic()
        outcome = await backend.dispatch(validated)
        report["dispatched_monotonic"] = time.monotonic()
        readback = await backend.readback(validated)
        report.update(
            readback_monotonic=time.monotonic(),
            phase=outcome.phase,
            effect_hint=outcome.effect_hint,
            readback=readback,
            valid=outcome.phase == "sent" and readback.get("outcome") == "applied",
        )
    except Exception as exc:  # noqa: BLE001 - failure evidence, no retry
        report.update(valid=False, error_type=type(exc).__name__, error=str(exc)[:300])
    finally:
        if backend is not None:
            try:
                await backend.close()
            except Exception as exc:  # noqa: BLE001 - retain a terminal cleanup failure
                report.update(valid=False, close_error_type=type(exc).__name__)
        report["finished_monotonic"] = time.monotonic()
        _write(run_dir / "child.json", report)
    return 0 if report["valid"] else 1


def _execute(scope_path: Path, run_dir: Path, text: str) -> int:
    from capability_host_trial import OracleError, ax_document_text

    scope = json.loads(scope_path.read_text())
    destination = scope["destination"]
    run_dir.mkdir(mode=0o700)
    os.chmod(run_dir, 0o700)
    report: dict[str, Any] = {"scope": str(scope_path), "text": text, "timeout_s": TIMEOUT_S}
    try:
        before = ax_document_text(destination["pid"], destination["document"])
    except OracleError as exc:
        report.update(valid=False, prerequisite_error=str(exc))
        _write(run_dir / "report.json", report)
        return 1
    separator = "" if not before or before.endswith("\n") else "\n"
    expected = before + separator + text
    argv = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--child",
        "--scope",
        str(scope_path),
        "--run-dir",
        str(run_dir),
        "--text",
        text,
    ]
    _write(run_dir / "command.json", {"argv": argv, "start_new_session": True})
    spawn_started = time.monotonic()
    with (run_dir / "stdout.log").open("x") as stdout, (run_dir / "stderr.log").open("x") as stderr:
        os.chmod(run_dir / "stdout.log", 0o600)
        os.chmod(run_dir / "stderr.log", 0o600)
        proc = subprocess.Popen(argv, stdout=stdout, stderr=stderr, start_new_session=True)
        report.update(pid=proc.pid, spawn_started_monotonic=spawn_started)
        try:
            code = proc.wait(timeout=TIMEOUT_S)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                code = proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                code = proc.wait(timeout=5)
    report.update(exit_code=code, timed_out=timed_out, elapsed_s=time.monotonic() - spawn_started)
    child_path = run_dir / "child.json"
    child = json.loads(child_path.read_text()) if child_path.exists() else None
    report["child"] = child
    if child:
        report["spawn_to_imports_s"] = (
            child["imported_monotonic"] - spawn_started if "imported_monotonic" in child else None
        )
        report["spawn_to_dispatch_s"] = (
            child["dispatched_monotonic"] - spawn_started if "dispatched_monotonic" in child else None
        )
    try:
        actual = ax_document_text(destination["pid"], destination["document"])
        report["oracle"] = {
            "before": before,
            "separator": separator,
            "expected": expected,
            "actual": actual,
            "passed": actual == expected,
        }
    except OracleError as exc:
        report["oracle"] = {"passed": False, "error": str(exc)}
    report["valid"] = bool(
        code == 0 and not timed_out and child and child.get("valid") and report["oracle"]["passed"]
    )
    _write(run_dir / "report.json", report)
    print(json.dumps({"valid": report["valid"], "run_dir": str(run_dir), "elapsed_s": report["elapsed_s"]}))
    return 0 if report["valid"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--text", default="17.25 USD")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    scope, run_dir = args.scope.resolve(), args.run_dir.resolve()
    output_root = Path(__file__).resolve().parents[2] / "output"
    if not run_dir.is_relative_to(output_root) or run_dir == output_root:
        parser.error("run-dir must be a new directory inside project output")
    if not args.text.strip() or len(args.text) > 4096:
        parser.error("text must contain 1 to 4096 characters")
    if args.child:
        return asyncio.run(_child(scope, run_dir, args.text))
    if not args.execute:
        print(
            json.dumps(
                {
                    "execute": False,
                    "scope": str(scope),
                    "run_dir": str(run_dir),
                    "text": args.text,
                    "detached": True,
                    "timeout_s": TIMEOUT_S,
                }
            )
        )
        return 0
    return _execute(scope, run_dir, args.text)


if __name__ == "__main__":
    raise SystemExit(main())
