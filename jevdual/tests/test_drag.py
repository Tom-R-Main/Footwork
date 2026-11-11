"""The drag player against a fake poster and clock: event order, timing, and one release on every exit."""

from __future__ import annotations

import math

import pytest

pytest.importorskip("cua_driver")

import itertools

from jevdual.drag import DragPlan, DragRefused, DragSettings, Sample, plan_drag, play_drag


class FakeClock:
    def __init__(self) -> None:
        self.t = 100.0
        #: extra seconds a sleep_until overshoots by, keyed by call number
        self.oversleep: dict[int, float] = {}
        self.calls = 0

    def now(self) -> float:
        return self.t

    def sleep_until(self, t: float) -> None:
        self.calls += 1
        self.t = max(self.t, t) + self.oversleep.get(self.calls, 0.0)


class FakePoster:
    """Records events; the pointer follows each post unless a test moves it."""

    def __init__(self) -> None:
        self.events: list[tuple[str, float, float]] = []
        self.pointer = (0.0, 0.0)
        self.foreign: str | None = None
        self.foreign_after: int | None = None  # report foreign input once this many drags were posted
        self.raise_after: int | None = None

    def down(self, x, y):
        self.events.append(("down", x, y))
        self.pointer = (x, y)

    def drag(self, x, y):
        if self.raise_after is not None and self.drags() >= self.raise_after:
            raise RuntimeError("CGEventPost failed")
        self.events.append(("drag", x, y))
        self.pointer = (x, y)

    def up(self, x, y):
        self.events.append(("up", x, y))

    def escape(self):
        self.events.append(("escape", 0.0, 0.0))

    def location(self):
        return self.pointer

    def foreign_input(self):
        if self.foreign_after is not None and self.drags() >= self.foreign_after:
            return self.foreign
        return None

    def drags(self) -> int:
        return sum(1 for e in self.events if e[0] == "drag")

    def kinds(self) -> list[str]:
        out: list[str] = []
        for kind, _, _ in self.events:
            if not out or out[-1] != kind:
                out.append(kind)
        return out


START, END = (100.0, 200.0), (500.0, 260.0)


def _plan() -> DragPlan:
    return plan_drag(START, END, seed="t")


def test_a_drag_presses_moves_settles_and_releases_at_the_drop_point():
    plan, poster, clock = _plan(), FakePoster(), FakeClock()
    result = play_drag(plan, poster, clock)
    assert result.outcome == "dropped" and not result.escape_sent
    assert poster.kinds() == ["down", "drag", "up"]
    assert poster.events[0] == ("down", *START) and poster.events[-1] == ("up", *END)
    assert poster.events[-2] == ("drag", *END)
    assert result.posted_drags == len(plan.samples) - 1
    assert result.max_gap_s <= DragSettings().max_gap_s


def test_the_first_drag_waits_for_the_press_hold_and_samples_keep_their_schedule():
    plan, poster, clock = _plan(), FakePoster(), FakeClock()
    start = clock.t
    result = play_drag(plan, poster, clock)
    hold = DragSettings().press_hold_s
    # the fake clock never runs late, so every post is on time
    assert max(result.lateness_s) == pytest.approx(0.0)
    assert clock.t == pytest.approx(start + hold + plan.samples[-1].t + DragSettings().settle_s)


def test_plan_drops_repeated_endpoints_and_ends_exactly_on_the_drop_point():
    plan = _plan()
    points = [(s.x, s.y) for s in plan.samples]
    assert all(a != b for a, b in itertools.pairwise(points))
    assert points[0] == START and points[-1] == END
    assert len(points) > 60  # about 1 s at 120 Hz


def test_a_drag_too_short_to_register_is_refused_before_anything_is_posted():
    with pytest.raises(DragRefused) as err:
        plan_drag((10.0, 10.0), (13.0, 12.0))
    assert err.value.code == "drag_too_short"


def test_cancel_sends_escape_then_releases_where_the_pointer_is():
    plan, poster, clock = _plan(), FakePoster(), FakeClock()
    result = play_drag(plan, poster, clock, cancelled=lambda: poster.drags() >= 10)
    assert result.outcome == "aborted:cancelled" and result.escape_sent
    assert poster.kinds() == ["down", "drag", "escape", "up"]
    last_drag = [e for e in poster.events if e[0] == "drag"][-1]
    assert poster.events[-1] == ("up", last_drag[1], last_drag[2])
    assert [e[0] for e in poster.events].count("up") == 1


