"""A human-paced real-pointer drag on macOS.

A drag is a left-button press, the planner's path played as ``LeftMouseDragged`` events at their scheduled
times, and a release. Coordinates are global screen points (the space of AX frames and Quartz events).

The one invariant that matters most: once the button is down, every exit releases it exactly once. A
finished drag releases at the drop point after a short settle. Every other exit (cancel, a stalled
schedule, foreign input, an exception) first posts Escape, which cancels a drag session in AppKit and
browsers, then releases where the pointer last was. The result says which happened, because a release
mid-path can still drop something there.

Contention here is a first cut: foreign key and button presses from the session counters, and a pointer
that is not where the last post put it. The tagged event tap of the pointer-motion plan (§3.4) replaces
it when P1b lands.
"""

from __future__ import annotations

import itertools
import math
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

#: tags every event this module posts (kCGEventSourceUserData), so a tap or a log can tell them apart
TAG = 0x46574447  # "FWDG"
ESCAPE_KEYCODE = 53


@dataclass(frozen=True)
class DragSettings:
    """Recorded settings for a drag. Changing one is a settings change, not tuning toward a result."""

    #: between the press and the first drag event; many apps need a held press before a drag starts
    press_hold_s: float = 0.12
    #: after the last sample, before the release, so a drop target can respond to the pointer resting on it
    settle_s: float = 0.15
    #: the longest allowed time between two posts once the drag is moving
    max_gap_s: float = 0.05
    #: a shorter drag is refused: apps start a drag only past a few points of movement
    min_distance_pt: float = 6.0
    #: drags read as straighter than free pointer moves
    arc_size: float = 0.1
    #: post Escape before releasing on an abort
    cancel_with_escape: bool = True


DEFAULT = DragSettings()


@dataclass(frozen=True)
class Sample:
    t: float  # seconds after the first drag post
    x: float
    y: float


@dataclass(frozen=True)
class DragPlan:
    start: tuple[float, float]
    end: tuple[float, float]
    samples: tuple[Sample, ...]
    seed: str
    max_step_pt: float


@dataclass
class DragResult:
    #: "dropped" (released at the drop point) or "aborted:<cause>" (Escape, then released mid-path)
    outcome: str
    posted_drags: int = 0
    released_at: tuple[float, float] | None = None
    escape_sent: bool = False
    causes: list[str] = field(default_factory=list)
    max_gap_s: float = 0.0
    lateness_s: list[float] = field(default_factory=list)


class DragRefused(ValueError):
    """The drag was refused before anything was posted."""

    def __init__(self, code: str, reason: str) -> None:
        super().__init__(f"{code}: {reason}")
        self.code = code


class Poster(Protocol):
    def down(self, x: float, y: float) -> None: ...
    def drag(self, x: float, y: float) -> None: ...
    def up(self, x: float, y: float) -> None: ...
    def escape(self) -> None: ...
    def location(self) -> tuple[float, float]: ...
    def foreign_input(self) -> str | None: ...


class Clock(Protocol):
    def now(self) -> float: ...
    def sleep_until(self, t: float) -> None: ...


def plan_drag(
    start: tuple[float, float],
    end: tuple[float, float],
    settings: DragSettings = DEFAULT,
    *,
    seed: str = "drag",
    planner: Any = None,
) -> DragPlan:
    """Plan a drag path with CUA's motion planner; refuses a drag too short to register as one."""
    if math.dist(start, end) < settings.min_distance_pt:
        raise DragRefused(
            "drag_too_short", f"{math.dist(start, end):.1f} pt is under {settings.min_distance_pt} pt"
        )
    if planner is None:
        import cua_driver as planner
    params = planner.default_cursor_motion_params()
    params.arc_size = settings.arc_size
    trajectory = planner.plan_cursor_move(
        params,
        planner.CursorMoveRequest(
            from_point=planner.CursorMotionPoint(x=start[0], y=start[1]),
            to_point=planner.CursorMotionPoint(x=end[0], y=end[1]),
            from_heading=None,
            end_heading=None,
            target=None,
            seed=seed,
            reduced_motion=False,
        ),
    )
    samples: list[Sample] = []
    for s in trajectory.samples():
        if samples and (s.x, s.y) == (samples[-1].x, samples[-1].y):
            continue  # the planner repeats the endpoint while it settles; repeats post nothing new
        samples.append(Sample(s.t, s.x, s.y))
    if (samples[-1].x, samples[-1].y) != end:
        samples.append(Sample(samples[-1].t, end[0], end[1]))
    steps = [math.dist((a.x, a.y), (b.x, b.y)) for a, b in itertools.pairwise(samples)]
    gaps = [b.t - a.t for a, b in itertools.pairwise(samples)]
    if gaps and max(gaps) > settings.max_gap_s:
        raise DragRefused("schedule_exceeds_gap", f"a scheduled interval of {max(gaps) * 1000:.1f} ms")
    return DragPlan(start, end, tuple(samples), seed, max(steps, default=0.0))


class _Abort(Exception):
    def __init__(self, cause: str) -> None:
        self.cause = cause


