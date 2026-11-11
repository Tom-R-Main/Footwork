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


# Unlike the CLI scenarios, this standalone Mac double does not request ``world``.
@pytest.mark.usefixtures("mac_native_contract")
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


def test_setup_placement_ignores_the_keep_out_and_sets_continuity(world, fw, filmed):
    _start(fw, "--keep-out", "0,120,300,40")
    Poster.pointer = (900.0, 900.0)  # wherever the person left it, outside the window
    code, _, err = fw("park", "--place")
    assert code == 0, err
    assert filmed.events == [("move", 440.0, 370.0)]
    assert _state(fw)["filmed"]["last_pointer"] == [440.0, 370.0]


def test_the_keep_out_is_armed_mid_take_and_refused_when_the_pointer_is_inside(world, fw, filmed):
    out = _start(fw)
    seven = _id(out, "7")
    code, _, err = fw("keep-out", "0,120,300,40")
    assert code == 0, err
    _, out, err = fw("do", "click", str(seven), "--no-judge")
    assert "path_crosses_keepout" in out + err and world.presses == []
    assert fw("keep-out", "off")[0] == 0
    assert fw("do", "click", str(seven), "--no-judge")[0] == 0 and world.presses == ["7"]
    code, _, err = fw("keep-out", "0,200,300,100")  # the pointer now rests on 7, inside it
    assert code == 4 and "pointer" in err


def test_point_rests_over_a_collapsed_group_and_refuses_an_ambiguous_name(world, fw, filmed, monkeypatch):
    from jevdual import ax

    scenes = [
        ("AXGroup", f"Scene {n}: a scene, 9 seconds", ax.Frame(440.0 + 60 * n, 500.0, 50.0, 40.0))
        for n in (1, 2)
    ]
    monkeypatch.setattr(ax, "labelled", lambda win, label: [h for h in scenes if h[1].startswith(label)])
    _start(fw)
    code, _, err = fw("point", "Scene 2:")
    assert code == 0, err
    assert _moves(filmed.events)[-1] == (585.0, 520.0) and world.presses == []
    code, _, err = fw("point", "Scene")
    assert code == 4 and "2 elements" in err


def test_filmed_start_reserves_desktop_and_subject_until_explicit_handoff(world, fw, filmed):
    from jevdual.coordination import Coordinator, app_resource

    _start(fw)
    state = _state(fw)
    token = state["coordination_token"]
    reservation, = Coordinator().status()["reservations"]
    assert reservation["token"] == token and reservation["state"] == "active"
    assert set(reservation["resources"]) == {"desktop", app_resource("Calculator")}
    Coordinator().revoke(token)
    before = len(filmed.events)
    code, _, err = fw("park")
    assert code == 7 and "reservation unavailable" in err
    assert len(filmed.events) == before
