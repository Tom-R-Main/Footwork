"""Run DemoGeek iteration 6's TAKE.md journey through Footwork's filmed pointer mode.

    python scripts/demogeek_take.py OUT_DIR [--url http://localhost:8766/index.html] [--record]

Moves the real pointer and types. Run only inside the takeover protocol with nobody at the machine.
Setup (off camera): a fresh Chrome app window in its own profile with a 1440x900 CSS px content area, a
filmed session with TAKE.md's keep-out and rest position, and the pointer parked at rest. Rolling: steps
1-10 of TAKE.md. Every command's output and timing goes to OUT_DIR/take.jsonl; the run stops at the first
failed step, because a take is never retried mid-way.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

KEEP_OUT = "420,145,980,558"
REST = "360,460"
BRIEF = "Show how a failed webhook gets replayed in relay.dev"
REVISION = "Hold the replay scene a bit longer"
WINDOW = {"x": 36, "y": 40, "w": 1440, "h": 932}


class TakeFailed(Exception):
    pass


class Take:
    def __init__(self, out: Path) -> None:
        self.out = out
        self.session = out / "session"
        self.log = (out / "take.jsonl").open("a")
        self.t0 = time.monotonic()

    def record(self, **kw) -> None:
        kw["t"] = round(time.monotonic() - self.t0, 3)
        self.log.write(json.dumps(kw) + "\n")
        self.log.flush()
        print(
            f"[{kw['t']:7.2f}] {kw.get('step', '')} {kw.get('cmd', '')} -> {kw.get('code', '')}", flush=True
        )

    def fw(self, step: str, *argv: str, ok: tuple[int, ...] = (0,)) -> str:
        cmd = ["footwork", *argv, "--session", str(self.session)]
        if argv[0] == "do":
            cmd += ["--no-judge", "--settle", "0.3"]
        started = time.monotonic()
        p = subprocess.run(["uv", "run", *cmd], capture_output=True, text=True, check=False)
        self.record(
            step=step,
            cmd=" ".join(argv),
            code=p.returncode,
            s=round(time.monotonic() - started, 2),
            out=p.stdout[-1500:],
            err=p.stderr[-600:],
        )
        if p.returncode not in ok or re.search(
            r"\b(refused|paused before dispatch|not sent)\b", p.stdout + p.stderr
        ):
            raise TakeFailed(
                f"{step}: {' '.join(argv)} exited {p.returncode}: {(p.stderr or p.stdout)[-400:]}"
            )
        return p.stdout

    def wait_for(self, step: str, label: str, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            p = subprocess.run(
                ["uv", "run", "footwork", "look", "--session", str(self.session)],
                capture_output=True,
                text=True,
                check=False,
            )
            if label in p.stdout:
                self.record(step=step, cmd=f"wait {label!r}", code=0)
                return
            time.sleep(0.4)
        raise TakeFailed(f"{step}: {label!r} did not appear within {timeout} s")


def chrome(out: Path, url: str) -> int:
    profile = out / "chrome-profile"
    subprocess.run(
        [
            "open",
            "-na",
            "Google Chrome",
            "--args",
            f"--user-data-dir={profile}",
            "--no-first-run",
            "--no-default-browser-check",
            "--force-renderer-accessibility",
            f"--window-position={WINDOW['x']},{WINDOW['y']}",
            f"--window-size={WINDOW['w']},{WINDOW['h']}",
            f"--app={url}",
        ],
        check=True,
    )
    time.sleep(4)
    pids = subprocess.run(
        ["pgrep", "-f", f"user-data-dir={profile}"], capture_output=True, text=True, check=False
    ).stdout.split()
    if not pids:
        raise TakeFailed("setup: Chrome did not start")
    return min(int(p) for p in pids)


def run(take: Take, url: str) -> None:
    pid = chrome(take.out, url)
    out = take.fw(
        "setup",
        "start",
        "Make a Relay demo in DemoGeek",
        "--app",
        "Google Chrome",
        "--pid",
        str(pid),
        "--window",
        "DemoGeek",
        "--mode",
        "exclusive_desktop",
        "--pointer-motion",
        "filmed",
        "--rest",
        REST,
        "--authorize",
        "Send",
    )
    if "content 1440x900" not in out:
        raise TakeFailed(f"setup: the content area is not 1440x900 CSS px: {out[:300]}")
    take.wait_for("setup", "'Message'", 10)  # Chrome builds web accessibility lazily
    take.fw("setup", "park", "--place")
    take.record(step="rolling", cmd="filmed_phase rolling")
    # 1-2: brief
    # a web textarea offers type, not click: in a filmed take, type travels to the field first
    take.fw("1", "do", "type", "Message", BRIEF)
    take.fw("2", "do", "key", "Return")
    take.wait_for("2", "'45 sec'", 15)
    # 3: length
    take.fw("3", "do", "click", "45 sec")
    take.wait_for("3", "'Record it'", 15)
    # 4: hover each scene, hover to hover
    for n in range(1, 5):
        take.fw("4", "point", f"Scene {n}:")  # Chrome's groups are collapsed by the Driver; point finds them
        time.sleep(0.7)
    # 5-6: record, then park while the product draws its own cursor
    # the product frame draws its own cursor from Record on: no path may enter it from here
    take.fw("5", "keep-out", KEEP_OUT)
    take.fw("5", "do", "click", "Record it")
    take.fw("6", "park")
    take.wait_for("5", "'See proof'", 15)
    # 7: revision
    take.fw("7", "do", "type", "Message", REVISION)
    take.fw("7", "do", "key", "Return")
    take.wait_for("7", "is now 12s", 15)
    # 8-9: jump to the replay segment, then waypoint below the frame and open the proof
    take.fw("8", "do", "click", "Replay it, 12 seconds. Click to jump.")
    take.fw("9", "park", "400", "765")
    take.fw("9", "do", "click", "See proof")
    # 10: rest and hold
    take.fw("10", "park")
    time.sleep(2)
    take.record(step="end", cmd="take complete")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--url", default="http://localhost:8766/index.html")
    args = ap.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    take = Take(out)
    try:
        run(take, args.url)
    except TakeFailed as exc:
        take.record(step="failed", cmd=str(exc)[:500])
        print(f"take failed: {exc}", file=sys.stderr)
        return 1
    finally:
        subprocess.run(["pkill", "-f", f"user-data-dir={out / 'chrome-profile'}"], check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
