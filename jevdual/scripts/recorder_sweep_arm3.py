#!/usr/bin/env python3
"""Arm 3 of the recorder-refusal sweep (notebook DGR2): a Footwork filmed session that parks during takes.

Local commands for the sweep's own cycle runner. None calls a model or the network; each runs the
installed ``footwork`` and appends JSON lines to ``<out>/arm3.jsonl``. Standard library only.

    recorder_sweep_arm3.py start --out /abs/dir --pid CHROME_PID (--window TITLE | --window-id ID)
    recorder_sweep_arm3.py park  --out /abs/dir          # once per take, while the recorder runs
    recorder_sweep_arm3.py end   --out /abs/dir
    recorder_sweep_arm3.py watch --out /abs/dir --handshake /abs/dir (--until HH:MM | --go-file PATH)

``start`` checks that the installed release is the one the sweep names, waits for an unlocked screen
with 10 s of no human input, starts a native ``exclusive_desktop`` filmed session on that window and
parks once at the rest position. ``park`` moves the real pointer through the sweep's screen points in
turn, one move about every 2.5 s for ``--seconds``, as the glide arm does, and stops at the first
refusal. ``end`` yields the session's desktop reservation and records whether any Footwork process is
left. ``watch`` is the file handshake: it waits for ``arm3-request``, reads ``target.json``, runs
``start`` and writes ``arm3-up`` (or ``arm3-failed``), then waits for ``arm3-done``, runs ``end`` and
writes ``arm3-down``. With ``--go-file`` it does nothing until that file is written after the watch began;
the file holds the grant's end time. It serves one request, starts no session at or after the end
time, and ends a session it started when the runner says so or at the end time, whichever is first.
Exit codes: 0 done; 3 the installed release differs; 4 Footwork refused; 5 the screen stayed locked
or busy; 6 the watch ran out of time; 2 a usage error.
"""
from __future__ import annotations

import argparse
import json
import os
import plistlib
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

RELEASE = Path.home() / ".local/share/footwork/current/footwork-release.json"
#: the release installed during DGR1's incidents; arm 3 measures this one
EXPECTED = {"source_commit": "6d571a1ed7c7bf77576279a01053f77fc20ce469",
            "cua-driver": "0.46.0+footwork.5486b624.cleanup2.focus1"}
TASK = "Recorder sweep arm 3: park the pointer during each take"
#: the glide arm's screen points (DemoGeek sweep.zsh PTS), visited in turn
SCREEN_POINTS = "420,380;980,520;640,300;1100,700;520,640;860,360"
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
    if len(points) < 2 or any(len(p) != 2 for p in points):
        raise ValueError("--screen-points needs at least two X,Y pairs separated by semicolons")
    return points  # type: ignore[return-value]


