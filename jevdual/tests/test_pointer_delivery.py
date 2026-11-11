"""The player must distinguish submitted events from native pointer delivery (PS1)."""

from __future__ import annotations

import struct
import sys
from types import SimpleNamespace

import pytest
from jevdual.drag import DragPlan, QuartzPoster, Sample, play_drag, play_move


class Clock:
    def __init__(self):
        self.t = 100.0

    def now(self):
        return self.t

    def sleep_until(self, deadline):
        self.t = max(self.t, deadline)


def plan(end=100):
    samples = tuple(Sample(i * .01, i * 5., 0.) for i in range(end // 5 + 1))
    return DragPlan((0., 0.), (float(end), 0.), samples, 'delivery', 5.)


class DelayedPoster:
    """Posts enter a queue; actual location changes only when their delivery is due."""
    def __init__(self, clock, delay=.03):
        self.clock = clock
        self.delay = delay
        self.pointer = (0., 0.)
        self.pending = []
        self.events = []
        self.max_pending = 0
        self.external = None
        self.foreign = None
        self.final_post_cost = 0.

    def flush(self):
        while self.pending and self.pending[0][0] <= self.clock.now():
            _, self.pointer = self.pending.pop(0)

    def location(self):
        self.flush()
        if self.external is not None and self.moves():
            return self.external
        return self.pointer

    def foreign_input(self):
        return self.foreign() if self.foreign else None

    def move(self, x, y):
        self.flush()
        self.events.append(('move', x, y))
        self.pending.append((self.clock.now() + self.delay, (x, y)))
        self.max_pending = max(self.max_pending, len(self.pending))
        self.clock.t += self.final_post_cost

    drag = move

    def down(self, x, y):
        self.events.append(('down', x, y))
        self.pointer = (x, y)

    def up(self, x, y):
        self.events.append(('up', x, y))

    def escape(self):
        self.events.append(('escape', 0., 0.))

    def moves(self):
        return sum(kind == 'move' for kind, *_ in self.events)


@pytest.mark.parametrize('player,success', [(play_move, 'arrived'), (play_drag, 'dropped')])
def test_delayed_own_delivery_is_acknowledged_before_next_post_and_success(player, success):
    clock = Clock()
    poster = DelayedPoster(clock)
    result = player(plan(), poster, clock)
    assert result.outcome == success
    assert poster.location() == (100., 0.)
    assert poster.max_pending == 1
    assert result.posted_drags == 20
    if player is play_drag:
        assert sum(kind == 'up' for kind, *_ in poster.events) == 1


@pytest.mark.parametrize('player', [play_move, play_drag])
def test_missing_delivery_stalls_without_queuing_more_input(player):
    clock = Clock()
    poster = DelayedPoster(clock, delay=float('inf'))
    result = player(plan(), poster, clock)
    assert result.outcome == 'aborted:playback_stall'
    assert result.stall_gap_s == pytest.approx(.05)
    assert poster.moves() == 1
    if player is play_drag:
        assert sum(kind == 'up' for kind, *_ in poster.events) == 1


@pytest.mark.parametrize('player', [play_move, play_drag])
def test_slow_final_post_cannot_return_success(player):
    clock = Clock()
    poster = DelayedPoster(clock, delay=0.)
    poster.final_post_cost = .2
    result = player(plan(5), poster, clock)
    assert result.outcome == 'aborted:playback_stall'
    assert result.stall_gap_s >= .2
    assert poster.moves() == 1
    if player is play_drag:
        assert sum(kind == 'up' for kind, *_ in poster.events) == 1


@pytest.mark.parametrize('player', [play_move, play_drag])
def test_outside_tolerance_foreign_motion_refuses_immediately_during_delivery(player):
    clock = Clock()
    poster = DelayedPoster(clock)
    poster.external = (80., 80.)
    result = player(plan(), poster, clock)
    assert result.outcome.startswith('aborted:pointer_contended:pointer_moved')
    assert poster.moves() == 1
    # No grace period permits an out-of-region pointer to return unnoticed.
    moving_start = 100.12 if player is play_drag else 100.
    assert clock.now() - moving_start < .02
    if player is play_drag:
        assert sum(kind == 'up' for kind, *_ in poster.events) == 1


@pytest.mark.parametrize('player', [play_move, play_drag])
@pytest.mark.parametrize('interruption', ['cancel', 'foreign_key'])
def test_delivery_wait_retains_cancellation_and_foreign_key_fences(player, interruption):
    clock = Clock()
    poster = DelayedPoster(clock)
    moving_start = 100.12 if player is play_drag else 100.
    interrupted = lambda: clock.now() >= moving_start + .025
    if interruption == 'foreign_key':
        poster.foreign = lambda: 'key_down' if interrupted() else None
    result = player(plan(), poster, clock,
                    cancelled=interrupted if interruption == 'cancel' else lambda: False)
    expected = 'cancelled' if interruption == 'cancel' else 'pointer_contended:key_down'
    assert result.outcome == 'aborted:' + expected
    assert poster.moves() == 1
    if player is play_drag:
        assert sum(kind == 'up' for kind, *_ in poster.events) == 1


@pytest.mark.parametrize('player', [play_move, play_drag])
def test_foreign_key_during_scheduled_sleep_refuses_before_first_move(player):
    moving_start = 100.12 if player is play_drag else 100.

    class InterruptedClock(Clock):
        def sleep_until(self, deadline):
            super().sleep_until(deadline)
            # A key arrives after the pre-sleep check but before the first move is due.
            # For drag, the initial press-hold sleep itself remains undisturbed.
            if self.now() > moving_start + .005:
                poster.foreign = lambda: 'key_down'

    clock = InterruptedClock()
    poster = DelayedPoster(clock)
    result = player(plan(), poster, clock)
    assert result.outcome == 'aborted:pointer_contended:key_down'
    assert poster.moves() == 0
    if player is play_drag:
        assert sum(kind == 'up' for kind, *_ in poster.events) == 1


@pytest.mark.parametrize('player,success', [(play_move, 'arrived'), (play_drag, 'dropped')])
def test_finite_native_float32_readback_matches_without_spatial_grace(player, success):
    clock = Clock()

    class RoundedPoster(DelayedPoster):
        def location(self):
            point = super().location()
            return struct.unpack('ff', struct.pack('ff', *point))

    poster = RoundedPoster(clock, delay=0.)
    target = (5.123456789, .123456789)
    trajectory = DragPlan((0., 0.), target,
                          (Sample(0., 0., 0.), Sample(.01, *target)), 'float32', 6.)
    result = player(trajectory, poster, clock)
    assert result.outcome == success
    assert poster.location() != target
    assert poster.location() == struct.unpack('ff', struct.pack('ff', *target))
    assert poster.moves() == 1


@pytest.mark.parametrize('player', [play_move, play_drag])
def test_post_and_delivery_share_original_budget_without_reset(player):
    clock = Clock()

    class SlowThenDelayed(DelayedPoster):
        def move(self, x, y):
            self.flush()
            self.clock.t += .03
            self.events.append(('move', x, y))
            # Delivery needs another30ms after posting returns, not from its start.
            self.pending.append((self.clock.now() + .03, (x, y)))
            self.max_pending = max(self.max_pending, len(self.pending))

        drag = move

    poster = SlowThenDelayed(clock)
    result = player(plan(5), poster, clock)
    assert result.outcome == 'aborted:playback_stall'
    assert result.stall_gap_s == pytest.approx(.05)
    assert result.max_post_s == pytest.approx(.03)
    assert result.max_ack_s == pytest.approx(.02)
    assert poster.moves() == 1 and poster.location() == (0., 0.)
    if player is play_drag:
        assert sum(kind == 'up' for kind, *_ in poster.events) == 1


def test_real_poster_prepares_cold_mouse_bridge_without_input_before_timed_playback(monkeypatch):
    clock = Clock()

    class Quartz:
        kCGEventSourceStateHIDSystemState = 1
        kCGEventSourceStateCombinedSessionState = 2
        kCGEventKeyDown = 10
        kCGEventLeftMouseDown = 1
        kCGEventRightMouseDown = 3
        kCGEventOtherMouseDown = 25
        kCGEventMouseMoved = 5
        kCGMouseButtonLeft = 0
        kCGEventSourceUserData = 42
        kCGHIDEventTap = 0

        def __init__(self):
            self.created = 0
            self.posts = []
            self.pointer = SimpleNamespace(x=0., y=0.)

        def CGEventSourceCreate(self, state):
            return object()

        def CGEventSourceCounterForEventType(self, state, kind):
            return 0

        def CGPointMake(self, x, y):
            return SimpleNamespace(x=x, y=y)

        def CGEventCreateMouseEvent(self, source, kind, point, button):
            if not self.created:
                clock.t += .2
            self.created += 1
            return {'point': point}

        def CGEventSetIntegerValueField(self, event, field, value):
            event[field] = value

        def CGEventPost(self, tap, event):
            self.posts.append(event)
            self.pointer = event['point']

        def CGEventCreate(self, source):
            return {'point': self.pointer}

        def CGEventGetLocation(self, event):
            return event['point']

    quartz = Quartz()
    monkeypatch.setitem(sys.modules, 'Quartz', quartz)
    poster = QuartzPoster()
    assert quartz.posts == [], 'bridge preparation must not move the real pointer'
    result = play_move(plan(), poster, clock)
    assert result.outcome == 'arrived'
    assert len(quartz.posts) == 20
    assert result.max_post_s < .05
