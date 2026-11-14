"""``footwork drag-points``: a real-pointer drag between two screen points, for no session (PTD2).

The drag itself is ``jevdual.drag``: an approach with no button, a press, drag events along a planned
path, a release, and exactly one release on every exit after the press. This module is only the way in
for a caller that has two points and no elements: a canvas, where a box or an arrow begins and ends on
nothing an observation lists.

It belongs to no session. A browser session cannot share a browser with another DevTools client, and
a filmed session's take ends when anything else moves the pointer between its commands; the caller
this is for does both. So the command makes no DevTools connection and reads no window. What a
session's command gets from its entrypoint it takes itself: the desktop, claimed in the coordination
registry for as long as it runs and refused at once when another owner holds it.

Points are global screen points with the origin at the top left of the main display, the space of
Quartz events and accessibility frames. They are points, not backing pixels, and may be fractions.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import sys
import time
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

#: nothing was posted: the arguments, the display, the button or the desktop's owner refused it
EXIT_REFUSED = 4
#: pointer moves were posted and the button never pressed: the approach did not arrive
EXIT_APPROACH = 5
#: the button was pressed and the drag did not end at its end point; it was released where it says
EXIT_ABORTED = 6

#: a pointer this near the start (points) is not moved first; the press is posted at the start itself
AT_START_PT = 2.0
#: how long the button is read for after a release before it is reported still down. The system shows a
#: posted release in the button's state a little after the post returns: the first live interrupted drag
#: read it 0.2 ms after posting, was told "down", and reported a stuck button that was not (PTD4)
BUTTON_UP_WAIT_S = 0.25

Point = tuple[float, float]
Rect = tuple[float, float, float, float]


def display_bounds() -> list[Rect]:
    """Each active display's bounds in global screen points."""
    from jevdual.pointer_trace import display_geometry

    return [tuple(display["bounds"]) for display in display_geometry()]  # type: ignore[misc]


def _on_a_display(point: Point, displays: list[Rect]) -> bool:
    return any(x <= point[0] < x + w and y <= point[1] < y + h for x, y, w, h in displays)


def add_parser(sub: Any) -> None:
    dp = sub.add_parser(
        "drag-points",
        help="drag the real pointer from one screen point to another (no session, no browser connection)",
        description="Move the real pointer to X0 Y0 with no button, press, drag to X1 Y1 and release. Global "
        "screen points, origin top left. Prints one JSON object. Exit 0: released at the end point. "
        f"{EXIT_REFUSED}: refused, nothing posted. {EXIT_APPROACH}: the approach did not arrive, never "
        f"pressed. {EXIT_ABORTED}: pressed, then released somewhere else (it says where).",
    )
    for name in ("x0", "y0", "x1", "y1"):
        dp.add_argument(name, type=float)
    dp.add_argument("--mode", default="background_only",
                    choices=("background_only", "foreground_permitted", "exclusive_desktop"),
                    help="must be exclusive_desktop: the command moves the real pointer and holds its button")
    dp.add_argument("--owner", help="who the desktop is claimed for in the coordination registry "
                    "(default: this process)")
    dp.add_argument("--duration", type=float, metavar="SECONDS",
                    help="how long the drag's motion takes, press hold and settle apart (default: the "
                    "planner's, about 0.6 s for a short drag); not shorter than the planner's")
    dp.add_argument("--record", metavar="FILE", help="append the drag's pointer_gesture/1 record to FILE")
    dp.set_defaults(fn=cmd_drag_points)


def arguments(*argv: str) -> argparse.Namespace:
    """The command's parsed arguments (for a caller inside the process, and the tests)."""
    parser = argparse.ArgumentParser(prog="footwork")
    add_parser(sub := parser.add_subparsers(dest="cmd"))
    del sub
    return parser.parse_args(["drag-points", *argv])


def _button_up(poster: Any) -> tuple[bool, float | None]:
    """Whether the left button reads up within ``BUTTON_UP_WAIT_S``, and after how many milliseconds."""
    began = time.monotonic()
    while True:
        waited = time.monotonic() - began
        if not poster.left_button_down():
            return True, round(waited * 1000, 2)
        if waited >= BUTTON_UP_WAIT_S:
            return False, None
        time.sleep(0.002)


def _say(report: dict[str, Any], code: int, note: str = "") -> int:
    if note:
        print(note, file=sys.stderr)
    print(json.dumps(report))
    return code


def _stretched(plan: Any, duration: float, settings: Any) -> Any:
    """``plan`` played over ``duration`` seconds: every sample's time scaled by one factor, so the path
    and the shape of its speed are the planner's. Refuses a duration shorter than the planner's (a drag
    faster than a hand's) or so long that two posts would be further apart than the engine allows."""
    from jevdual.drag import DragRefused

    planned = plan.samples[-1].t
    if planned <= 0:
        raise DragRefused("duration_unreachable", "the planned path has no duration to scale")
    if duration < planned:
        raise DragRefused("duration_unreachable",
                          f"{duration:g} s is shorter than the planned {planned:.3f} s for this distance")
    factor = duration / planned
    samples = tuple(replace(s, t=s.t * factor) for s in plan.samples)
    widest = max((b.t - a.t for a, b in itertools.pairwise(samples)), default=0.0)
    if widest > settings.max_gap_s:
        longest = planned * settings.max_gap_s / (widest / factor)
        raise DragRefused("duration_unreachable",
                          f"{duration:g} s would leave {widest * 1000:.0f} ms between two posts (limit "
                          f"{settings.max_gap_s * 1000:.0f} ms); the longest this path takes is {longest:.2f} s")
    return replace(plan, samples=samples)