def cmd_start(args: argparse.Namespace, out: Path) -> int:
    if (out / "arm3.jsonl").exists():
        print(f"{out} already holds an arm 3 log; use a fresh directory", file=sys.stderr)
        return 2
    try:
        points = _points(args.screen_points)
        rest = tuple(float(v) for v in args.rest.split(","))
        if len(rest) != 2:
            raise ValueError("--rest needs X,Y")
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    found = installed(Path(args.release_json))
    record = {"kind": "start", "installed": found, "expected": EXPECTED, "footwork": args.footwork,
              "pid": args.pid, "window_id": args.window_id, "screen_points": points, "rest": rest,
              "leftover_before": leftover()}
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
    deadline = getattr(args, "deadline", None)
    if deadline is not None and time.time() >= deadline:
        _log(out, {**record, "outcome": "grant_expired"})
        print("the grant's end time has passed; nothing started", file=sys.stderr)
        return 6
    window = ["--window-id", str(args.window_id)] if args.window_id else ["--window", args.window]
    started = _run([args.footwork, "start", TASK, "--app", args.app, "--pid", str(args.pid), *window,
                    "--mode", "exclusive_desktop", "--pointer-motion", "filmed", "--rest", args.rest,
                    "--session", str(out / "session")], timeout=80.0)
    record["footwork_start"] = started
    if started["exit"] != 0:
        _log(out, {**record, "outcome": "start_refused"})
        print(f"footwork start refused (exit {started['exit']}): {started['stderr'][-300:]}", file=sys.stderr)
        return 4
    first = _run([args.footwork, "park", "--session", str(out / "session")], timeout=20.0)
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
    if args.pid is not None and (args.pid, args.window_id) != (start["pid"], start["window_id"]):
        _log(out, {"kind": "park_mismatch", "given": [args.pid, args.window_id], "bound": [start["pid"], start["window_id"]]})
        print("the window given is not the one this session is bound to", file=sys.stderr)
        return 2
    try:
        origin = json.loads((out / "session/session.json").read_text())["filmed"]["content"][:2]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        _log(out, {"kind": "park_unreadable", "error": f"{type(exc).__name__}: {exc}"})
        print("the session has no filmed content origin", file=sys.stderr)
        return 4
    stop = {"now": False}
    signal.signal(signal.SIGTERM, lambda *_: stop.update(now=True))  # finish and log the move under way
    points = start["screen_points"]
    n = sum(1 for r in records if r.get("kind") == "park")
    take = len({r.get("take") for r in records if r.get("kind") == "park"}) + 1
    began, moves = time.time(), 0
    while not stop["now"] and time.time() - began < args.seconds:
        step = time.time()
        sx, sy = points[n % len(points)]
        x, y = sx - origin[0], sy - origin[1]
        result = _run([args.footwork, "park", f"{x:g}", f"{y:g}", "--session", str(out / "session")], timeout=20.0)
        n, moves = n + 1, moves + 1
        _log(out, {"kind": "park", "n": n, "take": take, "screen": [sx, sy], "viewport": [x, y], **result})
        if result["exit"] != 0:
            print(f"take {take}: park {n} refused (exit {result['exit']}): {result['stderr'][-300:]}", file=sys.stderr)
            return 4
        pause = args.interval - (time.time() - step)
        while pause > 0 and not stop["now"] and time.time() - began < args.seconds:
            time.sleep(min(0.1, pause))
            pause -= 0.1
    print(f"take {take}: {moves} parks in {time.time() - began:.1f} s")
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
    print(json.dumps({**{k: summary[k] for k in ("parks", "parks_refused", "live_reservations", "leftover_after")},
                      "clean": clean}))
    return 0 if clean else 4


def _write(path: Path, payload: dict) -> None:
    """Appear whole: the runner polls for the file's existence."""
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload) + "\n")
    temporary.replace(path)


def _clock(raw: str, after: float) -> float:
    """The first HH:MM (this machine's clock) at or after ``after``, as epoch seconds."""
    hour, minute = (int(v) for v in raw.strip().split(":"))
    day = time.localtime(after)
    at = time.mktime((day.tm_year, day.tm_mon, day.tm_mday, hour, minute, 0, 0, 0, -1))
    if at < after:
        at += 86400
    # an end time more than twelve hours off is one that has already passed today
    return at if at - after <= 12 * 3600 else after


def _fresh(path: Path, since: float) -> bool:
    """A handshake file the runner wrote after this watch began (its content is ``date +%s``)."""
    try:
        return int(path.read_text().strip()) >= int(since) - 2
    except (OSError, ValueError):
        return False


def _grant(go_file: Path, began: float) -> tuple[float | None, dict]:
    """The end time a go file grants, with what was read. Only a file written after this watch began
    counts (an earlier one belongs to another sweep), and only an end time within three hours of it."""
    try:
        written = go_file.stat().st_mtime
        text = go_file.read_text().strip()
    except OSError:
        return None, {}
    seen = {"go_file_written": written, "go_file_text": text[:20]}
    if written < began:
        return None, {**seen, "ignored": "written before this watch began"}
    try:
        until = _clock(text, written)
    except ValueError:
        return None, {**seen, "ignored": "not HH:MM"}
    if not 0 < until - written <= 3 * 3600:
        return None, {**seen, "ignored": "end time is not within three hours after the go"}
    return until, seen


