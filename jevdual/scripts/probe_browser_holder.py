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
from probe_page_effects import _front, _sample_front, _serve

PROTECTED_PORTS = {"9333", "9555"}
PROTECTED_PROFILES = {Path.home() / ".config/jevdual/chrome-profile", Path.home() / ".config/jevdual/chrome-profile-signin"}


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

    server, fixture_port = _serve(out)
    url = f"http://127.0.0.1:{fixture_port}/"
    gate = _wait_idle()
    front_at_start = _front()
    stop = threading.Event()
    sampler = threading.Thread(target=_sample_front, args=(out, stop), daemon=True)
    sampler.start()
    steps: list[dict] = []
    record = {"arm": args.arm, "port": port, "profile": str(profile), "gate": gate,
              "front_at_start": front_at_start, "fixture": url, "steps": steps}
    try:
        steps.append(_cli(env, out, "00-start", "start", "probe the browser holder", "--browser", "--url", url,
                          "--session", str(session)))
        steps[-1]["tab"] = _tab(session)
        time.sleep(1.0)
        if _front() != front_at_start:
            subprocess.run(["osascript", "-e", f'tell application "{front_at_start}" to activate'],
                           capture_output=True, timeout=10, check=False)
        time.sleep(5.0)
        record["restored"] = {"t": time.time(), "front": _front()}
        for i in range(1, args.rounds + 1):
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
