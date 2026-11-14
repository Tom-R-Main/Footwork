"""``footwork drag-points``: a real-pointer drag between two screen points, for no session (PTD2).

The drag itself is ``jevdual.drag``: an approach with no button, a press, drag events along a planned
path, a release, and exactly one release on every exit after the press. This module is only the way in
for a caller that has two points and no elements: a canvas, where a box or an arrow begins and ends on
nothing an observation lists.

It belongs to no session. A browser session cannot share a browser with another DevTools client, and
a filmed session's take ends when anything else moves the pointer between its commands; the caller
this is for does both. So the command makes no DevTools connection and reads no window's contents.
What a session's command gets from its entrypoint it takes itself: the desktop and the application
whose window is under the start point, claimed in the coordination registry for as long as it runs
and refused at once when another owner holds either.

The button is the thing it must not get wrong (PTD9, PTD10). Told to stop (SIGINT, SIGTERM, SIGHUP)
it stops the drag as foreign input does, with Escape and a release, and reports before it exits. A
post that fails is reported with what was posted. After any press it reads the button; when no
release was posted, or the button still reads down, it posts one more release at the pointer and
reads again; and when it still cannot say the button is up it keeps its claim, so the registry
holds the desktop until someone looks (``footwork control recover TOKEN --input-cleaned``).

Points are global screen points with the origin at the top left of the main display, the space of
Quartz events and accessibility frames. They are points, not backing pixels, and may be fractions.
"""

from __future__ import annotations

import argparse
import asyncio
import itertools
import json
import math
import os
import signal
import sys
import time
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

#: nothing was posted: the arguments, the display, the button or the desktop's owner refused it
EXIT_REFUSED = 4
#: pointer moves were posted and the button never pressed: the approach did not arrive
EXIT_APPROACH = 5
#: the button was pressed and the drag did not end as asked; it was released where it says
EXIT_ABORTED = 6
#: the button was pressed and the command cannot say it is up: the desktop stays claimed (it names the
#: token). Not 7, which the launcher uses for a command stopped by an error it did not handle
EXIT_HELD = 8

#: a pointer this near the start (points) is not moved first; the press is posted at the start itself
AT_START_PT = 2.0
#: how long the button is read for after a release before it is reported still down. The system shows a
#: posted release in the button's state a little after the post returns: the first live interrupted drag
#: read it 0.2 ms after posting, was told "down", and reported a stuck button that was not (PTD4)
BUTTON_UP_WAIT_S = 0.25
#: the longest --duration taken: the desktop is claimed, and the button held, for all of it
MAX_DURATION_S = 30.0
#: told to stop by one of these, the command stops as foreign input stops it, and still reports
STOP_SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)

Point = tuple[float, float]
Rect = tuple[float, float, float, float]


def display_bounds() -> list[Rect]:
    """Each active display's bounds in global screen points."""
    from jevdual.pointer_trace import display_geometry

    return [tuple(display["bounds"]) for display in display_geometry()]  # type: ignore[misc]


def _on_a_display(point: Point, displays: list[Rect]) -> bool:
    return any(x <= point[0] < x + w and y <= point[1] < y + h for x, y, w, h in displays)


def app_under(point: Point) -> str | None:
    """The application that owns the frontmost ordinary window containing ``point``, by the window
    server's list (front to back, owner names only: no window is opened or read). None over none."""
    import Quartz

    listed = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID) or ()
    for window in listed:
        bounds = window.get("kCGWindowBounds") or {}
        if window.get("kCGWindowLayer", 0) != 0 or not window.get("kCGWindowAlpha", 1):
            continue
        x, y = bounds.get("X", 0.0), bounds.get("Y", 0.0)
        if x <= point[0] < x + bounds.get("Width", 0.0) and y <= point[1] < y + bounds.get("Height", 0.0):
            return str(window.get("kCGWindowOwnerName") or "") or None
    return None


def add_parser(sub: Any) -> None:
    dp = sub.add_parser(
        "drag-points",
        help="drag the real pointer from one screen point to another (no session, no browser connection)",
        description="Move the real pointer to X0 Y0 with no button, press, drag to X1 Y1 and release. Global "
        "screen points, origin top left. Prints one JSON object. Exit 0: released at the end point. "
        f"{EXIT_REFUSED}: nothing posted. {EXIT_APPROACH}: the pointer was moved and the button never "
        f"pressed. {EXIT_ABORTED}: pressed, and released otherwise than asked (it says where and why). "
        f"{EXIT_HELD}: pressed, and the button cannot be said to be up; the desktop stays claimed.",
    )
    for name in ("x0", "y0", "x1", "y1"):
        dp.add_argument(name, type=float)
    dp.add_argument("--mode", default="background_only",
                    choices=("background_only", "foreground_permitted", "exclusive_desktop"),
                    help="must be exclusive_desktop: the command moves the real pointer and holds its button")
    dp.add_argument("--owner", help="who the desktop is claimed for in the coordination registry "
                    "(default: this process)")
    dp.add_argument("--app", metavar="NAME", help="the application to claim with the desktop (default: "
                    "the one whose window is under the start point)")
    dp.add_argument("--duration", type=float, metavar="SECONDS",
                    help="how long the drag's motion takes, press hold and settle apart (default: the "
                    f"planner's, about 0.6 s for a short drag); not shorter than that, at most {MAX_DURATION_S:g}")
    dp.add_argument("--record", metavar="FILE", help="append the drag's pointer_gesture/1 record to FILE")
    dp.set_defaults(fn=cmd_drag_points)


