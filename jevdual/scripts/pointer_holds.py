"""Hold the real pointer still at known points and report when it arrived and left, on the host clock.

    uv run python scripts/pointer_holds.py --window-id 40123 --hold-ms 500 120,80 600,400 ...
    uv run python scripts/pointer_holds.py --screen 300,200 900,600

Points are in points (not pixels): relative to the window's top-left with --window-id, else global screen
points. Travel between points is Footwork's planned human path (--travel path) or one jump (--travel jump).
Each point prints one JSON line:

    {"i": 0, "target": [x, y], "arrive_ns": ..., "depart_ns": ..., "held_ms": ...,
     "max_drift_pt": ..., "outcome": "held"}

arrive_ns is the first CLOCK_UPTIME_RAW reading (clock_gettime_nsec_np, the clock mach_absolute_time counts
in, converted to ns) at which the pointer read back on the target; depart_ns is the reading just before the
first event that moves it away (or the end of the hold for the last point). The pointer is sampled every 2 ms
through the hold; a drift over 0.5 pt, or a key or button press by someone else, stops the run (exit 3).
Only mouse-moved events are posted: no clicks, no keys.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections.abc import Callable, Sequence

Point = tuple[float, float]
DRIFT_PT = 0.5


def uptime_raw_ns() -> int:
    return time.clock_gettime_ns(time.CLOCK_UPTIME_RAW)


def window_origin(window_id: int) -> Point:
    import Quartz

    info = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionIncludingWindow, window_id)
    if not info:
        raise SystemExit(f"window {window_id} is not on screen")
    b = info[0]["kCGWindowBounds"]
    return (float(b["X"]), float(b["Y"]))


def run_holds(
    targets: Sequence[Point],
    hold_s: float,
    poster,
    clock,
    now_ns: Callable[[], int] = uptime_raw_ns,
    *,
    travel: str = "path",
    plan: Callable[[Point, Point], object] | None = None,
    emit: Callable[[dict], None] = lambda rec: print(json.dumps(rec), flush=True),
) -> int:
    from jevdual import drag

    records: list[dict] = []
    for i, target in enumerate(targets):
        here = poster.location()
        if records:  # leaving the previous point now
            records[-1]["depart_ns"] = now_ns()
            _finish(records[-1], emit)
        if poster.foreign_input() is not None:
            emit({"i": i, "target": list(target), "outcome": f"contended:{poster.foreign_input()}"})
            return 3
        if travel == "path" and math.dist(here, target) >= 1.0:
            p = plan(here, target) if plan else drag.plan_path(here, target, timing="DELIBERATE")
            result = drag.play_move(p, poster, clock, drag.DragSettings(arc_size=0.0))
            if result.outcome != "arrived":
                emit({"i": i, "target": list(target), "outcome": result.outcome})
                return 3
        else:
            poster.move(*target)
        deadline = clock.now() + 0.25
        while math.dist(poster.location(), target) > DRIFT_PT:
            if clock.now() > deadline:
                emit({"i": i, "target": list(target), "outcome": "did_not_arrive", "at": poster.location()})
                return 3
            clock.sleep_until(clock.now() + 0.001)
        rec = {"i": i, "target": list(target), "arrive_ns": now_ns(), "max_drift_pt": 0.0}
        records.append(rec)
        end = clock.now() + hold_s
        while clock.now() < end:
            loc = poster.location()
            rec["max_drift_pt"] = round(max(rec["max_drift_pt"], math.dist(loc, target)), 2)
            cause = poster.foreign_input()
            if rec["max_drift_pt"] > DRIFT_PT or cause is not None:
                rec["depart_ns"] = now_ns()
                rec["outcome"] = f"contended:{cause or 'pointer_moved'}"
                _finish(rec, emit, keep_outcome=True)
                return 3
            clock.sleep_until(min(end, clock.now() + 0.002))
    if records:
        records[-1]["depart_ns"] = now_ns()
        _finish(records[-1], emit)
    return 0


def _finish(rec: dict, emit: Callable[[dict], None], *, keep_outcome: bool = False) -> None:
    rec["held_ms"] = round((rec["depart_ns"] - rec["arrive_ns"]) / 1e6, 3)
    if not keep_outcome:
        rec["outcome"] = "held"
    emit(rec)


def _point(text: str) -> Point:
    x, y = text.split(",")
    return (float(x), float(y))


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    where = ap.add_mutually_exclusive_group(required=True)
    where.add_argument("--window-id", type=int, help="points are relative to this window's top-left")
    where.add_argument("--screen", action="store_true", help="points are global screen points")
    ap.add_argument("--hold-ms", type=float, default=500.0)
    ap.add_argument("--travel", choices=("path", "jump"), default="path")
    ap.add_argument("points", nargs="+", type=_point, metavar="X,Y")
    args = ap.parse_args(argv)
    from jevdual import drag

    ox, oy = window_origin(args.window_id) if args.window_id else (0.0, 0.0)
    targets = [(ox + x, oy + y) for x, y in args.points]
    print(json.dumps({"clock": "CLOCK_UPTIME_RAW ns", "origin": [ox, oy], "now_ns": uptime_raw_ns()}))
    return run_holds(
        targets, args.hold_ms / 1000, drag.QuartzPoster(), drag.MonotonicClock(), travel=args.travel
    )


if __name__ == "__main__":
    sys.exit(main())
