"""``footwork do drag <source> <destination>`` end to end on the simulated Mac (notebook PD2).

The poster and clock are replaced, so the scenarios see every pointer event the command would post; the
rest of the command (observation, resolution, posture, judgment, authorization, receipts) is real.
"""

from __future__ import annotations

import pytest

pytest.importorskip("cua_driver")

from tests.test_session_scenarios import _id, _mac_selectors, _state, fw, world  # noqa: F401


class Poster:
    events: list[tuple[str, float, float]] = []

    def __init__(self) -> None:
        self.pointer = (10.0, 10.0)

    def move(self, x, y):
        Poster.events.append(("move", x, y))
        self.pointer = (x, y)

    def down(self, x, y):
        Poster.events.append(("down", x, y))

    def drag(self, x, y):
        Poster.events.append(("drag", x, y))
        self.pointer = (x, y)

    def up(self, x, y):
        Poster.events.append(("up", x, y))

    def escape(self):
        Poster.events.append(("escape", 0.0, 0.0))

    def location(self):
        return self.pointer

    def foreign_input(self):
        return None


class Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def now(self):
        return self.t

    def sleep_until(self, t):
        self.t = max(self.t, t)


@pytest.fixture
def poster(monkeypatch):
    from jevdual import drag

    Poster.events = []
    monkeypatch.setattr(drag, "QuartzPoster", Poster)
    monkeypatch.setattr(drag, "MonotonicClock", Clock)
    return Poster


def _centre(world, label):
    el = next(e for e in world.base["elements"] if e.get("label") == label)
    f = el["frame"]
    return (f["x"] + f["w"] / 2, f["y"] + f["h"] / 2)


def _kinds(events):
    out = []
    for kind, _, _ in events:
        if not out or out[-1] != kind:
            out.append(kind)
    return out


def test_a_drag_approaches_presses_on_the_source_and_releases_on_the_destination(world, fw, poster):
    _, out, _ = fw("start", "Drag a key", "--app", "Calculator", "--mode", "exclusive_desktop")
    seven, eight = _id(out, "7"), _id(out, "8")
    code, out, err = fw("do", "drag", str(seven), str(eight), "--no-judge")
    assert code == 0, err
    assert _kinds(poster.events) == ["move", "down", "drag", "up"]
    down = next(e for e in poster.events if e[0] == "down")
    assert down[1:] == _centre(world, "7")
    assert poster.events[-1] == ("up", *_centre(world, "8"))
    assert sum(1 for e in poster.events if e[0] == "drag") > 5
    assert "dispatched drag(7 -> 8)" in out
    assert _state(fw)["memory"][-1].startswith("step 1: drag(7 -> 8)")


def test_background_only_posts_nothing_and_says_the_drag_needs_the_desktop(world, fw, poster):
    _, out, _ = fw("start", "Drag a key", "--app", "Calculator")
    code, out, _ = fw("do", "drag", str(_id(out, "7")), str(_id(out, "8")), "--no-judge")
    assert poster.events == []
    assert "requires_desktop" in out


def test_a_destination_not_on_the_observation_posts_nothing(world, fw, poster):
    _, out, _ = fw("start", "Drag a key", "--app", "Calculator", "--mode", "exclusive_desktop")
    code, _, err = fw("do", "drag", str(_id(out, "7")), "9999", "--no-judge")
    assert code == 4 and "9999" in err and poster.events == []


def test_dropping_onto_delete_pauses_before_anything_is_posted(world, fw, poster):
    _, out, _ = fw("start", "Drag a key", "--app", "Calculator", "--mode", "exclusive_desktop")
    code, out, _ = fw("do", "drag", str(_id(out, "7")), "Delete", "--no-judge")
    assert code == 3 and "paused before dispatch" in out and poster.events == []


def test_a_drag_needs_two_targets(world, fw, poster):
    fw("start", "Drag a key", "--app", "Calculator", "--mode", "exclusive_desktop")
    with pytest.raises(SystemExit) as exc:
        fw("do", "drag", "7", "--no-judge")
    assert "drag needs a source and a destination" in str(exc.value)
    assert poster.events == []
