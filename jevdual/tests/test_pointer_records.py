"""Filmed input records preserve dispatch and use the Mac host-clock epoch."""
# ruff: noqa: F811
from __future__ import annotations

import json
import math
import sys

import pytest
from jevdual import drag, pointer_trace
from jevdual.filmed import Filmed

from tests.test_drag import FakeClock as DragClock
from tests.test_drag import FakePoster as DragPoster
from tests.test_filmed_session import (  # noqa: F401
    CONTENT,
    WINDOW,
    _start,
    filmed,
    fw,
    world,
)
from tests.test_session_scenarios import _id


class FakeClock(DragClock):
    def __init__(self):
        super().__init__()
        self.deadlines = []

    def sleep_until(self, deadline):
        self.deadlines.append(deadline)
        super().sleep_until(deadline)


class FakePoster(DragPoster):
    def move(self, x, y):
        self.drag(x, y)


pytestmark = pytest.mark.skipif(not hasattr(pointer_trace.time, 'CLOCK_UPTIME_RAW'), reason='macOS raw uptime')


@pytest.fixture(autouse=True)
def displays(monkeypatch):
    monkeypatch.setattr(pointer_trace, 'display_geometry', lambda: [
        {'id': 1, 'bounds': [0, 0, 1000, 1000], 'backing_scale': 2.0},
        {'id': 2, 'bounds': [-1000, 0, 1000, 1000], 'backing_scale': 1.0},
    ])


def _rows(fw):
    return [json.loads(line) for line in (fw.session / 'pointer-gestures.jsonl').read_text().splitlines()]


def _trace(tmp_path, plan=None):
    filmed = Filmed(WINDOW, CONTENT, trace_path=str(tmp_path / 'pointer-gestures.jsonl'))
    return pointer_trace.GestureTrace(filmed, 'park', 'fixture', (0, 0), (24, 0), plan)


def test_park_records_absolute_planned_and_posted_samples_and_origins(world, fw, filmed):
    _start(fw)
    before = pointer_trace.uptime_raw_ns()
    assert fw('park', '100', '200')[0] == 0
    after = pointer_trace.uptime_raw_ns()
    record = _rows(fw)[0]
    assert record['schema'] == 'pointer_gesture/1'
    assert record['clock'] == 'CLOCK_UPTIME_RAW'
    assert record['requested_target'] == [520, 530]
    assert record['final_location'] == [520, 530]
    assert record['window_origin'] == list(WINDOW[:2])
    assert record['content_origin'] == list(CONTENT[:2])
    assert record['backing_scale'] == 2
    assert record['geometry_complete'] is True
    assert record['space'] == {'coordinates': 'global_screen_points', 'origin': 'top_left', 'unit': 'pt'}
    assert all(before <= s['t_ns'] <= s['post_returned_ns'] <= after for s in record['posted_samples'])
    assert all(isinstance(s['t_ns'], int) for s in record['planned_samples'])
    assert [(s['x'], s['y']) for s in record['posted_samples']] == [(x, y) for kind, x, y in filmed.events]


def test_session_keeps_every_move_beyond_fifty(world, fw, filmed):
    _start(fw)
    for index in range(52):
        assert fw('park', str(20 + index % 2 * 100), '40')[0] == 0
    assert len(_rows(fw)) == 52
    state = json.loads((fw.session / 'session.json').read_text())
    assert len(state['filmed']['gestures']) == 50


def test_auto_approach_and_drag_are_both_recorded(world, fw, filmed):
    out = _start(fw)
    assert fw('do', 'drag', str(_id(out, '7')), str(_id(out, '8')), '--no-judge')[0] == 0
    records = _rows(fw)
    assert [r['kind'] for r in records] == ['approach', 'drag']
    drag_record = records[-1]
    assert drag_record['outcome'] == 'dropped'
    assert drag_record['posted_samples'][0]['event'] == 'down'
    assert drag_record['posted_samples'][-1]['event'] == 'up'
    assert drag_record['playback_started_ns'] <= drag_record['posted_samples'][0]['t_ns']
    assert drag_record['final_location'] == [517, 569]