def test_a_stalled_schedule_aborts_without_posting_late_and_releases():
    plan, poster, clock = _plan(), FakePoster(), FakeClock()
    clock.oversleep[20] = 0.2  # one wake-up arrives 200 ms late
    result = play_drag(plan, poster, clock)
    assert result.outcome == "aborted:playback_stall"
    assert poster.drags() < len(plan.samples) - 1
    assert [e[0] for e in poster.events].count("up") == 1 and poster.events[-1][0] == "up"


def test_foreign_key_input_aborts_and_releases():
    plan, poster, clock = _plan(), FakePoster(), FakeClock()
    poster.foreign, poster.foreign_after = "key_down", 15
    result = play_drag(plan, poster, clock)
    assert result.outcome == "aborted:pointer_contended:key_down"
    assert poster.drags() == 15 and poster.events[-2:] == [("escape", 0.0, 0.0), ("up", *poster.pointer)]


def test_a_pointer_moved_by_someone_else_aborts_the_drag():
    plan, poster, clock = _plan(), FakePoster(), FakeClock()

    class Moved(FakePoster):
        def location(self):
            if self.drags() >= 25:
                return (self.pointer[0] + 80.0, self.pointer[1])
            return self.pointer

    poster = Moved()
    result = play_drag(plan, poster, clock)
    assert result.outcome.startswith("aborted:pointer_contended:pointer_moved")
    assert poster.drags() == 25 and [e[0] for e in poster.events].count("up") == 1


def test_an_exception_mid_drag_still_releases_the_button_once():
    plan, poster, clock = _plan(), FakePoster(), FakeClock()
    poster.raise_after = 30
    with pytest.raises(RuntimeError):
        play_drag(plan, poster, clock)
    assert [e[0] for e in poster.events].count("up") == 1 and poster.events[-1][0] == "up"


def test_a_schedule_with_a_long_interval_is_refused_at_planning():
    class Planner:
        """Stands in for cua_driver with a trajectory that has one 80 ms interval."""

        class _T:
            def samples(self):
                from types import SimpleNamespace

                return [
                    SimpleNamespace(t=i * 0.0083 + (0.08 if i > 5 else 0), x=float(i * 10), y=0.0)
                    for i in range(12)
                ]

        def default_cursor_motion_params(self):
            from types import SimpleNamespace

            return SimpleNamespace(arc_size=0.25)

        def plan_cursor_move(self, params, request):
            return self._T()

        def CursorMoveRequest(self, **kw):
            return kw

        def CursorMotionPoint(self, **kw):
            return kw

    with pytest.raises(DragRefused) as err:
        plan_drag((0.0, 0.0), (110.0, 0.0), planner=Planner())
    assert err.value.code == "schedule_exceeds_gap"


def test_samples_follow_the_planned_path_within_its_largest_step():
    plan = _plan()
    straight = math.dist(START, END)
    assert plan.max_step_pt < straight / 20
    assert isinstance(plan.samples[0], Sample)


def test_move_stall_records_failed_interval_separately_from_successful_posts():
    from jevdual.drag import play_move

    plan = DragPlan((0., 0.), (20., 0.),
                    (Sample(0, 0, 0), Sample(.01, 10, 0), Sample(.02, 20, 0)), 'test', 10)
    clock = FakeClock()
    clock.oversleep[1] = .2
    poster = FakePoster()
    poster.move = poster.drag
    result = play_move(plan, poster, clock)
    assert result.outcome == 'aborted:playback_stall'
    assert result.stall_gap_s == pytest.approx(.21)
    assert result.max_gap_s == 0 and result.posted_drags == 0 and poster.events == []


@pytest.mark.parametrize('delay_stage', ['check', 'post'])
def test_move_records_post_cost_without_hiding_slow_check_or_post(delay_stage):
    from jevdual.drag import play_move

    plan = DragPlan((0., 0.), (20., 0.),
                    (Sample(0, 0, 0), Sample(.01, 10, 0), Sample(.02, 20, 0)), 'test', 10)
    clock, poster = FakeClock(), FakePoster()

    def move(x, y):
        poster.drag(x, y)
        if delay_stage == 'post':
            clock.t += .2
    poster.move = move

    def cancel():
        if delay_stage == 'check':
            clock.t += .2
        return False
    result = play_move(plan, poster, clock, cancelled=cancel)
    assert result.outcome == 'aborted:playback_stall'
    assert result.stall_gap_s >= .2
    assert result.max_post_s == pytest.approx(.2 if delay_stage == 'post' else 0)
    assert result.posted_drags == (1 if delay_stage == 'post' else 0)
