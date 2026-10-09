"""CS3: kill the real capability server mid-append, restart it, and check what a caller can recover.

Preregistered in docs/notebook/2026-10-09-capability-slice.md (CS3). No model is involved: this script is
the MCP client. It speaks JSON-RPC over the server's stdio and, as a caller, uses only the public tools.
Two independent watchers decide when to kill and classify the evidence; neither steers the caller.

- **Case A (delivered):** the client sends ``act`` and does not read the reply. An AX watcher SIGKILLs the
  server's process group at the first change of the scoped field.
- **Case B (intent durable):** a read-only journal watcher SIGKILLs at the first durable ``dispatching``
  row. That does not establish that nothing was delivered: the OS call may already be in flight.

Each case then restarts the server on the same journal. The caller runs ``status()``, ``act`` with the
same public target and token, and, for an unresolved operation, a fresh bind and observe followed by a
tokenless ``act``. The independent AX oracle (scripts/capability_host_trial.py) reads the document after
each step.

Without ``--execute`` the script only prints its plan. Only trial-owned server process groups are killed.

    uv run python scripts/capability_interrupt_trial.py --scope RUN/scope.json --run-dir RUN/interrupt \
        --expected-value '17.25 USD' --start-text $'Invoice report\\n' --execute
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
import select
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from capability_host_trial import OracleError, ax_document_text, ax_reset_text

TOKEN = "cs3-interrupt-{case}"
WATCH_TIMEOUT_S = 20.0
RPC_TIMEOUT_S = 30.0
POLL_S = {"A": 0.01, "B": 0.002}


class Server:
    """One trial-owned MCP server process group, driven as a plain JSON-RPC client."""

    def __init__(self, scope: Path, journal: Path, log: Path) -> None:
        self.proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "jevdual.capability.mcp_server",
                "--scope",
                str(scope),
                "--journal",
                str(journal),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=log.open("a"),
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
            start_new_session=True,
        )
        self.next_id = 1
        self._buf = b""
        try:
            result = self.request(
                "initialize",
                {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "footwork-cs3", "version": "1"},
                },
            )
            if result.get("serverInfo", {}).get("name") != "footwork-capability":
                raise RuntimeError(f"unexpected server: {result}")
            self.notify("notifications/initialized", {})
        except BaseException:
            if self.proc.poll() is None:
                with contextlib.suppress(ProcessLookupError, PermissionError):
                    os.killpg(self.proc.pid, signal.SIGKILL)
            self.proc.wait(timeout=10)
            raise

    def _write(self, message: dict[str, Any]) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write((json.dumps(message) + "\n").encode())
        self.proc.stdin.flush()

    def notify(self, method: str, params: dict[str, Any]) -> None:
        self._write({"jsonrpc": "2.0", "method": method, "params": params})

    def send(self, method: str, params: dict[str, Any]) -> int:
        rid, self.next_id = self.next_id, self.next_id + 1
        self._write({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        return rid

    def read(self, rid: int, timeout: float = RPC_TIMEOUT_S) -> dict[str, Any]:
        assert self.proc.stdout is not None
        deadline = time.monotonic() + timeout
        while True:
            while b"\n" in self._buf:
                line, self._buf = self._buf.split(b"\n", 1)
                msg = json.loads(line)
                if msg.get("id") == rid:
                    if "error" in msg:
                        raise RuntimeError(f"rpc error: {msg['error']}")
                    return msg["result"]
            left = deadline - time.monotonic()
            if left <= 0 or not select.select([self.proc.stdout], [], [], left)[0]:
                raise TimeoutError(f"no reply to request {rid}")
            chunk = os.read(self.proc.stdout.fileno(), 65536)
            if not chunk:
                raise RuntimeError("server closed its stdout")
            self._buf += chunk

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        return self.read(self.send(method, params))

    def tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        return {"is_error": bool(result.get("isError")), **(result.get("structuredContent") or {})}

    def kill(self) -> bytes:
        """SIGKILL the whole server process group; return reply bytes it wrote that nobody read."""
        os.killpg(self.proc.pid, signal.SIGKILL)
        self.proc.wait(timeout=10)
        assert self.proc.stdout is not None
        fd = self.proc.stdout.fileno()
        fcntl.fcntl(fd, fcntl.F_SETFL, fcntl.fcntl(fd, fcntl.F_GETFL) | os.O_NONBLOCK)
        unread = self._buf
        try:
            while chunk := os.read(fd, 65536):
                unread += chunk
        except BlockingIOError:
            pass
        return unread

    def stop(self) -> None:
        if self.proc.poll() is None:
            assert self.proc.stdin is not None
            self.proc.stdin.close()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(self.proc.pid, signal.SIGKILL)
                self.proc.wait(timeout=10)


def journal_rows(path: Path) -> list[dict[str, Any]]:
    """Read-only view for the watcher and the evidence record; the scripted caller never uses it."""
    if not path.exists():
        return []
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=1)
    try:
        rows = db.execute("SELECT id, state, disposition, phase, client_token FROM operations").fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        db.close()
    return [dict(zip(("id", "state", "disposition", "phase", "client_token"), r, strict=True)) for r in rows]


def destination_target(observation: dict[str, Any]) -> str:
    targets = [e["target"] for e in observation.get("elements") or [] if "append" in (e.get("moves") or [])]
    if len(targets) != 1:
        raise RuntimeError(f"expected one append target, saw {len(targets)}")
    return targets[0]


def count_value(text: str | None, start: str, value: str) -> int | None:
    """0 for the exact starting text, k for the starting text plus exactly k copies of ``value``, else None."""
    if text is None or not text.startswith(start):
        return None
    rest = text[len(start) :]
    k = rest.count(value)
    return k if rest == value * k else None


def run_case(case: str, a: argparse.Namespace, out: Path) -> dict[str, Any]:
    pid, document = a.pid, a.document
    journal, log = out / f"{case}-operations.sqlite", out / f"{case}-server-stderr.txt"
    token = TOKEN.format(case=case)
    rec: dict[str, Any] = {"case": case, "token": token, "steps": []}

    def oracle(label: str) -> int | None:
        try:
            text = ax_document_text(pid, document)
        except OracleError as exc:
            rec["steps"].append({"oracle": label, "error": str(exc)})
            return None
        n = count_value(text, a.start_text, a.expected_value)
        rec["steps"].append({"oracle": label, "text": text, "count": n})
        return n

    ax_reset_text(pid, document, a.start_text)
    time.sleep(0.5)
    if ax_document_text(pid, document) != a.start_text:
        rec["verdict"] = "inconclusive"
        rec["reason"] = "reset not confirmed by the AX oracle"
        return rec

    first = Server(a.scope, journal, log)
    try:
        first.tool("bind", {"name": "source"})
        dest = first.tool("bind", {"name": "destination"})
        target = destination_target(dest)
        rec["target"] = target
        t0 = time.monotonic()
        first.send(
            "tools/call",
            {"name": "act", "arguments": {"target": target, "text": a.expected_value, "client_token": token}},
        )
        trigger = None
        while time.monotonic() - t0 < WATCH_TIMEOUT_S:
            if case == "A":
                try:
                    if ax_document_text(pid, document) != a.start_text:
                        trigger = "field_changed"
                except OracleError:
                    pass
            else:
                rows = journal_rows(journal)
                if rows:
                    trigger = "row_" + rows[0]["state"]
            if trigger:
                break
            time.sleep(POLL_S[case])
        rec["trigger"] = trigger
        rec["trigger_s"] = round(time.monotonic() - t0, 4)
        unread = first.kill()
    finally:
        if first.proc.poll() is None:
            first.kill()
    rec["unread_reply"] = unread.decode(errors="replace")[:4000]
    rec["journal_at_kill"] = journal_rows(journal)
    oracle("after_kill")
    time.sleep(1.0)
    oracle("after_settle")

    at_kill = [r["state"] for r in rec["journal_at_kill"]]
    if trigger is None or (case == "B" and (trigger != "row_dispatching" or at_kill != ["dispatching"])):
        rec["verdict"] = "inconclusive"
        rec["reason"] = (
            f"kill did not land in the intended phase (trigger={trigger}, journal at kill={at_kill})"
        )
        return rec

    second = Server(a.scope, journal, log)
    try:
        status = second.tool("status", {})
        rec["status"] = status
        listed = [
            r
            for r in (status.get("unresolved") or []) + (status.get("recent") or [])
            if r.get("client_token") == token
        ]
        op = listed[0] if listed else None
        rec["listed"] = op
        before_repeat = oracle("before_repeat")
        repeat = second.tool("act", {"target": target, "text": a.expected_value, "client_token": token})
        rec["repeat"] = repeat
        after_repeat = oracle("after_repeat")
        busy = None
        unresolved = op is not None and op.get("state") in ("dispatching", "unknown")
        if unresolved:
            bound = second.tool("bind", {"name": "destination"})
            fresh = second.tool("observe", {"resource": bound["resource"]})
            busy = second.tool("act", {"target": destination_target(fresh), "text": a.expected_value})
            rec["tokenless"] = busy
            oracle("after_tokenless")
        final = oracle("final")
    finally:
        second.stop()

    rec["verdict"], rec["reason"] = judge(
        case, op, repeat, busy, unresolved, before_repeat, after_repeat, final
    )
    return rec


def judge(
    case: str,
    op: dict[str, Any] | None,
    repeat: dict[str, Any],
    busy: dict[str, Any] | None,
    unresolved: bool,
    before_repeat: int | None,
    after_repeat: int | None,
    final: int | None,
) -> tuple[str, str]:
    if op is None:
        return "against", "restarted status does not list the operation"
    if repeat.get("operation_id") != op.get("operation_id") or not repeat.get("repeat"):
        return "against", "same-token act did not return the original operation"
    if after_repeat is None or before_repeat is None or after_repeat != before_repeat:
        return "against", "same-token act changed the document"
    if unresolved:
        error = (busy or {}).get("error") or {}
        if not (busy and busy.get("is_error") and error.get("code") == "busy"):
            return "against", "tokenless act proceeded while the operation was unresolved"
        if error.get("operation_id") != op.get("operation_id"):
            return "against", "busy refusal names a different operation"
    if case == "A":
        if not unresolved and op.get("disposition") != "applied":
            return "against", f"case A operation finished as {op.get('disposition')}, not applied"
        if final != 1:
            return "against", f"value present {final} times, expected exactly once"
    else:
        if op.get("disposition") != "unknown" or op.get("phase") != "ambiguous":
            return (
                "against",
                f"case B recorded as {op.get('disposition')}/{op.get('phase')}, not unknown/ambiguous",
            )
        if final not in (0, 1):
            return "against", f"value present {final} times"
    return "held", "all predicted observations made"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scope", type=Path, required=True)
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--expected-value", required=True)
    ap.add_argument("--start-text", required=True)
    ap.add_argument("--cases", default="A,B")
    ap.add_argument("--execute", action="store_true")
    a = ap.parse_args(argv)
    a.scope = a.scope.resolve()
    dest = json.loads(a.scope.read_text())["destination"]
    a.pid, a.document = int(dest["pid"]), str(dest["document"])
    cases = [c for c in a.cases.split(",") if c in ("A", "B")]
    if not a.execute:
        for c in cases:
            print(
                f"[dry-run] case {c}: AX reset {a.document!r}; start server; bind source+destination; "
                f"act(token={TOKEN.format(case=c)!r}) unread; kill on "
                f"{'first AX field change' if c == 'A' else 'first durable dispatching row'}; restart on the same "
                "journal; status(); same-token act; if unresolved: fresh bind/observe + tokenless act; AX oracle each step"
            )
        return 0
    out = a.run_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    results = []
    for c in cases:
        rec = run_case(c, a, out)
        (out / f"case-{c}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        results.append({"case": c, "verdict": rec["verdict"], "reason": rec.get("reason")})
        print(f"case {c}: {rec['verdict']} ({rec.get('reason')})")
    (out / "summary.json").write_text(json.dumps({"prediction": "CS3", "cases": results}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
