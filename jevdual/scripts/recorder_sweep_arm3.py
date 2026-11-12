#!/usr/bin/env python3
"""Arm 3 of the recorder-refusal sweep (notebook DGR2): a Footwork filmed session that parks during takes.

Three local commands for the sweep's own cycle runner. None calls a model or the network; each runs
the installed ``footwork`` and appends one JSON line to ``<out>/arm3.jsonl``. Standard library only.

    recorder_sweep_arm3.py start --out /abs/dir --pid CHROME_PID (--window TITLE | --window-id ID)
    recorder_sweep_arm3.py park  --out /abs/dir          # once per take, while the recorder runs
    recorder_sweep_arm3.py end   --out /abs/dir

``start`` checks that the installed release is the one the sweep names, waits for an unlocked screen
with 10 s of no human input, starts a native ``exclusive_desktop`` filmed session on that window and
parks once at the rest position. ``park`` moves the real pointer to the next of two points (viewport
CSS px), alternating. ``end`` yields the session's desktop reservation and records whether any
Footwork process is left. Exit codes: 0 done; 3 the installed release differs; 4 Footwork refused;
5 the screen stayed locked or busy; 2 a usage error.
"""
from __future__ import annotations

import argparse
import json
import plistlib
import re
import subprocess
import sys
import time
from pathlib import Path

RELEASE = Path.home() / ".local/share/footwork/current/footwork-release.json"
#: the release installed during DGR1's incidents; arm 3 measures this one
EXPECTED = {"source_commit": "6d571a1ed7c7bf77576279a01053f77fc20ce469",
            "cua-driver": "0.46.0+footwork.5486b624.cleanup2.focus1"}
TASK = "Recorder sweep arm 3: park the pointer during each take"
#: Footwork's own processes: the driver, the CLI and holder modules, and anything run from the release
LEFTOVER = r"cua-driver|cua_driver|jevdual\.cli|jevdual\.browser_session_holder|\.local/share/footwork/|\.local/bin/footwork"


def _log(out: Path, record: dict) -> dict:
    record = {"t": time.time(), **record}
    with (out / "arm3.jsonl").open("a") as stream:
        stream.write(json.dumps(record) + "\n")
    return record


def _records(out: Path) -> list[dict]:
    path = out / "arm3.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def _run(argv: list[str], timeout: float = 120.0) -> dict:
    started = time.time()
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
        code, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        code, stdout, stderr = 124, "", f"timed out after {timeout:.0f} s"
    except OSError as exc:
        code, stdout, stderr = 127, "", f"{type(exc).__name__}: {exc}"
    return {"t_start": started, "t_end": time.time(), "exit": code, "stdout": stdout[-600:], "stderr": stderr[-600:]}


def installed(release: Path) -> dict:
    """The installed release's commit and driver version, or the reason they cannot be read."""
    try:
        data = json.loads(release.read_text())
        return {"source_commit": data["source_commit"], "cua-driver": data["installed_files"]["cua-driver"]["version"]}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {"unreadable": f"{type(exc).__name__}: {exc}"}


def idle_s() -> float:
    out = subprocess.run(["ioreg", "-c", "IOHIDSystem", "-d", "4"], capture_output=True, text=True, check=False).stdout
    match = re.search(r'"HIDIdleTime" = (\d+)', out)
    return int(match.group(1)) / 1e9 if match else 0.0


def console_locked(ioreg_plist: bytes) -> bool:
    """Anything that does not read as an unlocked console session counts as locked."""
    try:
        users = plistlib.loads(ioreg_plist).get("IOConsoleUsers")
    except Exception:  # noqa: BLE001 - unreadable output is not evidence of an unlocked screen
        return True
    console = [u for u in users or [] if isinstance(u, dict) and u.get("kCGSSessionOnConsoleKey")]
    return not console or any(u.get("CGSSessionScreenIsLocked", False) is not False for u in console)


def gate(minimum: float, limit_s: float) -> dict | None:
    """Wait for an unlocked screen with ``minimum`` seconds of no input; None when the limit passes."""
    start = time.time()
    while True:
        idle = idle_s()
        locked = console_locked(subprocess.run(["ioreg", "-n", "Root", "-d1", "-a"], capture_output=True, check=False).stdout)
        if idle >= minimum and not locked:
            return {"idle_s": round(idle, 1), "waited_s": round(time.time() - start, 1)}
        if time.time() - start >= limit_s:
            return None
        time.sleep(2)


def leftover() -> list[str]:
    out = subprocess.run(["pgrep", "-fl", LEFTOVER], capture_output=True, text=True, check=False).stdout
    return [line[:200] for line in out.splitlines() if "recorder_sweep_arm3" not in line]


def _points(raw: str) -> list[tuple[float, float]]:
    points = [tuple(float(v) for v in pair.split(",")) for pair in raw.split(";")]
    if len(points) != 2 or any(len(p) != 2 for p in points):
        raise ValueError("--points needs two X,Y pairs separated by a semicolon")
    return points  # type: ignore[return-value]


