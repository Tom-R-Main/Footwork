"""Filmed pointer mode: the real pointer travels to each target like a person's before Footwork acts.

A filmed session (``footwork start ... --pointer-motion filmed``, exclusive_desktop only) keeps this state
between commands:

- the scene window's frame and its web content origin, in global screen points;
- a keep-out rectangle no planned path may enter (the product's own cursor is drawn there);
- a rest position for ``footwork park``;
- the last point a gesture ended at, so a pointer that moved between commands ends the take;
- the take latch: once set, every filmed route refuses with ``take_ended`` until a new session starts.

Delivery is unchanged: the approach only moves the pointer, then the existing route acts (an AX press,
CUA's hover, type_text). Contention during an approach is ``jevdual.drag``'s first cut (session counters
and pointer location); the tagged event tap of the pointer-motion plan replaces it later.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

from jevdual.coordination import owned_thread

Point = tuple[float, float]
Rect = tuple[float, float, float, float]
#: how far (points) the pointer may sit from the position that was hit-tested on a page target. The
#: proof is of that position and no other, so this is float noise, not a tolerance: nothing moves the
#: pointer between the two reads unless someone does.
HELD_TOLERANCE_PT = 0.01


class FilmedRefusal(Exception):
    """A filmed route refused before the action was delivered."""

    def __init__(self, code: str, reason: str) -> None:
        super().__init__(f"{code}: {reason}")
        self.code = code
        self.reason = reason


def _inside(p: Point, r: Rect, inset: float = 0.0) -> bool:
    x, y, w, h = r
    return x + inset <= p[0] <= x + w - inset and y + inset <= p[1] <= y + h - inset


@dataclass
class Filmed:
    window: Rect
    content: Rect
    keep_out: Rect | None = None
    rest: Point | None = None
    margin_pt: float = 4.0
    #: arc sizes tried in order; a path that leaves the window or enters the keep-out takes the next
    arcs: tuple[float, ...] = (0.18, 0.1, 0.05, 0.0)
    timing: str = "DELIBERATE"
    #: a pause on the target after arriving, so the hover state reads before the action
    dwell_s: float = 0.18
    type_delay_ms: int = 65
    continuity_pt: float = 2.0
    take_ended: str | None = None
    last_pointer: Point | None = None
    gestures: list[dict[str, Any]] = field(default_factory=list)
    trace_path: str | None = None

    # ---- persistence

    def to_record(self) -> dict[str, Any]:
        out = asdict(self)
        out["gestures"] = self.gestures[-50:]
        return out

    @classmethod
    def from_record(cls, rec: dict[str, Any]) -> Filmed:
        fields = {
            k: (tuple(v) if isinstance(v, list) and k not in ("gestures",) else v) for k, v in rec.items()
        }
        return cls(**fields)

    def viewport(self, x: float, y: float) -> Point:
        """A point given in viewport CSS px (100% zoom) as global screen points."""
        return (self.content[0] + x, self.content[1] + y)

    # ---- the latch

    def check(self) -> None:
        if self.take_ended:
            raise FilmedRefusal("take_ended", f"the take ended ({self.take_ended}); start a new take")

    def end_take(self, cause: str) -> None:
        if not self.take_ended:
            self.take_ended = cause

    # ---- planning

    def admit(self, start: Point, end: Point, *, planner: Any = None) -> Any:
        """The first planned path, over the arc fallbacks, that stays in the window and out of the keep-out."""
        from jevdual import drag

        if self.keep_out is not None and _inside(end, self.keep_out):
            raise FilmedRefusal("target_in_keepout", f"{end} is inside the keep-out {self.keep_out}")
        if not _inside(end, self.window, self.margin_pt):
            raise FilmedRefusal(
                "target_outside_window", f"{end} is not inside the scene window {self.window}"
            )
        why = ""
        for arc in self.arcs:
            settings = drag.DragSettings(arc_size=arc)
            plan = drag.plan_path(start, end, settings, seed="filmed", planner=planner, timing=self.timing)
            pts = [(s.x, s.y) for s in plan.samples]
            outside = [p for p in pts[1:] if not _inside(p, self.window, self.margin_pt)]
            crossing = [p for p in pts if self.keep_out is not None and _inside(p, self.keep_out)]
            if not outside and not crossing:
                return plan
            why = (
                "leaves the window"
                if outside
                else f"enters the keep-out at {crossing[0][0]:.0f},{crossing[0][1]:.0f}"
            )
        code = "path_crosses_keepout" if "keep-out" in why else "path_outside_window"
        raise FilmedRefusal(code, f"every arc {self.arcs} {why}; route it with footwork park X Y first")

    # ---- moving

    def _continuity(self, here: Point) -> None:
        if self.last_pointer is not None and math.dist(here, self.last_pointer) > self.continuity_pt:
            self.end_take("pointer_moved_idle")
            raise FilmedRefusal(
                "pointer_moved_idle",
                f"the pointer is at {here[0]:.1f},{here[1]:.1f}, not where the last gesture left it "
                f"({self.last_pointer[0]:.1f},{self.last_pointer[1]:.1f}): someone moved it; the take ended",
            )

    def _where(self) -> Point:
        from jevdual import drag

        self.check()
        here = drag.QuartzPoster().location()
        self._continuity(here)
        return here

    async def pointer(self) -> Point:
        """Where the pointer is now, in screen points, as the system reports it. Refuses, ending the
        take, when that is not where the last gesture left it."""
        return await owned_thread(self._where)

    def _hold(self, at: Point | None) -> None:
        here = self._where()
        if at is not None and math.dist(here, at) > HELD_TOLERANCE_PT:
            self.end_take("pointer_moved_idle")
            raise FilmedRefusal(
                "pointer_moved_idle",
                f"the pointer is at {here[0]:.1f},{here[1]:.1f}, not at {at[0]:.1f},{at[1]:.1f} where it was "
                "found on the target: someone moved it; the take ended",
            )

    async def held(self, at: Point | None = None) -> None:
        """Refuse, ending the take, unless the pointer is still where the last gesture left it and,
        with ``at`` (a position ``pointer`` read and the page was asked about), still at that position."""
        await owned_thread(self._hold, at)

    def _move(self, end: Point, kind: str, label: str) -> dict[str, Any]:
        from jevdual import drag

        self.check()
        poster, clock = drag.QuartzPoster(), drag.MonotonicClock()
        here = poster.location()
        self._continuity(here)
        record: dict[str, Any] = {"kind": kind, "label": label, "from": here, "to": end}
        if math.dist(here, end) >= 1.0:
            plan = self.admit(here, end)
            from jevdual.pointer_trace import GestureTrace

            trace = GestureTrace(self, kind, label, here, end, plan) if self.trace_path else None
            result = None
            try:
                result = drag.play_move(plan, trace.poster(poster) if trace else poster, clock,
                                        drag.DragSettings(arc_size=0.0), trace=trace)
            except BaseException:
                if trace is not None:
                    trace.finish(poster, "exception", result)
                raise
            record.update(
                samples=len(plan.samples),
                duration_s=plan.samples[-1].t,
                posted=result.posted_drags,
                max_gap_ms=round(result.max_gap_s * 1000, 1),
                stall_gap_ms=(round(result.stall_gap_s * 1000, 1) if result.stall_gap_s is not None else None),
                max_post_ms=round(result.max_post_s * 1000, 1),
                max_ack_ms=round(result.max_ack_s * 1000, 1),
                outcome=result.outcome,
            )
            if result.outcome != "arrived":
                if trace is not None:
                    trace.finish(poster, result.outcome, result)
                self.end_take(result.outcome.removeprefix("aborted:"))
                self.last_pointer = None
                self.gestures.append(record)
                raise FilmedRefusal(
                    "pointer_contended",
                    f"the approach {result.outcome} after {result.posted_drags} pointer events; the take ended",
                )
            dwell_end = clock.now() + self.dwell_s
            dwell_outcome = result.outcome
            try:
                clock.sleep_until(dwell_end)
            except BaseException:
                dwell_outcome = "exception:dwell"
                raise
            finally:
                if trace is not None:
                    trace.finish(poster, dwell_outcome, result)
        else:
            if self.trace_path:
                from jevdual.pointer_trace import GestureTrace

                GestureTrace(self, kind, label, here, end).finish(poster, "arrived")
            record.update(samples=0, outcome="arrived")
        self.last_pointer = end
        self.gestures.append(record)
        return record

    async def approach(self, frame: Rect, label: str) -> dict[str, Any]:
        """Travel to the centre of ``frame`` (screen points) before an action on it."""
        x, y, w, h = frame
        return await owned_thread(self._move, (x + w / 2, y + h / 2), "approach", label)

    def place(self, point: Point | None = None) -> dict[str, Any]:
        """Setup only, off camera: put the pointer at ``point`` (or the rest position) in one move,
        with no path admission, and make it the take's continuity reference."""
        from jevdual import drag

        self.check()
        target = point if point is not None else self.rest
        if target is None:
            raise FilmedRefusal("rest_unset", "no rest position; start the take with --rest X,Y")
        poster = drag.QuartzPoster()
        here = poster.location()
        from jevdual.pointer_trace import GestureTrace

        trace = GestureTrace(self, "place", "setup", here, target) if self.trace_path else None
        outcome = "exception"
        try:
            (trace.poster(poster) if trace else poster).move(*target)
            outcome = "arrived"
        finally:
            if trace is not None:
                trace.finish(poster, outcome)
        self.last_pointer = target
        record = {
            "kind": "place",
            "label": "setup",
            "from": here,
            "to": target,
            "samples": 1,
            "outcome": "arrived",
        }
        self.gestures.append(record)
        return record

    async def park(self, point: Point | None = None) -> dict[str, Any]:
        """Travel to ``point`` (screen points), or to the rest position."""
        target = point if point is not None else self.rest
        if target is None:
            raise FilmedRefusal("rest_unset", "no rest position; start the take with --rest X,Y")
        return await owned_thread(self._move, target, "park", "rest" if point is None else "waypoint")

    async def observe_sdk(self, kind: str, label: str, target: Point | None, call: Any) -> Any:
        """Report opaque SDK input honestly; the SDK does not expose its posted samples."""
        from jevdual import drag
        from jevdual.pointer_trace import GestureTrace, uptime_raw_ns

        poster = drag.QuartzPoster()
        trace = GestureTrace(self, kind, label, poster.location(), target,
                             completeness="unavailable_sdk_samples")
        trace.record['planned_samples'] = None
        trace.record['posted_samples'] = None
        trace.record['call_started_ns'] = uptime_raw_ns()
        outcome = 'exception'
        try:
            result = await call()
            outcome = 'sdk_returned'
            return result
        finally:
            trace.record['call_returned_ns'] = uptime_raw_ns()
            trace.finish(poster, outcome)