def cmd_watch(args: argparse.Namespace, out: Path) -> int:
    """One sweep's arm 3, once: wait for the go and the runner's request, start, wait, end."""
    handshake = Path(args.handshake)
    began = time.time()
    out.mkdir(parents=True, exist_ok=True)

    def note(event: str, **more: object) -> None:
        _write(out / f"watch-{event}.json", {"t": time.time(), **more})

    go_file = Path(args.go_file) if args.go_file else None
    note("began", pid_of_watch=os.getpid(), until=args.until, go_file=args.go_file,
         stale_go_file=bool(go_file and go_file.exists()))
    until = _clock(args.until, began) if args.until else None
    granted_at, grant = began, {}
    while True:  # wait for the go (when it comes by file) and then the runner's request
        if until is None and go_file is not None:
            until, grant = _grant(go_file, began)
            if until is not None:
                granted_at = grant["go_file_written"]
                note("granted", until=until, **grant)
        if until is not None and time.time() >= until:
            note("expired", waiting_for="arm3-request", **grant)
            return 6
        if until is not None and _fresh(handshake / "arm3-request", granted_at):
            break
        if time.time() - began > args.max_wait:
            note("expired", waiting_for="go" if until is None else "arm3-request", **grant)
            return 6
        time.sleep(0.5)
    note("consumed", until=until, **grant)  # this watch serves this one request and no other
    try:
        target_file = handshake / "target.json"
        if target_file.stat().st_mtime < granted_at - 2:
            raise ValueError("it is older than the go, so it describes another run's window")
        target = json.loads(target_file.read_text())
        args.pid, args.window_id, args.window, args.app = int(target["pid"]), int(target["window_id"]), None, target["app"]
        os.kill(args.pid, 0)  # the process the target names is running
    except (OSError, ValueError, KeyError, TypeError) as exc:
        _write(handshake / "arm3-failed", {"t": time.time(), "why": f"target.json: {type(exc).__name__}: {exc}"[:200]})
        return 2
    args.deadline = until
    code = cmd_start(args, out)
    if code != 0:
        cmd_end(args, out)
        _write(handshake / "arm3-failed", {"t": time.time(), "why": f"start exit {code}", "log": str(out / "arm3.jsonl")})
        return code
    (handshake / "arm3-out").write_text(str(out) + "\n")  # where the in-take step finds this session
    _write(handshake / "arm3-up", {"t": time.time(), "pid": args.pid, "window_id": args.window_id,
                                   "until": until, "log": str(out / "arm3.jsonl")})
    # the session ends when the runner says the arm is over, and at the grant's end time at the latest
    while not _fresh(handshake / "arm3-done", granted_at) and time.time() < until:
        time.sleep(0.5)
    at_expiry = not _fresh(handshake / "arm3-done", granted_at)
    code = cmd_end(args, out)
    _write(handshake / "arm3-down", {"t": time.time(), "clean": code == 0, "ended_at_expiry": at_expiry})
    return 6 if at_expiry else code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("start", "park", "end", "watch"):
        p = sub.add_parser(name)
        p.add_argument("--out", required=True, help="absolute directory for this arm's session and log")
        p.add_argument("--footwork", default=str(Path.home() / ".local/bin/footwork"))
    for name in ("start", "watch"):
        st = sub.choices[name]
        st.add_argument("--app", default="Google Chrome")
        st.add_argument("--rest", default="120,120", help="X,Y in viewport CSS px")
        st.add_argument("--screen-points", default=SCREEN_POINTS, help="park points in screen points, X,Y;X,Y;...")
        st.add_argument("--idle", type=float, default=10.0)
        st.add_argument("--gate-limit", type=float, default=100.0)
        st.add_argument("--release-json", default=str(RELEASE))
    st = sub.choices["start"]
    st.add_argument("--pid", type=int, required=True, help="the throwaway Chrome's process")
    target = st.add_mutually_exclusive_group(required=True)
    target.add_argument("--window", help="window title substring")
    target.add_argument("--window-id", type=int, help="exact CGWindowID")
    pk = sub.choices["park"]
    pk.add_argument("--pid", type=int, help="checked against the window the session is bound to")
    pk.add_argument("--window-id", type=int)
    pk.add_argument("--seconds", type=float, default=18.0, help="start no move after this long")
    pk.add_argument("--interval", type=float, default=2.5, help="seconds from one move's start to the next")
    wt = sub.choices["watch"]
    wt.add_argument("--handshake", required=True, help="the runner's handshake directory")
    go = wt.add_mutually_exclusive_group(required=True)
    go.add_argument("--until", help="HH:MM on this machine's clock: start no session at or after it")
    go.add_argument("--go-file", help="act only once this file exists; it holds the HH:MM end time")
    wt.add_argument("--max-wait", type=float, default=4 * 3600.0, help="give up waiting after this many seconds")
    args = parser.parse_args()
    out = Path(args.out)
    if not out.is_absolute():
        print("--out must be absolute", file=sys.stderr)
        return 2
    return {"start": cmd_start, "park": cmd_park, "end": cmd_end, "watch": cmd_watch}[args.cmd](args, out)


if __name__ == "__main__":
    sys.exit(main())
