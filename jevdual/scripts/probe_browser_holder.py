"""Probe for notebook prediction BH1: does the session browser holder let later commands run in the background?

Starts a ``start --browser`` session on an owned local fixture page in a Chrome that Footwork launches
into an isolated profile and port, restores the application that was frontmost before the launch,
then runs ``look`` and ``do click`` on the fixture's counter, each as its own process, while a
sampler records every change of the frontmost application. Arm ``held`` uses the holder (the
default); arm ``control`` sets ``FOOTWORK_BROWSER_HOLDER=0`` so each command builds its own driver.

Waits for an unlocked screen and at least 10 s without input before launching, because the launch
brings Chrome forward. Sends no input to any other application. At the end it stops the holder and
terminates the isolated Chrome it launched.

Run from ``jevdual/`` with the pinned driver overlay first on ``PYTHONPATH``::

    FOOTWORK_CHROME_PROFILE=/abs/fresh/profile FOOTWORK_CHROME_PORT=9466 \\
    PYTHONPATH=output/foreground-helptag/overlay:python \\
    .venv/bin/python scripts/probe_browser_holder.py --arm held --out /abs/out/dir

Refuses to run against Footwork's default profile or port, or the sign-in test's.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import probe_page_effects
from probe_page_effects import _front, _serve

#: BH7 adds an empty field to the fixture, before its script
NOTE_FIELD = '<p><label>Note <input id="note" size="30"></label></p>\n<script>'

PROTECTED_PORTS = {"9333", "9555"}
PROTECTED_PROFILES = {Path.home() / ".config/jevdual/chrome-profile", Path.home() / ".config/jevdual/chrome-profile-signin"}


def _front_pid() -> int | None:
    """The frontmost application's process ID: two Chromes share one application name."""
    try:
        asn = subprocess.run(["lsappinfo", "front"], capture_output=True, text=True, timeout=2, check=False).stdout.strip()
        out = subprocess.run(["lsappinfo", "info", "-only", "pid", asn], capture_output=True, text=True, timeout=2,
                             check=False).stdout
        match = re.search(r"=\s*(\d+)", out)
        return int(match.group(1)) if match else None
    except (OSError, subprocess.SubprocessError):
        return None


def _sample_front(out: Path, stop: threading.Event) -> None:
    """Every change of the frontmost process, with the sample count and largest gap at the end."""
    last, samples, largest_gap, previous = None, 0, 0.0, time.time()
    with (out / "front-app.jsonl").open("a") as stream:
        while not stop.is_set():
            pid = _front_pid()
            now = time.time()
            samples += 1
            largest_gap = max(largest_gap, now - previous)
            previous = now
            if pid != last:
                stream.write(json.dumps({"t": now, "front_pid": pid}) + "\n")
                stream.flush()
                last = pid
        stream.write(json.dumps({"t": time.time(), "samples": samples, "largest_gap_s": round(largest_gap, 4)}) + "\n")


def _activate_pid(pid: int) -> None:
    script = f'tell application "System Events" to set frontmost of (first process whose unix id is {pid}) to true'
    subprocess.run(["osascript", "-e", script], capture_output=True, timeout=10, check=False)


def _idle_s() -> float:
    out = subprocess.run(["ioreg", "-c", "IOHIDSystem", "-d", "4"], capture_output=True, text=True, check=False).stdout
    match = re.search(r'"HIDIdleTime" = (\d+)', out)
    return int(match.group(1)) / 1e9 if match else 0.0


def _locked() -> bool:
    out = subprocess.run(["ioreg", "-n", "Root", "-d1", "-a"], capture_output=True, text=True, check=False).stdout
    return "<key>CGSSessionScreenIsLocked</key>\n\t<true/>" in out


def _wait_idle(minimum: float = 10.0, limit_s: float = 3600.0) -> dict:
    start, polls = time.time(), 0
    while time.time() - start < limit_s:
        polls += 1
        idle = _idle_s()
        if idle >= minimum and not _locked():
            return {"polls": polls, "idle_s": round(idle, 1), "waited_s": round(time.time() - start, 1)}
        time.sleep(5)
    raise SystemExit("never idle and unlocked within the limit")


def _cli(env: dict, out: Path, name: str, *argv: str) -> dict:
    started = time.time()
    proc = subprocess.run([sys.executable, "-m", "jevdual.cli", *argv], capture_output=True, text=True,
                          env=env, timeout=120, check=False)
    (out / f"{name}.stdout").write_text(proc.stdout)
    (out / f"{name}.stderr").write_text(proc.stderr)
    return {"name": name, "t_start": started, "t_end": time.time(), "exit": proc.returncode,
            "stdout": proc.stdout, "stderr": proc.stderr}


def _counter_id(text: str) -> int | None:
    match = re.search(r"\[\s*(\d+)\]\s+button\s+'Count clicks'", text)
    return int(match.group(1)) if match else None


def _field_id(text: str, label: str) -> int | None:
    match = re.search(rf"\[\s*(\d+)\]\s+\w+\s+'{label}'", text)
    return int(match.group(1)) if match else None


def _field_value(text: str, label: str) -> str | None:
    match = re.search(rf"\[\s*\d+\]\s+\w+\s+'{label}' = '([^']*)'", text)
    return match.group(1) if match else None