def cmd_start(args: argparse.Namespace, out: Path) -> int:
    if (out / "arm3.jsonl").exists():
        print(f"{out} already holds an arm 3 log; use a fresh directory", file=sys.stderr)
        return 2
    try:
        points = _points(args.points)
        rest = tuple(float(v) for v in args.rest.split(","))
        if len(rest) != 2:
            raise ValueError("--rest needs X,Y")
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    found = installed(Path(args.release_json))
    record = {"kind": "start", "installed": found, "expected": EXPECTED, "footwork": args.footwork,
              "points": points, "rest": rest, "leftover_before": leftover()}
    if found != EXPECTED:
        _log(out, {**record, "outcome": "release_differs"})
        print(f"installed release {found} is not the one the sweep names {EXPECTED}; nothing started", file=sys.stderr)
        return 3
    passed = gate(args.idle, args.gate_limit)
    record["gate"] = passed
    if passed is None:
        _log(out, {**record, "outcome": "screen_locked_or_busy"})
        print("the screen stayed locked or in use; nothing started", file=sys.stderr)
        return 5
    window = ["--window-id", str(args.window_id)] if args.window_id else ["--window", args.window]
    started = _run([args.footwork, "start", TASK, "--app", "Google Chrome", "--pid", str(args.pid), *window,
                    "--mode", "exclusive_desktop", "--pointer-motion", "filmed", "--rest", args.rest,
                    "--session", str(out / "session")])
    record["footwork_start"] = started
    if started["exit"] != 0:
        _log(out, {**record, "outcome": "start_refused"})
        print(f"footwork start refused (exit {started['exit']}): {started['stderr'][-300:]}", file=sys.stderr)
        return 4
    first = _run([args.footwork, "park", "--session", str(out / "session")])
    _log(out, {**record, "first_park": first, "outcome": "started" if first["exit"] == 0 else "first_park_refused"})
    if first["exit"] != 0:
        print(f"the first park refused (exit {first['exit']}): {first['stderr'][-300:]}", file=sys.stderr)
        return 4
    print(f"arm 3 session started; parked at rest: {first['stdout'].strip()}")
    return 0


def cmd_park(args: argparse.Namespace, out: Path) -> int:
    records = _records(out)
    start = next((r for r in records if r.get("kind") == "start" and r.get("outcome") == "started"), None)
    if start is None:
        print(f"no started arm 3 session in {out}", file=sys.stderr)
        return 2
    n = sum(1 for r in records if r.get("kind") == "park") + 1
    x, y = start["points"][(n - 1) % 2]
    result = _run([args.footwork, "park", f"{x:g}", f"{y:g}", "--session", str(out / "session")], timeout=30.0)
    _log(out, {"kind": "park", "n": n, "point": [x, y], **result})
    if result["exit"] != 0:
        print(f"park {n} refused (exit {result['exit']}): {result['stderr'][-300:]}", file=sys.stderr)
        return 4
    print(f"park {n}: {result['stdout'].strip()}")
    return 0


def cmd_end(args: argparse.Namespace, out: Path) -> int:
    records = _records(out)
    token = ""
    try:
        token = json.loads((out / "session/session.json").read_text()).get("coordination_token", "")
    except (OSError, ValueError):
        pass
    yielded = _run([args.footwork, "control", "yield", token]) if token else None
    status = _run([args.footwork, "control", "status"])
    live = None
    try:
        live = [r for r in json.loads(status["stdout"])["reservations"] if r.get("state") not in ("revoked", "released")]
    except (ValueError, KeyError, TypeError):
        pass
    parks = [r for r in records if r.get("kind") == "park"]
    summary = {"kind": "end", "token_found": bool(token), "yield": yielded, "live_reservations": live,
               "parks": len(parks), "parks_refused": sum(1 for r in parks if r["exit"] != 0),
               "leftover_after": leftover()}
    _log(out, summary)
    clean = bool(token) and yielded is not None and yielded["exit"] == 0 and live == [] and not summary["leftover_after"]
    print(json.dumps({k: summary[k] for k in ("parks", "parks_refused", "live_reservations", "leftover_after")}
                     | {"clean": clean}))
    return 0 if clean else 4


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("start", "park", "end"):
        p = sub.add_parser(name)
        p.add_argument("--out", required=True, help="absolute directory for this arm's session and log")
        p.add_argument("--footwork", default=str(Path.home() / ".local/bin/footwork"))
    st = sub.choices["start"]
    st.add_argument("--pid", type=int, required=True, help="the throwaway Chrome's process")
    target = st.add_mutually_exclusive_group(required=True)
    target.add_argument("--window", help="window title substring")
    target.add_argument("--window-id", type=int, help="exact CGWindowID")
    st.add_argument("--rest", default="120,120", help="X,Y in viewport CSS px")
    st.add_argument("--points", default="220,200;520,320", help="the two park points, X,Y;X,Y in viewport CSS px")
    st.add_argument("--idle", type=float, default=10.0)
    st.add_argument("--gate-limit", type=float, default=300.0)
    st.add_argument("--release-json", default=str(RELEASE))
    args = parser.parse_args()
    out = Path(args.out)
    if not out.is_absolute():
        print("--out must be absolute", file=sys.stderr)
        return 2
    return {"start": cmd_start, "park": cmd_park, "end": cmd_end}[args.cmd](args, out)


if __name__ == "__main__":
    sys.exit(main())