def test_opaque_sdk_hover_surfaces_unavailable_samples(world, filmed, tmp_path):
    import asyncio

    from jevdual.native import NativeBridge
    from jevdual.posture import ExecutionPolicy

    from tests.test_posture import Activity

    bridge = NativeBridge(world, 77, world.window_id, policy=ExecutionPolicy("exclusive_desktop", activity=Activity()))
    bridge.filmed = Filmed(WINDOW, CONTENT, trace_path=str(tmp_path / 'pointer-gestures.jsonl'))
    nm = asyncio.run(bridge.observe())
    object.__setattr__(nm.menu.candidate(5), "operations", ("click", "hover"))
    effect = asyncio.run(bridge.act(nm, "hover", 5))
    assert effect.dispatched
    records = [json.loads(line) for line in (tmp_path / 'pointer-gestures.jsonl').read_text().splitlines()]
    assert [r['kind'] for r in records] == ['approach', 'hover_sdk']
    record = records[-1]
    assert record['completeness'] == 'unavailable_sdk_samples'
    assert record['posted_samples'] is None and record['planned_samples'] is None
    assert record['call_started_ns'] <= record['call_returned_ns']


def test_aborted_move_persists_only_successfully_posted_samples(tmp_path):
    plan = drag.DragPlan((0, 0), (24, 0), tuple(drag.Sample(i / 120, i, 0) for i in range(25)), 'test', 1)
    poster, clock = FakePoster(), FakeClock()
    trace = _trace(tmp_path, plan)
    # The player checks counters before the next post.
    poster.foreign_after = 2
    poster.foreign = 'key'
    result = drag.play_move(plan, trace.poster(poster), clock, trace=trace)
    record = trace.finish(poster, result.outcome, result)
    assert result.outcome.startswith('aborted:')
    assert len(record['posted_samples']) == 2
    assert record['final_location'] == [2, 0]


def test_poster_exception_keeps_partial_record_and_unknown_attempt(tmp_path, monkeypatch):
    from jevdual import filmed as filmed_module
    plan = drag.DragPlan((0, 0), (24, 0), tuple(drag.Sample(i / 120, i, 0) for i in range(25)), 'test', 1)
    poster = FakePoster()
    original = poster.move
    def failing_move(x, y):
        if x == 3:
            raise RuntimeError('poster failure')
        original(x, y)
    monkeypatch.setattr(poster, 'move', failing_move)
    monkeypatch.setattr(drag, 'QuartzPoster', lambda: poster)
    monkeypatch.setattr(drag, 'MonotonicClock', FakeClock)
    monkeypatch.setattr(filmed_module.Filmed, 'admit', lambda *args: plan)
    filmed_state = Filmed((0, 0, 100, 100), (0, 0, 100, 100), trace_path=str(tmp_path / 'pointer-gestures.jsonl'))
    with pytest.raises(RuntimeError, match='poster failure'):
        filmed_state._move((24, 0), 'park', 'fixture')
    record = json.loads((tmp_path / 'pointer-gestures.jsonl').read_text())
    assert len(record['posted_samples']) == 2
    assert record['post_errors'][0]['x'] == 3
    assert record['outcome'] == 'exception'
    assert record['completeness'] == 'post_error_outcome_unknown'


def test_real_clock_brackets_recorded_dispatch_and_planned_anchor(tmp_path):
    plan = drag.DragPlan((0, 0), (2, 0), (drag.Sample(0, 0, 0), drag.Sample(.002, 1, 0),
                                        drag.Sample(.004, 2, 0)), 'test', 1)
    poster = FakePoster()
    before = pointer_trace.uptime_raw_ns()
    trace = _trace(tmp_path, plan)
    result = drag.play_move(plan, trace.poster(poster), drag.MonotonicClock(), trace=trace)
    record = trace.finish(poster, result.outcome, result)
    after = pointer_trace.uptime_raw_ns()
    assert before <= record['t0_ns'] <= record['posted_samples'][0]['t_ns']
    assert all(before <= s['t_ns'] <= s['post_returned_ns'] <= after for s in record['posted_samples'])
    assert record['planned_samples'][-1]['t_ns'] - record['t0_ns'] == 4_000_000


