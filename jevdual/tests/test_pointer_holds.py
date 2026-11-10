"""scripts/pointer_holds.py on a simulated pointer and clock: holds, timings, and contention."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from jevdual import drag

_spec = importlib.util.spec_from_file_location(
    "pointer_holds", Path(__file__).parent.parent / "scripts" / "pointer_holds.py"
)
holds = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(holds)


class Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def now(self):
        return self.t

    def sleep_until(self, t):
        self.t = max(self.t + 1e-4, t)


class Poster:
    def __init__(self, clock, start=(10.0, 10.0)) -> None:
        self.clock, self.at, self.moves, self.nudge_at = clock, start, [], None

    def move(self, x, y):
        self.moves.append((x, y))
        self.at = (x, y)

    def location(self):
        if self.nudge_at is not None and self.clock.t >= self.nudge_at:
            return (self.at[0] + 3, self.at[1])
        return self.at

    def foreign_input(self):
        return None


def _straight(a, b):
    n = 20
    return drag.DragPlan(
        start=a,
        end=b,
        samples=tuple(
            drag.Sample(t=k * 0.01, x=a[0] + (b[0] - a[0]) * k / n, y=a[1] + (b[1] - a[1]) * k / n)
            for k in range(n + 1)
        ),
        seed="test",
        max_step_pt=max(abs(b[0] - a[0]), abs(b[1] - a[1])) / n,
    )


def _run(poster, clock, targets, hold_s=0.3):
    out = []
    code = holds.run_holds(
        targets, hold_s, poster, clock, lambda: int(clock.t * 1e9), plan=_straight, emit=out.append
    )
    return code, out


def test_each_point_is_held_for_the_hold_and_timed_on_the_given_clock():
    clock = Clock()
    poster = Poster(clock)
    targets = [(100.0, 100.0), (300.0, 120.0), (300.0, 120.0)]
    code, out = _run(poster, clock, targets)
    assert code == 0 and [r["outcome"] for r in out] == ["held"] * 3
    for r, t in zip(out, targets, strict=True):
        assert r["target"] == list(t) and r["held_ms"] >= 300 and r["max_drift_pt"] == 0
        assert r["arrive_ns"] < r["depart_ns"]
    assert out[0]["depart_ns"] <= out[1]["arrive_ns"]
    assert poster.moves[-1] == targets[-1] and len(poster.moves) > 20  # travelled, not jumped


def test_a_pointer_nudged_during_a_hold_stops_the_run():
    clock = Clock()
    poster = Poster(clock)
    poster.nudge_at = 0.4  # inside the first hold (travel 0.2 s, hold to ~0.5 s)
    code, out = _run(poster, clock, [(100.0, 100.0), (300.0, 120.0)])
    assert code == 3 and out[-1]["outcome"] == "contended:pointer_moved" and len(out) == 1
