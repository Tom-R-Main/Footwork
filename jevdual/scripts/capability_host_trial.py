"""CS2 host trial: fresh Claude Code sessions that may use only the four Footwork capability tools.

Preregistered in docs/notebook/2026-10-09-capability-slice.md (CS2). Each session gets a fresh journal and
MCP config under the run directory, and an empty working directory outside the home directory, so no
CLAUDE.md, AGENTS.md or project memory can give it repository context. Built-in tools are disabled, setting
sources are cleared and hooks disabled. The fixture (served page, TextEdit document, scope.json) is
prepared beforehand by whoever runs the trial.

Without ``--execute`` the script only prints what it would do: no OS, app or model activity.

The oracle is independent of Footwork. It reads the destination window's accessibility tree directly
through PyObjC (no ``jevdual`` import): the window whose AXDocument is the scoped file, its unique
AXTextArea, and that element's exact AXValue. The reset before each session sets that AXValue on the
already-open document, so no Apple Events or app file access are involved (TextEdit is sandboxed), and the
oracle must read every reset back before anything is spent. A session completes
only if the AX text equals the starting text followed by the expected value, exactly. The journal is
read with plain sqlite3 for CS2's second criterion (one ``applied`` operation whose readback passed).

The machine verdict covers the environment, process, oracle, journal and repairs. Whether the agent's
final message actually claims completion is reviewed by a person afterwards, recorded as
``claim_review``. CS2 cannot be ``held`` until every counted session has a passing review. The run
stops at the first failed prerequisite or invalid environment; invalid sessions are not retried.

    uv run python scripts/capability_host_trial.py --scope RUN/scope.json --run-dir RUN \
        --expected-value 1,284.50 --start-text $'Invoice report\\n' --model claude-sonnet-5-5 --effort high
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

TASK = (
    "Read the invoice total shown on the source page and append exactly that total — nothing else — "
    "to the destination document. Tell me when it is done and how you know."
)
SERVER = "footwork"
TOOLS = tuple(f"mcp__{SERVER}__{t}" for t in ("bind", "observe", "act", "status"))
REPAIR_CODES = ("invalid_arguments", "unsupported_move", "stale_target", "unknown_tool")
MAX_REPAIRS = 2
MAX_SESSIONS = 3
MAX_BUDGET_USD = 5.0
SESSION_TIMEOUT_S = 900
#: no hooks; setting sources are cleared separately, so user/project settings cannot add any
SETTINGS = {"disableAllHooks": True}


class OracleError(Exception):
    pass


# ---- independent accessibility oracle -----------------------------------------------------------


def _ax(el: Any, attr: str) -> Any:
    from ApplicationServices import AXUIElementCopyAttributeValue

    err, value = AXUIElementCopyAttributeValue(el, attr, None)
    return None if err else value


def _document_path(window: Any) -> str | None:
    url = _ax(window, "AXDocument")
    if not url:
        return None
    parts = urlsplit(str(url))
    return unquote(parts.path) if parts.scheme == "file" else None


def _text_areas(el: Any, depth: int = 0) -> list[Any]:
    if depth > 12:
        return []
    found = [el] if _ax(el, "AXRole") == "AXTextArea" else []
    for child in _ax(el, "AXChildren") or []:
        found += _text_areas(child, depth + 1)
    return found


def _scoped_text_area(pid: int, document: str) -> Any:
    """The one AXTextArea in the window of ``pid`` whose AXDocument is ``document``."""
    from ApplicationServices import AXUIElementCreateApplication

    want = os.path.realpath(document)
    windows = [
        w
        for w in _ax(AXUIElementCreateApplication(pid), "AXWindows") or []
        if (p := _document_path(w)) and os.path.realpath(p) == want
    ]
    if len(windows) != 1:
        raise OracleError(f"{len(windows)} windows of pid {pid} show {document}")
    areas = _text_areas(windows[0])
    if len(areas) != 1:
        raise OracleError(f"{len(areas)} text areas in the scoped window")
    return areas[0]


def ax_document_text(pid: int, document: str) -> str:
    """The exact AXValue of the scoped document's text area."""
    value = _ax(_scoped_text_area(pid, document), "AXValue")
    if not isinstance(value, str):
        raise OracleError("the text area has no string value")
    return str(value)