def play_drag(
    plan: DragPlan,
    poster: Poster,
    clock: Clock,
    settings: DragSettings = DEFAULT,
    *,
    cancelled: Callable[[], bool] = lambda: False,
) -> DragResult:
    """Press at the start, play the samples, release. Every exit after the press releases exactly once."""
    tolerance = 1.5 * plan.max_step_pt + 2.0
    result = DragResult("aborted:unknown")
    last = plan.start
    released = False

    def release(at: tuple[float, float]) -> None:
        nonlocal released
        if not released:
            released = True
            poster.up(*at)
            result.released_at = at

    def check() -> None:
        if cancelled():
            raise _Abort("cancelled")
        cause = poster.foreign_input()
        if cause is not None:
            raise _Abort(f"pointer_contended:{cause}")
        loc = poster.location()
        if math.dist(loc, last) > tolerance:
            raise _Abort(f"pointer_contended:pointer_moved {loc[0]:.1f},{loc[1]:.1f}")

    poster.down(*plan.start)
    try:
        t0 = clock.now() + settings.press_hold_s
        clock.sleep_until(t0)
        last_post = clock.now()
        for s in plan.samples[1:]:
            check()
            due = t0 + s.t
            clock.sleep_until(due)
            now = clock.now()
            if now - last_post > settings.max_gap_s:
                raise _Abort("playback_stall")
            poster.drag(s.x, s.y)
            result.lateness_s.append(now - due)
            result.max_gap_s = max(result.max_gap_s, now - last_post)
            result.posted_drags += 1
            last, last_post = (s.x, s.y), now
        clock.sleep_until(clock.now() + settings.settle_s)
        check()
        release(plan.end)
        result.outcome = "dropped"
    except _Abort as abort:
        result.outcome = f"aborted:{abort.cause}"
        result.causes.append(abort.cause)
        if settings.cancel_with_escape:
            poster.escape()
            result.escape_sent = True
        release(last)
    finally:
        release(last)  # an exception from the poster or clock still lets go of the button
    return result


# ---- the real Mac --------------------------------------------------------------------------------


class MonotonicClock:
    """Sleeps until about 1 ms before a deadline, then spins."""

    def now(self) -> float:
        return time.monotonic()

    def sleep_until(self, t: float) -> None:
        while (left := t - time.monotonic()) > 0.001:
            time.sleep(left - 0.001)
        while time.monotonic() < t:
            pass


class QuartzPoster:
    """Posts tagged left-button events through the HID event tap at absolute points, with no warp."""

    def __init__(self) -> None:
        import Quartz

        self.q = Quartz
        self.source = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
        self._kinds = (
            Quartz.kCGEventKeyDown,
            Quartz.kCGEventLeftMouseDown,
            Quartz.kCGEventRightMouseDown,
            Quartz.kCGEventOtherMouseDown,
        )
        self._own = dict.fromkeys(self._kinds, 0)
        self._base = {k: self._count(k) for k in self._kinds}

    def _count(self, kind: int) -> int:
        return int(
            self.q.CGEventSourceCounterForEventType(self.q.kCGEventSourceStateCombinedSessionState, kind)
        )

    def _mouse(self, kind: int, x: float, y: float, click_state: int | None = None) -> None:
        q = self.q
        event = q.CGEventCreateMouseEvent(self.source, kind, q.CGPointMake(x, y), q.kCGMouseButtonLeft)
        q.CGEventSetIntegerValueField(event, q.kCGEventSourceUserData, TAG)
        if click_state is not None:
            q.CGEventSetIntegerValueField(event, q.kCGMouseEventClickState, click_state)
        q.CGEventPost(q.kCGHIDEventTap, event)

    def down(self, x: float, y: float) -> None:
        self._own[self.q.kCGEventLeftMouseDown] += 1
        self._mouse(self.q.kCGEventLeftMouseDown, x, y, 1)

    def drag(self, x: float, y: float) -> None:
        self._mouse(self.q.kCGEventLeftMouseDragged, x, y)

    def up(self, x: float, y: float) -> None:
        self._mouse(self.q.kCGEventLeftMouseUp, x, y, 1)

    def escape(self) -> None:
        q = self.q
        self._own[q.kCGEventKeyDown] += 1
        for down in (True, False):
            event = q.CGEventCreateKeyboardEvent(self.source, ESCAPE_KEYCODE, down)
            q.CGEventSetIntegerValueField(event, q.kCGEventSourceUserData, TAG)
            q.CGEventPost(q.kCGHIDEventTap, event)

    def location(self) -> tuple[float, float]:
        p = self.q.CGEventGetLocation(self.q.CGEventCreate(None))
        return (p.x, p.y)

    def foreign_input(self) -> str | None:
        names = {
            self.q.kCGEventKeyDown: "key_down",
            self.q.kCGEventLeftMouseDown: "left_down",
            self.q.kCGEventRightMouseDown: "right_down",
            self.q.kCGEventOtherMouseDown: "other_down",
        }
        for kind in self._kinds:
            if self._count(kind) - self._base[kind] > self._own[kind]:
                return names[kind]
        return None

    def left_button_down(self) -> bool:
        q = self.q
        return bool(
            q.CGEventSourceButtonState(q.kCGEventSourceStateCombinedSessionState, q.kCGMouseButtonLeft)
        )


def path_points(plan: DragPlan) -> Sequence[tuple[float, float]]:
    return [(s.x, s.y) for s in plan.samples]