def _typing(env: dict, out: Path, session: Path, rounds: int, spacing: float, steps: list[dict]) -> dict:
    """BH7: appends to Name, a type into the empty Note, then a type into Note that holds text."""
    def look(name: str) -> dict:
        step = _cli(env, out, name, "look", "--session", str(session))
        steps.append(step)
        return step

    for i in range(1, rounds + 1):
        seen = look(f"{i:02d}-look")
        name_id = _field_id(seen["stdout"], "Name")
        steps.append(_cli(env, out, f"{i:02d}-append", "do", "append", str(name_id), f" +{i}", "--no-judge",
                          "--session", str(session)) if name_id is not None else {"name": f"{i:02d}-append", "skipped": "no Name"})
        time.sleep(spacing)
    for name, text in (("type-empty", "first note"), ("type-held", "second")):
        seen = look(f"{name}-look")
        note_id = _field_id(seen["stdout"], "Note")
        steps.append(_cli(env, out, name, "do", "type", str(note_id), text, "--no-judge", "--session", str(session))
                     if note_id is not None else {"name": name, "skipped": "no Note"})
        time.sleep(3.0)
    final = look("final-look")
    return {"name": _field_value(final["stdout"], "Name"), "note": _field_value(final["stdout"], "Note")}


def _tab(session: Path) -> str | None:
    try:
        return json.loads((session / "session.json").read_text()).get("browser_tab")
    except (OSError, ValueError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--arm", choices=("held", "control"), required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--spacing", type=float, default=25.0, help="seconds between rounds")
    parser.add_argument("--typing", action="store_true", help="BH7: append and type instead of clicking")
    args = parser.parse_args()
    out = Path(args.out)
    if not out.is_absolute():
        raise SystemExit("--out must be absolute")
    port = os.environ.get("FOOTWORK_CHROME_PORT", "9333")
    profile = Path(os.environ.get("FOOTWORK_CHROME_PROFILE", str(Path.home() / ".config/jevdual/chrome-profile")))
    if port in PROTECTED_PORTS or profile in PROTECTED_PROFILES:
        raise SystemExit("refusing to run against a protected profile or port; set both overrides")
    out.mkdir(parents=True, exist_ok=True)
    session = out / "session"
    env = {**os.environ, "FOOTWORK_BROWSER_HOLDER": "1" if args.arm == "held" else "0"}

    if args.typing:
        probe_page_effects.FIXTURE = probe_page_effects.FIXTURE.replace("<script>", NOTE_FIELD, 1)
    server, fixture_port = _serve(out)
    url = f"http://127.0.0.1:{fixture_port}/"
    gate = _wait_idle()
    front_at_start = _front()
    front_pid_at_start = _front_pid()
    stop = threading.Event()
    sampler = threading.Thread(target=_sample_front, args=(out, stop), daemon=True)
    sampler.start()
    steps: list[dict] = []
    record = {"arm": args.arm, "port": port, "profile": str(profile), "gate": gate,
              "front_at_start": front_at_start, "front_pid_at_start": front_pid_at_start, "fixture": url, "steps": steps}
    try:
        steps.append(_cli(env, out, "00-start", "start", "probe the browser holder", "--browser", "--url", url,
                          "--session", str(session)))
        steps[-1]["tab"] = _tab(session)
        time.sleep(1.0)
        if front_pid_at_start and _front_pid() != front_pid_at_start:
            _activate_pid(front_pid_at_start)
        time.sleep(5.0)
        from jevdual.browser_driver import chrome_pid as _owned_pid

        record["restored"] = {"t": time.time(), "front": _front(), "front_pid": _front_pid(),
                              "owned_chrome_pid": _owned_pid()}
        if args.typing:
            record["final_values"] = _typing(env, out, session, args.rounds, args.spacing, steps)
        for i in range(1, 0 if args.typing else args.rounds + 1):
            look = _cli(env, out, f"{i:02d}-look", "look", "--session", str(session))
            look["tab"] = _tab(session)
            steps.append(look)
            target = _counter_id(look["stdout"])
            if target is None:
                steps.append({"name": f"{i:02d}-click", "skipped": "counter not on the observation"})
            else:
                click = _cli(env, out, f"{i:02d}-click", "do", "click", str(target), "--no-judge",
                             "--session", str(session))
                click["tab"] = _tab(session)
                steps.append(click)
            if args.arm == "control" and look["exit"] != 0:
                break  # the prediction concerns the first background command; do not keep relaunching
            if i < args.rounds:
                time.sleep(args.spacing)
    finally:
        record["finished"] = time.time()
        from jevdual import browser_session_holder as bsh

        record["holder_stop"] = asyncio.run(bsh.stop_async(session)) if args.arm == "held" else None
        time.sleep(1.0)
        from jevdual.browser_driver import chrome_pid

        pid = chrome_pid()
        record["chrome_pid"] = pid
        if pid:
            os.kill(pid, signal.SIGTERM)
        stop.set()
        sampler.join(timeout=5)
        server.shutdown()
        for step in steps:
            step.pop("stdout", None)
            step["stderr"] = (step.get("stderr") or "")[-400:]
        (out / "run.json").write_text(json.dumps(record, indent=1))


if __name__ == "__main__":
    main()
