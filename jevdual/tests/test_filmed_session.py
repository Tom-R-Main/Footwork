"""A filmed take on the simulated Mac: the pointer travels before each action (notebook FT2).

The poster, clock and AX geometry are replaced; observation, resolution, gates and delivery are real.
The window is (420, 300, 300, 480) in screen points and its content starts at (420, 330).
"""

# ruff: noqa: F811  (the scenario fixtures are imported by name)
from __future__ import annotations

import math
from typing import ClassVar

import pytest

pytest.importorskip("cua_driver")

import itertools

from tests.test_session_scenarios import _id, _mac_selectors, _state, fw, world  # noqa: F401

WINDOW = (420.0, 300.0, 300.0, 480.0)
CONTENT = (420.0, 330.0, 300.0, 450.0)
SEVEN, EQUALS = (463.0, 569.0), (625.0, 731.0)


class Poster:
    events: ClassVar[list[tuple[str, float, float]]] = []
    pointer: ClassVar[tuple[float, float]] = (600.0, 400.0)

    def move(self, x, y):
        Poster.events.append(("move", x, y))
        Poster.pointer = (x, y)

    def down(self, x, y):
        Poster.events.append(("down", x, y))

    def drag(self, x, y):
        Poster.events.append(("drag", x, y))
        Poster.pointer = (x, y)

    def up(self, x, y):
        Poster.events.append(("up", x, y))

    def escape(self):
        Poster.events.append(("escape", 0.0, 0.0))

    def location(self):
        return Poster.pointer

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
def filmed(monkeypatch, world):
    from jevdual import ax, drag

    Poster.events, Poster.pointer = [], (600.0, 400.0)
    monkeypatch.setattr(drag, "QuartzPoster", Poster)
    monkeypatch.setattr(drag, "MonotonicClock", Clock)
    monkeypatch.setattr(ax, "window_element", lambda pid, wid: object())
    monkeypatch.setattr(ax, "frame_of", lambda el: ax.Frame(*WINDOW))
    monkeypatch.setattr(ax, "web_area_frame", lambda el: ax.Frame(*CONTENT))
    return Poster


def _start(fw, *extra):
    code, out, err = fw(
        "start",
        "Film a calculation",
        "--app",
        "Calculator",
        "--mode",
        "exclusive_desktop",
        "--pointer-motion",
        "filmed",
        "--rest",
        "20,40",
        *extra,
    )
    assert code == 0, err
    return out


def _moves(events):
    return [(x, y) for kind, x, y in events if kind == "move"]


def test_a_filmed_click_travels_to_the_target_then_presses_it_as_before(world, fw, filmed):
    out = _start(fw)
    code, _, err = fw("do", "click", str(_id(out, "7")), "--no-judge")
    assert code == 0, err
    moves = _moves(filmed.events)
    assert len(moves) > 20 and moves[-1] == SEVEN
    assert all(math.dist(a, b) < 25 for a, b in itertools.pairwise(moves))  # no jump
    assert world.presses == ["7"]  # delivery is the same AX press
    assert _state(fw)["filmed"]["last_pointer"] == list(SEVEN)


def test_park_rests_at_the_rest_position_and_a_waypoint_is_in_viewport_px(world, fw, filmed):
    _start(fw)
    code, _, err = fw("park")
    assert code == 0, err
    assert _moves(filmed.events)[-1] == (440.0, 370.0)
    code, _, err = fw("park", "100", "200")
    assert code == 0, err
    assert _moves(filmed.events)[-1] == (520.0, 530.0)


def test_a_path_through_the_keep_out_on_every_arc_is_refused_before_moving(world, fw, filmed):
    # a band across the window between the pointer (y 400) and the 7 key (y 569)
    out = _start(fw, "--keep-out", "0,120,300,40")
    _code, out, err = fw("do", "click", str(_id(out, "7")), "--no-judge")
    assert "path_crosses_keepout" in out + err
    assert filmed.events == [] and world.presses == []


def test_a_target_inside_the_keep_out_is_refused(world, fw, filmed):
    out = _start(fw, "--keep-out", "0,200,300,100")
    _, out, err = fw("do", "click", str(_id(out, "7")), "--no-judge")
    assert "target_in_keepout" in out + err and world.presses == []


def test_a_pointer_moved_between_commands_ends_the_take_and_every_filmed_route_refuses(world, fw, filmed):
    out = _start(fw)
    seven, equals = _id(out, "7"), _id(out, "Equals")
    assert fw("do", "click", str(seven), "--no-judge")[0] == 0
    Poster.pointer = (700.0, 320.0)  # the person nudged the mouse
    _, out, err = fw("do", "click", str(equals), "--no-judge")
    assert "pointer_moved_idle" in out + err
    _, out, err = fw("do", "click", str(equals), "--no-judge")
    assert "take_ended" in out + err
    code, _, err = fw("park")
    assert code == 4 and "take_ended" in err
    assert world.presses == ["7"]


def test_the_rest_position_inside_the_keep_out_is_refused_at_start(world, fw, filmed):
    code, _, err = fw(
        "start",
        "Film",
        "--app",
        "Calculator",
        "--mode",
        "exclusive_desktop",
        "--pointer-motion",
        "filmed",
        "--rest",
        "20,40",
        "--keep-out",
        "0,0,100,100",
    )
    assert code == 2 and "rest position is inside the keep-out" in err


def test_filmed_needs_the_exclusive_desktop(world, fw, filmed):
    code, _, err = fw("start", "Film", "--app", "Calculator", "--pointer-motion", "filmed")
    assert code == 2 and "exclusive_desktop" in err


def test_a_labelled_web_group_is_a_hover_target_and_an_unlabelled_one_is_not():
    from types import SimpleNamespace

    from jevdual.native import menu_from_snapshot

    def group(i, label):
        return {
            "element_index": i,
            "role": "AXGroup",
            "label": label,
            "element_token": f"s1:{i}",
            "frame": {"x": 10.0 * i, "y": 10.0, "w": 100.0, "h": 50.0},
            "actions": ["AXShowMenu"],
            "in_web_content": True,
        }

    snap = SimpleNamespace(
        snapshot_id="s1",
        app_name="Google Chrome",
        window_title="DemoGeek",
        pid=1,
        window_id=2,
        elements_complete=True,
        tree_markdown="",
        elements=[group(1, "Scene 1: A delivery fails, 3 seconds"), group(2, "")],
    )
    nm = menu_from_snapshot(snap)
    scenes = [c for c in nm.menu.candidates if c.role == "group"]
    assert [(c.label, c.operations) for c in scenes] == [("Scene 1: A delivery fails, 3 seconds", ("hover",))]


def test_filmed_typing_paces_the_characters(monkeypatch):
    import asyncio
    import json

    from jevdual.native import NativeBridge
    from jevdual.posture import ExecutionPolicy

    from tests.test_posture import Activity, FakeDriver, doc_snapshot

    class Film:
        type_delay_ms = 72

        async def approach(self, frame, label):
            return {}

        def check(self):
            return None

    d = FakeDriver(doc_snapshot(""))
    b = NativeBridge(d, 1, 2, policy=ExecutionPolicy("exclusive_desktop", activity=Activity()))
    b.filmed = Film()
    nm = asyncio.run(b.observe())
    text = next(c for c in nm.menu.candidates if c.role == "textbox" and c.label == "Search")
    object.__setattr__(nm, "web", frozenset({text.id}))
    asyncio.run(b.act(nm, "type", text.id, "hello"))
    typed = [args for name, args in d.calls if name == "type_text"]
    assert typed and typed[0]["delay_ms"] == 72, d.calls
    assert json.dumps(typed[0])