def test_target_scale_uses_secondary_display_and_missing_geometry_is_explicit(tmp_path, monkeypatch):
    trace = _trace(tmp_path)
    assert trace.scale_at((-40, 10)) == 1
    secondary = Filmed(WINDOW, CONTENT)
    assert pointer_trace.GestureTrace(secondary, 'park', 'secondary', (-50, 10), (-40, 10)).record['backing_scale'] == 1
    monkeypatch.setattr(pointer_trace, 'display_geometry', list)
    assert _trace(tmp_path).record['geometry_complete'] is False


def test_instrumentation_preserves_uninstrumented_posts_deadlines_and_outcomes(tmp_path):
    for player in (drag.play_move, drag.play_drag):
        plan = drag.DragPlan((0, 0), (24, 0), tuple(drag.Sample(i / 120, i, 0) for i in range(25)), 'test', 1)
        a, b, ca, cb = FakePoster(), FakePoster(), FakeClock(), FakeClock()
        expected = player(plan, a, ca)
        trace = _trace(tmp_path, plan)
        actual = player(plan, trace.poster(b), cb, trace=trace)
        assert a.events == b.events
        assert ca.t == cb.t and ca.calls == cb.calls
        assert ca.deadlines == cb.deadlines
        assert actual.outcome == expected.outcome
        assert actual.lateness_s == expected.lateness_s
        assert math.isclose(actual.max_gap_s, expected.max_gap_s)


def test_restarted_session_gets_fresh_trace_and_refused_start_preserves_it(world, fw, filmed):
    _start(fw)
    assert fw('park', '100', '200')[0] == 0
    original = (fw.session / 'pointer-gestures.jsonl').read_text()
    assert fw('start', 'bad', '--app', 'does-not-exist')[0] != 0
    assert (fw.session / 'pointer-gestures.jsonl').read_text() == original
    _start(fw)
    assert not (fw.session / 'pointer-gestures.jsonl').exists()


def test_point_and_automatic_click_each_leave_a_record(world, fw, filmed, monkeypatch):
    from jevdual import ax

    monkeypatch.setattr(ax, 'labelled', lambda win, label: [('AXButton', '7', ax.Frame(439, 545, 48, 48))])
    out = _start(fw)
    assert fw('point', '7')[0] == 0
    assert fw('do', 'click', str(_id(out, '8')), '--no-judge')[0] == 0
    assert [r['kind'] for r in _rows(fw)] == ['approach', 'approach']
    assert world.presses == ['8']


def test_foreground_sdk_click_is_explicitly_incomplete(world, filmed, tmp_path):
    import asyncio

    from jevdual.native import NativeBridge
    from jevdual.posture import ExecutionPolicy

    from tests.test_posture import Activity

    bridge = NativeBridge(world, 77, world.window_id, policy=ExecutionPolicy('exclusive_desktop', activity=Activity()))
    bridge.filmed = Filmed(WINDOW, CONTENT, trace_path=str(tmp_path / 'pointer-gestures.jsonl'))
    nm = asyncio.run(bridge.observe())
    asyncio.run(bridge._click_token(nm.tokens[5], foreground=True, target_point=(463, 569)))
    record = json.loads((tmp_path / 'pointer-gestures.jsonl').read_text())
    assert record['kind'] == 'foreground_click'
    assert record['requested_target'] == [463, 569]
    assert record['completeness'] == 'unavailable_sdk_samples'
    assert record['posted_samples'] is None