def ax_reset_text(pid: int, document: str, text: str) -> None:
    """Set the open document's text through accessibility: no Apple Events, no file access by the app."""
    from ApplicationServices import AXUIElementSetAttributeValue

    err = AXUIElementSetAttributeValue(_scoped_text_area(pid, document), "AXValue", text)
    if err:
        raise OracleError(f"AXValue reset failed with AX error {err}")


# ---- host session -------------------------------------------------------------------------------


def mcp_config(scope: Path, journal: Path) -> dict[str, Any]:
    return {
        "mcpServers": {
            SERVER: {
                "command": sys.executable,
                "args": [
                    "-m",
                    "jevdual.capability.mcp_server",
                    "--scope",
                    str(scope),
                    "--journal",
                    str(journal),
                ],
            }
        }
    }


def claude_argv(config: Path, *, model: str, effort: str, budget: float) -> list[str]:
    return [
        "claude",
        "-p",
        "--strict-mcp-config",
        "--mcp-config",
        str(config),
        "--setting-sources",
        "",
        "--settings",
        json.dumps(SETTINGS),
        "--tools",
        "",
        "--allowedTools",
        ",".join(TOOLS),
        "--model",
        model,
        "--effort",
        effort,
        "--max-budget-usd",
        str(budget),
        "--no-session-persistence",
        "--output-format",
        "stream-json",
        "--verbose",
    ]


def run_session(cmd: list[str], cwd: Path, transcript: Path) -> tuple[int | None, str, bool]:
    """Run one host session in its own process group, so a timeout also ends the MCP server it started."""
    with transcript.open("w") as out:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=out,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            start_new_session=True,
        )
        try:
            _, err = proc.communicate(TASK, timeout=SESSION_TIMEOUT_S)
            return proc.returncode, err, False
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                _, err = proc.communicate(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                _, err = proc.communicate()
            return proc.returncode, err, True


def read_transcript(path: Path) -> dict[str, Any]:
    """What the stream-json transcript records; nothing is inferred when its init event is missing."""
    events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), None)
    tools = sorted((init or {}).get("tools") or [])
    servers = sorted(s.get("name", "") for s in (init or {}).get("mcp_servers") or [])
    calls: list[str] = []
    repairs = 0
    for e in events:
        for block in (e.get("message") or {}).get("content") or []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                calls.append(block.get("name", ""))
            elif block.get("type") == "tool_result" and block.get("is_error"):
                text = json.dumps(block.get("content"))
                repairs += any(code in text for code in REPAIR_CODES)
    result = next((e for e in reversed(events) if e.get("type") == "result"), None)
    return {
        "init_event_present": init is not None,
        "valid_environment": init is not None and tools == sorted(TOOLS) and servers == [SERVER],
        "tools_offered": tools,
        "mcp_servers": servers,
        "model_reported": (init or {}).get("model"),
        "tool_calls": calls,
        "non_footwork_calls": [c for c in calls if c not in TOOLS],
        "argument_repairs": repairs,
        "result_event_present": result is not None,
        "final_text": str((result or {}).get("result") or "")[:4000],
        "result_is_error": bool((result or {}).get("is_error", True)),
        "result_subtype": (result or {}).get("subtype"),
        "cost_usd": (result or {}).get("total_cost_usd"),
        "model_usage": (result or {}).get("modelUsage"),
    }


def read_journal(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"operations": 0, "applied_with_passed_readback": 0, "unresolved": 0, "ids": []}
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    rows = db.execute("SELECT id, disposition, state, evidence FROM operations").fetchall()
    db.close()
    applied = sum(
        1
        for _, disposition, _, evidence in rows
        if disposition == "applied"
        and (json.loads(evidence or "{}").get("readback") or {}).get("passed") is True
    )
    return {
        "operations": len(rows),
        "applied_with_passed_readback": applied,
        "unresolved": sum(1 for _, _, state, _ in rows if state in ("dispatching", "unknown")),
        "ids": [r[0] for r in rows],
    }