def arguments(*argv: str) -> argparse.Namespace:
    """The command's parsed arguments (for a caller inside the process, and the tests)."""
    parser = argparse.ArgumentParser(prog="footwork")
    add_parser(sub := parser.add_subparsers(dest="cmd"))
    del sub
    return parser.parse_args(["drag-points", *argv])


def _button_up(poster: Any, since_ns: int | None) -> tuple[bool, float | None]:
    """Whether the left button reads up within ``BUTTON_UP_WAIT_S`` of now, and how many milliseconds
    after ``since_ns`` (the return of the release's post) the reading that said so was taken."""
    from jevdual.pointer_trace import uptime_raw_ns

    began = time.monotonic()
    while True:
        waited = time.monotonic() - began
        if not poster.left_button_down():
            read = uptime_raw_ns()
            return True, (None if since_ns is None else round((read - since_ns) / 1e6, 2))
        if waited >= BUTTON_UP_WAIT_S:
            return False, None
        time.sleep(0.002)


def _say(report: dict[str, Any], code: int, note: str = "") -> int:
    if note:
        print(note, file=sys.stderr)
    print(json.dumps(report))
    return code


def _stretched(plan: Any, duration: float, settings: Any) -> Any:
    """``plan`` played over ``duration`` seconds, along the same path. Every sample's time is scaled by
    one factor, so the shape of the speed is the planner's; and each stretch between two samples is
    cut into as many equal pieces as keep the planned posts no further apart in time than the plain
    plan's widest. A slow drag posts as often as a fast one: it is not nearer the engine's limit on
    the time between posts (PTD9). Refuses a duration shorter than the planner's."""
    from jevdual.drag import DragRefused, Sample

    planned = plan.samples[-1].t
    if planned <= 0:
        raise DragRefused("duration_unreachable", "the planned path has no duration to scale")
    if duration < planned:
        raise DragRefused("duration_unreachable",
                          f"{duration:g} s is shorter than the planned {planned:.3f} s for this distance")
    factor = duration / planned
    widest = max((b.t - a.t for a, b in itertools.pairwise(plan.samples)), default=0.0) or settings.max_gap_s
    first = plan.samples[0]
    samples = [replace(first, t=first.t * factor)]
    for a, b in itertools.pairwise(plan.samples):
        gap = (b.t - a.t) * factor
        pieces = max(1, math.ceil(gap / widest - 1e-9))
        for i in range(1, pieces):
            part = i / pieces
            samples.append(Sample(a.t * factor + gap * part, a.x + (b.x - a.x) * part, a.y + (b.y - a.y) * part))
        samples.append(replace(b, t=b.t * factor))
    return replace(plan, samples=tuple(samples))