def test_owned_titlebar_click_and_restore_are_traced_without_extra_events(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from jevdual import ax

    events = []
    back = SimpleNamespace(x=12, y=34)
    quartz = SimpleNamespace(CGEventCreate=lambda _: object(), CGEventGetLocation=lambda _: back,
                             CGEventCreateMouseEvent=lambda _, kind, xy, button: (kind, xy),
                             CGEventPost=lambda tap, event: events.append(event),
                             CGWarpMouseCursorPosition=lambda point: events.append(('warp', point.x, point.y)),
                             kCGEventLeftMouseDown=1, kCGEventLeftMouseUp=2, kCGHIDEventTap=0,
                             kCGMouseButtonLeft=0)
    monkeypatch.setitem(sys.modules, 'Quartz', quartz)
    monkeypatch.setattr(ax.time if hasattr(ax, 'time') else pointer_trace.time, 'sleep', lambda _: None)
    trace = _trace(tmp_path)
    ax.click_at(24, 56, trace=trace)
    assert events == [(1, (24, 56)), (2, (24, 56)), ('warp', 12, 34)]
    assert [(p[2], p[3], p[4]) for p in trace.posts] == [(24, 56, 'down'), (24, 56, 'up'), (12, 34, 'warp')]


def test_dwell_exception_keeps_the_successfully_posted_move(tmp_path, monkeypatch):
    plan = drag.DragPlan((0, 0), (2, 0), (drag.Sample(0, 0, 0), drag.Sample(.01, 2, 0)), 'test', 2)
    class DwellClock(FakeClock):
        def sleep_until(self, deadline):
            if self.calls == 1:
                raise KeyboardInterrupt
            super().sleep_until(deadline)

    poster = FakePoster()
    monkeypatch.setattr(drag, 'QuartzPoster', lambda: poster)
    monkeypatch.setattr(drag, 'MonotonicClock', DwellClock)
    monkeypatch.setattr(Filmed, 'admit', lambda *args: plan)
    filmed_state = Filmed((0, 0, 100, 100), (0, 0, 100, 100), trace_path=str(tmp_path / 'pointer-gestures.jsonl'))
    with pytest.raises(KeyboardInterrupt):
        filmed_state._move((2, 0), 'park', 'fixture')
    record = json.loads((tmp_path / 'pointer-gestures.jsonl').read_text())
    assert len(record['posted_samples']) == 1
    assert record['final_location'] == [2, 0]
    assert record['outcome'] == 'exception:dwell'


def test_setup_exception_before_post_is_not_reported_as_arrived(tmp_path, monkeypatch):
    class BrokenPoster(FakePoster):
        def record_posts(self, trace):
            pass  # model failure before reaching the Quartz posting boundary

        def move(self, x, y):
            raise RuntimeError('event creation failed')

    monkeypatch.setattr(drag, 'QuartzPoster', BrokenPoster)
    path = tmp_path / 'pointer-gestures.jsonl'
    film = Filmed((0, 0, 100, 100), (0, 0, 100, 100), trace_path=str(path))
    with pytest.raises(RuntimeError, match='event creation failed'):
        film.place((24, 24))
    record = json.loads(path.read_text())
    assert record['outcome'] == 'exception'
    assert record['posted_samples'] == []


def test_metadata_preparation_is_not_reported_as_playback_start(tmp_path, monkeypatch):
    raw = [100]
    monkeypatch.setattr(pointer_trace, 'uptime_raw_ns', lambda: raw[0])
    def delayed_geometry():
        raw[0] = 1_000_000_000
        return [{'id': 1, 'bounds': [0, 0, 1000, 1000], 'backing_scale': 2}]
    monkeypatch.setattr(pointer_trace, 'display_geometry', delayed_geometry)
    plan = drag.DragPlan((0, 0), (2, 0), (drag.Sample(0, 0, 0), drag.Sample(.01, 2, 0)), 'test', 2)
    trace = _trace(tmp_path, plan)
    assert trace.record['recording_started_ns'] == 100
    assert trace.record['playback_started_ns'] is None
    poster, clock = FakePoster(), FakeClock()
    result = drag.play_move(plan, trace.poster(poster), clock, trace=trace)
    record = trace.finish(poster, result.outcome, result)
    assert record['playback_started_ns'] == record['t0_ns'] == 1_000_000_000


def test_no_input_and_opaque_sdk_do_not_claim_a_playback_start(tmp_path):
    trace = _trace(tmp_path)
    trace.finish(FakePoster(), 'arrived')
    assert trace.record['playback_started_ns'] is None and trace.record['t0_ns'] is None
