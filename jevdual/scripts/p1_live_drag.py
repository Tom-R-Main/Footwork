"""Live drag check (notebook PD1): drag a square and a slider in the Tk fixture with the real pointer.

Moves the real pointer and holds the left button. Run only with the owner's authorization and nobody at the
machine. Waits up to 15 s for 3 s of HID idle. Writes DIR/result.json.
"""

from __future__ import annotations

import itertools
import json
import math
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path

from jevdual.coexist import idle_seconds
from jevdual.drag import DragSettings, MonotonicClock, QuartzPoster, plan_drag, play_drag


def wait_for(path: Path, timeout: float = 10.0) -> dict:
    deadline = time.monotonic() + timeout
    while not path.exists():
        if time.monotonic() > deadline:
            raise TimeoutError(path)
        time.sleep(0.1)
    time.sleep(0.1)
    return json.loads(path.read_text())


def activate(pid: int) -> None:
    from AppKit import NSApplicationActivateIgnoringOtherApps, NSRunningApplication

    app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
    if app is not None:
        app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)


def one(name: str, start, end, out: Path, settings: DragSettings) -> dict:
    events_path = out / "events.json"
    events_path.unlink(missing_ok=True)
    plan = plan_drag(tuple(start), tuple(end), settings, seed=name)
    poster, clock = QuartzPoster(), MonotonicClock()
    # put the pointer at the start without a button, like setup's placement
    import Quartz

    move = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventMouseMoved, Quartz.CGPointMake(*start), 0)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, move)
    time.sleep(0.3)
    deadline = time.monotonic() + 15.0
    while (idle := idle_seconds()) < 3.0 and time.monotonic() < deadline:
        time.sleep(0.25)
    if idle < 3.0:
        return {"name": name, "outcome": "refused:idle_guard", "idle_s": idle}
    poster = QuartzPoster()  # baseline the counters after the idle wait
    result = play_drag(plan, poster, clock, settings)
    time.sleep(0.3)
    after = poster.location()
    seen = wait_for(events_path, 5.0)
    evs = [e for e in seen["events"] if e["mono"] >= 0]
    motions = [e for e in evs if e["kind"] == "motion"]
    gaps = [b["mono"] - a["mono"] for a, b in itertools.pairwise(motions)]
    posted = [(s.x, s.y) for s in plan.samples]
    off_path = max(
        (min(math.dist((m["x_root"], m["y_root"]), p) for p in posted) for m in motions), default=None
    )
    return {
        "name": name,
        "plan": {
            "start": start,
            "end": end,
            "samples": len(plan.samples),
            "duration_s": plan.samples[-1].t,
            "max_step_pt": plan.max_step_pt,
        },
        "result": asdict(result)
        | {
            "lateness_s": None,
            "lateness_p95_ms": sorted(result.lateness_s)[int(0.95 * len(result.lateness_s))] * 1000
            if result.lateness_s
            else None,
        },
        "pointer_after": after,
        "button_down_after": poster.left_button_down(),
        "app": {
            "kinds": [e["kind"] for e in evs if e["kind"] != "motion"],
            "motion_events": len(motions),
            "max_motion_gap_ms": max(gaps) * 1000 if gaps else None,
            "max_off_path_pt": off_path,
            "first": evs[0] if evs else None,
            "last": evs[-1] if evs else None,
            "square_centre_after": seen["square_centre_root"],
            "slider_after": seen["slider"],
        },
        "idle_s": idle,
    }


def main(out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        [sys.executable, str(Path(__file__).parent / "drag_surface.py"), "--out", str(out)]
    )
    try:
        ready = wait_for(out / "ready.json")
        activate(proc.pid)
        time.sleep(0.8)
        settings = DragSettings()
        sq = ready["square_centre_root"]
        runs = [
            one("square", sq, [sq[0] + 400.0, sq[1] + 60.0], out, settings),
            one("slider", ready["slider_0_root"], ready["slider_75_root"], out, settings),
        ]
    finally:
        proc.terminate()
        proc.wait(timeout=5)
    report = {"ready": ready, "runs": runs, "t": time.strftime("%Y-%m-%dT%H:%M:%S")}
    (out / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