async def cmd_drag_points(args: Any) -> int:
    from jevdual import drag as d
    from jevdual.coordination import (
        CoordinationError,
        Coordinator,
        activated,
        app_resource,
        conflicts,
        owned_thread,
    )
    from jevdual.pointer_trace import CLOCK, GestureTrace, uptime_raw_ns

    start, end = (float(args.x0), float(args.y0)), (float(args.x1), float(args.y1))
    report: dict[str, Any] = {
        "outcome": "refused", "start": list(start), "end": list(end), "pressed": False,
        "pressed_at": None, "pressed_ns": None, "released_at": None, "released_ns": None,
        "clock": CLOCK, "approach_moves": 0, "drags": 0, "escape_sent": False,
        "releases_posted": 0, "stopped_by": None, "claim_kept": None,
    }
    stop: dict[str, str | None] = {"by": None}

    def stopped() -> bool:
        return stop["by"] is not None

    def refused(code: str, reason: str) -> int:
        report.update(outcome="refused", code=code, reason=reason, stopped_by=stop["by"])
        return _say(report, EXIT_REFUSED, f"not dragged: {code}: {reason}")

    def not_pressed(cause: str, moves: int | None) -> int:
        """An exit before the press: exit 4 when nothing was posted, 5 when the pointer was moved."""
        if moves == 0:
            return refused(cause.partition(":")[0], f"stopped before anything was posted ({cause})")
        report.update(outcome=f"approach_aborted:{cause}", pointer_after=list(poster.location()),
                      button_up=not poster.left_button_down(), stopped_by=stop["by"])
        return _say(report, EXIT_APPROACH,
                    f"not dragged: stopped ({cause}) after "
                    + ("an unknown number of" if moves is None else str(moves))
                    + " moves; the button was never pressed")

    if getattr(args, "mode", None) != "exclusive_desktop":
        return refused("requires_desktop", "drag-points moves the real pointer and holds its button; "
                       "it needs --mode exclusive_desktop")
    displays = display_bounds()
    for name, point in (("start", start), ("end", end)):
        if not _on_a_display(point, displays):
            return refused("point_off_display", f"the {name} point {point[0]:g},{point[1]:g} is on no display")
    duration = getattr(args, "duration", None)
    if duration is not None:
        duration = float(duration)
        if not math.isfinite(duration) or duration <= 0:
            return refused("duration_invalid", f"{duration:g} is not a number of seconds a drag can take")
        if duration > MAX_DURATION_S:
            return refused("duration_unreachable", f"{duration:g} s is over the {MAX_DURATION_S:g} s this "
                           "command will hold the desktop and the button for")
    settings = d.DragSettings()
    seed = f"drag-points|{start[0]!r},{start[1]!r}|{end[0]!r},{end[1]!r}"
    try:
        plan = d.plan_drag(start, end, settings, seed=seed)
        if duration is not None:
            plan = _stretched(plan, duration, settings)
    except d.DragRefused as exc:
        return refused(exc.code, str(exc).split(": ", 1)[-1])
    report.update(planned_motion_s=round(plan.samples[-1].t, 4), press_hold_s=settings.press_hold_s,
                  settle_s=settings.settle_s)

    app = getattr(args, "app", None)
    if not app:
        try:
            app = app_under(start)
        except Exception as exc:  # noqa: BLE001 - an unreadable window list is said, and only the desktop claimed
            report["app_unread"] = type(exc).__name__
    resources = ["desktop", *([app_resource(app)] if app else [])]
    report.update(app=app or None, claimed=sorted(resources))
    owner = getattr(args, "owner", None) or f"drag-points:{os.getpid()}"
    registry = Coordinator()
    # the signals are taken before the desktop is, and given back after it: a process ended by one while
    # it held the claim would leave the registry holding the desktop for a button that was never pressed
    loop, handled = asyncio.get_running_loop(), []
    for number in STOP_SIGNALS:
        def told(name: str = number.name) -> None:
            stop["by"] = stop["by"] or name
        try:
            loop.add_signal_handler(number, told)
            handled.append(number)
        except (ValueError, RuntimeError, NotImplementedError):  # not the main thread: the caller's to handle
            pass
    claim, kept = None, False
    try:
        try:
            # does not wait: a caller mid-film wants the refusal, not a drag that begins half a minute late
            claim = registry.claim(owner, resources, timeout=0.0)
            await claim.__aenter__()
        except CoordinationError as exc:
            claim = None
            held = registry.status()
            others = [row["resources"] for row in held["requests"] if row["state"] != "waiting"]
            others += [row["resources"] for row in held["reservations"] if row["state"] == "active"]
            if app and not any(conflicts(["desktop"], other) for other in others):
                return refused("app_busy", f"another owner holds {app} in footwork's registry ({exc})")
            return refused("desktop_busy", f"another owner holds this desktop in footwork's registry ({exc})")
        if stopped():
            return refused("cancelled", f"told to stop ({stop['by']}) before anything was posted")
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
                try:
                    approach = await owned_thread(d.play_move, approach_plan, poster, clock, settings,
                                                  cancelled=stopped)
                except Exception as exc:  # noqa: BLE001 - a failed post is reported, with the button never pressed
                    report["error"] = type(exc).__name__
                    return not_pressed(f"error:{type(exc).__name__}", None)
                report["approach_moves"] = approach.posted_drags
                if approach.outcome != "arrived":
                    return not_pressed(approach.outcome.removeprefix("aborted:"), approach.posted_drags)
            if stopped():
                return not_pressed("cancelled", report["approach_moves"])

            trace = GestureTrace(SimpleNamespace(trace_path=getattr(args, "record", None) or None,
                                                 window=(None, None), content=(None, None)),
                                 "drag", "drag-points", start, end, plan)
            recording = trace.poster(poster)
            result, failure = None, None
            try:
                try:
                    result = await owned_thread(d.play_drag, plan, recording, clock, settings,
                                                cancelled=stopped, trace=trace)
                except BaseException as exc:  # noqa: BLE001 - the button comes first; what must rise is raised below
                    failure = exc
                downs = [post for post in trace.posts if post[4] == "down"]
                # a press whose post raised may have been posted. One refused for ownership was not:
                # the poster checks that before it posts
                unsure = [e for e in trace.errors if e["event"] == "down" and e["error"] != "CoordinationError"]
                if not downs and not unsure:
                    if failure is not None and not isinstance(failure, (Exception, asyncio.CancelledError)):
                        raise failure
                    if failure is not None and not isinstance(failure, (CoordinationError, asyncio.CancelledError)):
                        report["error"] = type(failure).__name__
                        cause = f"error:{type(failure).__name__}"
                    else:
                        cause = result.outcome.removeprefix("aborted:") if result is not None else "cancelled"
                    code = not_pressed(cause, report["approach_moves"])
                    if isinstance(failure, asyncio.CancelledError):
                        raise failure
                    return code

                def releases() -> list[Any]:
                    return [post for post in trace.posts if post[4] == "up"]

                up, after_ms = _button_up(poster, releases()[-1][1] if releases() else None)
                if not releases() or not up:
                    # no release was posted, or one was and the button still reads down: one more, where
                    # the pointer is. A release nothing needed is a smaller thing than a held button
                    extra: dict[str, Any] = {"posted": False}
                    try:
                        at = poster.location()
                        extra["at"] = list(at)
                        recording.up(*at)
                        extra["posted"] = True
                    except Exception as exc:  # noqa: BLE001 - reported; the claim is kept below
                        extra["error"] = type(exc).__name__
                    report["extra_release"] = extra
                    up, after_ms = _button_up(poster, releases()[-1][1] if releases() else None)
                posted = releases()
                kept = not up or not posted
                before, wall, after = uptime_raw_ns(), time.time(), uptime_raw_ns()
                if downs:
                    report["pressed_at"], report["pressed_ns"] = [downs[0][2], downs[0][3]], downs[0][0]
                else:
                    report.update(pressed_at=[unsure[0]["x"], unsure[0]["y"]], pressed_ns=unsure[0]["t_ns"],
                                  press_post_failed=True)
                if posted:
                    report["released_at"], report["released_ns"] = [posted[0][2], posted[0][3]], posted[0][0]
                outcome = result.outcome if result is not None else f"error:{type(failure).__name__}"
                report.update(
                    outcome=outcome, pressed=True, releases_posted=len(posted), stopped_by=stop["by"],
                    drags=sum(1 for post in trace.posts if post[4] == "drag"),
                    escape_sent=bool(result is not None and result.escape_sent),
                    max_gap_ms=round(result.max_gap_s * 1000, 2) if result is not None else None,
                    pointer_after=list(poster.location()), button_up=up,
                    # from the return of the last release's post to the reading that said the button was up
                    button_up_ms_after_release=after_ms,
                    # one reading of both clocks, so a caller can put the two times beside a wall-clock log
                    clock_pair={"ns": (before + after) // 2, "unix_s": wall},
                )
                if failure is not None:
                    report["error"] = type(failure).__name__
                if result is not None and result.release_error:
                    report["release_error"] = result.release_error
                if kept:
                    claim.abandon()
                    report["claim_kept"] = claim.token
                    code = _say(report, EXIT_HELD,
                                f"drag {outcome}: THE LEFT BUTTON MAY STILL BE DOWN ("
                                + (f"it reads down {BUTTON_UP_WAIT_S * 1000:.0f} ms after {len(posted)} releases"
                                   if posted else "no release could be posted")
                                + f"). This desktop stays claimed in footwork's registry. Look at the button, "
                                f"then: footwork control recover {claim.token} --input-cleaned")
                elif outcome == "dropped" and "extra_release" not in report:
                    code = _say(report, 0)
                else:
                    where = f"released at {report['released_at'][0]:.1f},{report['released_at'][1]:.1f}"
                    if outcome != "dropped":
                        where += ", not at the end point"
                    if "extra_release" in report:
                        where += "; a second release was posted before the button read up"
                    code = _say(report, EXIT_ABORTED,
                                f"drag {outcome}: pressed at {start[0]:.1f},{start[1]:.1f}, {where}"
                                + ("; Escape was sent first" if report["escape_sent"] else "")
                                + (f"; stopped by {stop['by']}" if stop["by"] else ""))
                if failure is not None and not isinstance(failure, Exception):
                    raise failure  # a cancellation or an interrupt, after the button and the report
                return code
            finally:
                trace.finish(poster, report["outcome"] if report["pressed"] else "not_pressed", result)
    finally:
        if claim is not None and not kept:
            await claim.__aexit__(None, None, None)
        for number in handled:
            loop.remove_signal_handler(number)