def machine_verdict(session: dict[str, Any]) -> str:
    """``invalid`` sessions are reported, not counted; ``machine_held`` still needs its claim review."""
    t, j = session["transcript"], session["journal"]
    if not t["valid_environment"]:
        return "invalid"
    ok = (
        session["exit_code"] == 0
        and not session["timed_out"]
        and t["result_event_present"]
        and not t["result_is_error"]
        and t["final_text"].strip() != ""
        and session["oracle"]["exact"]
        and j["operations"] == 1
        and j["applied_with_passed_readback"] == 1
        and not t["non_footwork_calls"]
        and t["argument_repairs"] <= MAX_REPAIRS
    )
    return "machine_held" if ok else "against"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scope", type=Path, required=True)
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--expected-value", required=True)
    ap.add_argument("--start-text", required=True)
    ap.add_argument("--sessions", type=int, default=MAX_SESSIONS)
    ap.add_argument("--model", required=True)
    ap.add_argument("--effort", required=True)
    ap.add_argument("--budget", type=float, default=MAX_BUDGET_USD)
    ap.add_argument("--execute", action="store_true", help="actually reset the document and run the sessions")
    a = ap.parse_args(argv)
    if not 1 <= a.sessions <= MAX_SESSIONS or not 0 < a.budget <= MAX_BUDGET_USD:
        ap.error(f"at most {MAX_SESSIONS} sessions and ${MAX_BUDGET_USD} each (preregistered bounds)")

    scope = a.scope.resolve()
    dest = json.loads(scope.read_text())["destination"]
    pid, document = int(dest["pid"]), str(dest["document"])
    run_dir = a.run_dir.resolve()
    expected = a.start_text + a.expected_value
    results: list[dict[str, Any]] = []
    stopped = None
    for n in range(1, a.sessions + 1):
        sdir = run_dir / f"s{n}"
        config, journal, transcript = sdir / "mcp.json", sdir / "operations.sqlite", sdir / "transcript.jsonl"
        cmd = claude_argv(config, model=a.model, effort=a.effort, budget=a.budget)
        if not a.execute:
            print(
                f"[dry-run] session {n}: reset {document!r} to {a.start_text!r}; AX oracle must read it back"
            )
            print(
                f"[dry-run]   cwd: fresh empty dir under {tempfile.gettempdir()} (outside the home directory)"
            )
            print(f"[dry-run]   {' '.join(repr(c) if not c or ' ' in c else c for c in cmd)} <<< {TASK!r}")
            print(f"[dry-run]   oracle: AX text of pid {pid}'s window for that document == {expected!r}")
            continue
        sdir.mkdir(parents=True, exist_ok=False)
        config.write_text(json.dumps(mcp_config(scope, journal), indent=1))
        try:
            ax_reset_text(pid, document, a.start_text)
            time.sleep(0.5)
            if ax_document_text(pid, document) != a.start_text:
                raise OracleError("the AX oracle does not read the reset text back")
        except OracleError as exc:
            stopped = f"session {n}: prerequisite failed before any spend: {exc}"
            break
        cwd = Path(tempfile.mkdtemp(prefix=f"footwork-cs2-s{n}-"))
        if os.path.realpath(cwd).startswith(os.path.realpath(Path.home())):
            stopped = f"session {n}: cwd {cwd} is under the home directory; refusing to run"
            break
        t0 = time.monotonic()
        code, err, timed_out = run_session(cmd, cwd, transcript)
        try:
            text, oracle_error = ax_document_text(pid, document), None
        except OracleError as exc:
            text, oracle_error = None, str(exc)
        session = {
            "session": n,
            "cwd": str(cwd),
            "exit_code": code,
            "timed_out": timed_out,
            "wall_s": round(time.monotonic() - t0, 1),
            "oracle": {"exact": text == expected, "text": text, "expected": expected, "error": oracle_error},
            "transcript": read_transcript(transcript),
            "journal": read_journal(journal),
            "claim_review": None,  # filled in by a person: does the final message claim completion, truthfully?
        }
        session["machine_verdict"] = machine_verdict(session)
        (sdir / "session.json").write_text(json.dumps(session, indent=1, ensure_ascii=False))
        (sdir / "stderr.txt").write_text(err or "")
        results.append(session)
        print(f"session {n}: {session['machine_verdict']} (oracle exact={session['oracle']['exact']})")
        if session["machine_verdict"] == "invalid":
            stopped = f"session {n}: invalid environment; stopping without retry"
            break
    if not a.execute:
        return 0
    verdicts = [s["machine_verdict"] for s in results]
    summary = {
        "prediction": "CS2",
        "task": TASK,
        "model": a.model,
        "effort": a.effort,
        "sessions": [{"session": s["session"], "machine_verdict": s["machine_verdict"]} for s in results],
        "stopped": stopped,
        "cs2_machine": "against"
        if "against" in verdicts
        else "pending_claim_review"
        if len(verdicts) == a.sessions and set(verdicts) == {"machine_held"}
        else "inconclusive",
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    return 0 if stopped is None else 2


if __name__ == "__main__":
    raise SystemExit(main())