async def cmd_drag_points(args: Any) -> int:
    from jevdual import drag as d
    from jevdual.coordination import CoordinationError, Coordinator, activated, owned_thread
    from jevdual.pointer_trace import CLOCK, GestureTrace, uptime_raw_ns

    start, end = (float(args.x0), float(args.y0)), (float(args.x1), float(args.y1))
    report: dict[str, Any] = {
        "outcome": "refused", "start": list(start), "end": list(end), "pressed": False,
        "pressed_at": None, "pressed_ns": None, "released_at": None, "released_ns": None,
        "clock": CLOCK, "approach_moves": 0, "drags": 0, "escape_sent": False,
    }

    def refused(code: str, reason: str) -> int:
        report.update(outcome="refused", code=code, reason=reason)
        return _say(report, EXIT_REFUSED, f"not dragged: {code}: {reason}")

    if getattr(args, "mode", None) != "exclusive_desktop":
        return refused("requires_desktop", "drag-points moves the real pointer and holds its button; "
                       "it needs --mode exclusive_desktop")
    displays = display_bounds()
    for name, point in (("start", start), ("end", end)):
        if not _on_a_display(point, displays):
            return refused("point_off_display", f"the {name} point {point[0]:g},{point[1]:g} is on no display")
    settings = d.DragSettings()
    seed = f"drag-points|{start[0]!r},{start[1]!r}|{end[0]!r},{end[1]!r}"
    try:
        plan = d.plan_drag(start, end, settings, seed=seed)
        if getattr(args, "duration", None) is not None:
            plan = _stretched(plan, float(args.duration), settings)
    except d.DragRefused as exc:
        return refused(exc.code, str(exc).split(": ", 1)[-1])
    report.update(planned_motion_s=round(plan.samples[-1].t, 4), press_hold_s=settings.press_hold_s,
                  settle_s=settings.settle_s)

    owner = getattr(args, "owner", None) or f"drag-points:{os.getpid()}"
    try:
        # does not wait: a caller mid-film wants the refusal, not a drag that begins half a minute late
        claim = Coordinator().claim(owner, ["desktop"], timeout=0.0)
        await claim.__aenter__()
    except CoordinationError as exc:
        return refused("desktop_busy", f"another owner holds this desktop in footwork's registry ({exc})")
    try:
        with activated(claim):
            poster, clock = d.QuartzPoster(), d.MonotonicClock()
            if poster.left_button_down():
                return refused("button_down", "the left button is already down; a press now would end "
                               "that press, not begin a drag")
            here = poster.location()
            if not _on_a_display(here, displays):
                return refused("point_off_display", f"the pointer is at {here[0]:g},{here[1]:g}, on no display")
            approach_plan = None
            if math.dist(here, start) >= AT_START_PT:
                try:
                    approach_plan = d.plan_path(here, start, settings, seed=seed + "|approach")
                except d.DragRefused as exc:
                    return refused(exc.code, "the approach: " + str(exc).split(": ", 1)[-1])
            report["pointer_before"] = list(here)

            if approach_plan is not None:
                approach = await owned_thread(d.play_move, approach_plan, poster, clock, settings)
                report["approach_moves"] = approach.posted_drags
                if approach.outcome != "arrived":
                    cause = approach.outcome.removeprefix("aborted:")
                    report.update(outcome=f"approach_aborted:{cause}", pointer_after=list(poster.location()),
                                  button_up=not poster.left_button_down())
                    return _say(report, EXIT_APPROACH,
                                f"not dragged: the approach stopped ({cause}) after {approach.posted_drags} "
                                "moves; the button was never pressed")

            trace = GestureTrace(SimpleNamespace(trace_path=getattr(args, "record", None) or None,
                                                 window=(None, None), content=(None, None)),
                                 "drag", "drag-points", start, end, plan)

            def play() -> Any:
                result = None
                try:
                    result = d.play_drag(plan, trace.poster(poster), clock, settings, trace=trace)
                    return result
                finally:
                    trace.finish(poster, result.outcome if result else "exception", result)

            result = await owned_thread(play)
            up, up_after_ms = _button_up(poster)
            before, wall, after = uptime_raw_ns(), time.time(), uptime_raw_ns()
            posts = {event: (began, x, y) for began, _ended, x, y, event in trace.posts if event in ("down", "up")}
            for event, name in (("down", "pressed"), ("up", "released")):
                if event in posts:
                    report[f"{name}_at"], report[f"{name}_ns"] = list(posts[event][1:]), posts[event][0]
            report.update(
                outcome=result.outcome, pressed="down" in posts, drags=result.posted_drags,
                escape_sent=result.escape_sent, max_gap_ms=round(result.max_gap_s * 1000, 2),
                pointer_after=list(poster.location()), button_up=up, button_up_after_ms=up_after_ms,
                # one reading of both clocks, so a caller can put the two times beside a wall-clock log
                clock_pair={"ns": (before + after) // 2, "unix_s": wall},
            )
            if result.released_at is not None:
                report["released_at"] = list(result.released_at)
            if result.outcome == "dropped" and report["button_up"]:
                return _say(report, 0)
            where = (f"released at {result.released_at[0]:.1f},{result.released_at[1]:.1f}"
                     + ("" if result.outcome == "dropped" else ", not at the end point")
                     if result.released_at else "no release was posted")
            if not report["button_up"]:
                where += f"; THE LEFT BUTTON STILL READS DOWN after {BUTTON_UP_WAIT_S * 1000:.0f} ms"
            return _say(report, EXIT_ABORTED,
                        f"drag {result.outcome}: pressed at {start[0]:.1f},{start[1]:.1f}, {where}"
                        + ("; Escape was sent first" if result.escape_sent else ""))
    finally:
        await claim.__aexit__(None, None, None)