#: how far (points) a browser take's window or web area may sit from where the take recorded it. Page
#: positions are mapped to the screen from the recorded origin, so any real displacement is a refusal;
#: this is float noise only.
SCENE_TOLERANCE_PT = 0.01


def browser_scene_change(
    pid: int, window_id: int, filmed: Filmed, url: str | None, point: Point | None = None, *,
    frames_only: bool = False,
) -> str | None:
    """Why a browser take's recorded scene no longer holds, or None when it does.

    A page position maps to a screen point only while the scene is the one the take recorded: the
    browser is the frontmost application, the scene window is its main window and where it was, the
    window's web area is where it was, and that web area shows the session's page (compared without
    the fragment). With ``point`` (screen points, where the pointer is), a system-wide hit test there
    must also land inside a web area of the scene window: page hit-testing cannot see a native surface
    lying over the page. Read through the accessibility interface; nothing is changed.

    ``frames_only`` reads only where the scene window and its web area are, which is what maps a page
    position to the screen. It is the reading for after a page action has been delivered: the action's
    own effects may change the address, the main window, the frontmost application or what lies over
    the pointer, and none of that says where the page was when the action went."""
    from jevdual import ax, posture

    if not frames_only and (front := posture.frontmost_pid()) != pid:
        return f"the browser (pid {pid}) is not the frontmost application (pid {front} is)"
    try:
        win = ax.window_element(pid, window_id)
        window, main, area = ax.frame_of(win), ax.is_main(win), ax.web_area(win)
    except ax.AXError as exc:
        return f"the scene window could not be read ({exc})"

    def off(frame: Any, recorded: Rect) -> bool:
        return any(abs(a - b) > SCENE_TOLERANCE_PT
                   for a, b in zip((frame.x, frame.y, frame.w, frame.h), recorded, strict=True))

    def spot(frame: Any) -> str:
        return f"{frame.w:.0f}x{frame.h:.0f} at {frame.x:.1f},{frame.y:.1f}"

    def recorded(rect: Rect) -> str:
        return f"{rect[2]:.0f}x{rect[3]:.0f} at {rect[0]:.1f},{rect[1]:.1f}"

    if main is not True and not frames_only:
        return "the scene window is not the browser's main window"
    if window is None or off(window, filmed.window):
        return (f"the scene window is {spot(window) if window else 'without a frame'}; "
                f"the take recorded {recorded(filmed.window)}")
    if area is None or area[0] is None:
        return "the scene window shows no web area"
    if off(area[0], filmed.content):
        return f"the page area is {spot(area[0])}; the take recorded {recorded(filmed.content)}"
    if frames_only:
        return None
    if not url or not area[1] or area[1].split("#", 1)[0] != url.split("#", 1)[0]:
        return f"the window shows {(area[1] or 'no address')[:120]!r}, not the session's page {(url or '')[:120]!r}"
    if point is not None:
        try:
            over = ax.web_area_at(point[0], point[1])
        except ax.AXError as exc:
            return f"what is under the pointer could not be read ({exc})"
        if over != (window_id, True):
            return (f"the pointer at {point[0]:.1f},{point[1]:.1f} is not over the page of the scene window "
                    + ("(another window is there)" if over[0] not in (None, window_id)
                       else "(something that is not the page is there)"))
    return None
