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


@pytest.mark.parametrize("failure", ["observation", "binding_mismatch"])
def test_failed_filmed_replacement_start_revokes_the_reservation_it_created(world, fw, filmed, monkeypatch, failure):
    """A staged replacement start (existing session files) must not strand the take reservation it made."""
    from jevdual.coordination import Coordinator

    assert fw("start", "Plain earlier task", "--app", "Calculator")[0] == 0
    assert not _state(fw).get("coordination_token")
    before = (fw.session / "session.json").read_bytes()
    original = world.get_window_state

    async def observe(inp):
        if failure == "observation":
            raise RuntimeError("new observation unavailable")
        result = await original(inp)
        result["pid"] = 88
        return result

    monkeypatch.setattr(world, "get_window_state", observe)
    extra = ("--pid", "77", "--window-id", "40335") if failure == "binding_mismatch" else ()
    code, out, err = fw("start", "Film a replacement", "--app", "Calculator", "--mode", "exclusive_desktop",
                        "--pointer-motion", "filmed", "--rest", "20,40", *extra)
    assert code != 0, (out, err)
    assert (fw.session / "session.json").read_bytes() == before
    assert [r for r in Coordinator().status()["reservations"] if r["state"] == "active"] == []


def test_a_browser_session_films_the_pointer_over_its_own_window(world, fw, filmed, monkeypatch):
    """B7: one start --browser session binds the page and films the real pointer over the same window,
    under the same desktop reservation a native filmed take holds."""
    from jevdual import browser_driver, browser_target
    from jevdual.coordination import Coordinator
    from jevdual.native import NativeBridge

    monkeypatch.setattr(browser_target, "_catalog", lambda pid: (
        {"pid": pid, "incarnation": 1.0}, [{"type": "page", "id": "page-1", "url": "app://Calculator"}]))

    async def browser(url, policy):
        bridge = NativeBridge(world, 77, 40335)
        bridge.tab_id = "owned-browser-tab"
        return world, bridge

    monkeypatch.setattr(browser_driver, "bind_footwork_chrome", browser)
    code, out, err = fw("start", "Film the page", "--browser", "--mode", "exclusive_desktop",
                        "--pointer-motion", "filmed", "--rest", "20,40")
    assert code == 0, (out, err)
    state = _state(fw)
    assert state["mode"] == "browser" and state["filmed"]["content"] == list(CONTENT)
    reservation, = Coordinator().status()["reservations"]
    assert reservation["token"] == state["coordination_token"] and "desktop" in reservation["resources"]
    before = len(filmed.events)
    code, _, err = fw("park")
    assert code == 0, err
    assert len(filmed.events) > before


def test_a_browser_filmed_take_needs_the_exclusive_desktop(world, fw, filmed, monkeypatch):
    from jevdual import browser_driver, browser_target
    from jevdual.coordination import Coordinator
    from jevdual.native import NativeBridge

    monkeypatch.setattr(browser_target, "_catalog", lambda pid: (
        {"pid": pid, "incarnation": 1.0}, [{"type": "page", "id": "page-1", "url": "app://Calculator"}]))

    async def browser(url, policy):
        bridge = NativeBridge(world, 77, 40335)
        bridge.tab_id = "owned-browser-tab"
        return world, bridge

    monkeypatch.setattr(browser_driver, "bind_footwork_chrome", browser)
    code, _, err = fw("start", "Film the page", "--browser", "--pointer-motion", "filmed")
    assert code == 2 and "exclusive_desktop" in err, err
    assert Coordinator().status()["reservations"] == []


def test_a_cancelled_browser_start_releases_the_reservation_it_created(world, fw, filmed, monkeypatch):
    """Sol round 3 #3: cancellation after the filmed reservation (here at the first navigation) must
    not leave the desktop reserved with no session published."""
    import asyncio

    from jevdual import browser_driver, browser_target
    from jevdual.coordination import Coordinator
    from jevdual.native import NativeBridge

    monkeypatch.setattr(browser_target, "_catalog", lambda pid: (
        {"pid": pid, "incarnation": 1.0}, [{"type": "page", "id": "page-1", "url": "app://Calculator"}]))

    async def browser(url, policy):
        bridge = NativeBridge(world, 77, 40335)
        bridge.tab_id = "owned-browser-tab"
        return world, bridge

    async def cancelled(self, url):
        raise asyncio.CancelledError

    monkeypatch.setattr(browser_driver, "bind_footwork_chrome", browser)
    monkeypatch.setattr(NativeBridge, "navigate", cancelled, raising=False)
    with pytest.raises(BaseException) as raised:
        fw("start", "Film the page", "--browser", "--mode", "exclusive_desktop", "--pointer-motion", "filmed",
           "--rest", "20,40", "--url", "https://example.test/")
    assert isinstance(raised.value, (asyncio.CancelledError, KeyboardInterrupt, SystemExit)), raised.value
    assert [r for r in Coordinator().status()["reservations"] if r["state"] == "active"] == []
    assert not (fw.session / "session.json").exists()


def _browser_scene(monkeypatch, *, front=77, url=None, area=CONTENT, over=(40335, True)):
    """What the accessibility interface and the window server say about the filmed browser window."""
    from jevdual import ax, posture

    from tests.test_filmed_page_pointer import URL

    monkeypatch.setattr(posture, "frontmost_pid", lambda: front)
    monkeypatch.setattr(ax, "is_main", lambda el: True)
    monkeypatch.setattr(ax, "web_area", lambda el: (ax.Frame(*area), url or URL))
    monkeypatch.setattr(ax, "web_area_at", lambda x, y: over)


def test_a_filmed_browser_click_travels_to_the_page_target_before_the_page_click(world, fw, filmed, monkeypatch):
    """FP1: in a filmed start --browser session, do click moves the real pointer to the target's centre on
    screen (the content origin plus the ref's viewport rectangle) before the driver's page click."""
    from jevdual import browser_driver, browser_target
    from jevdual.browser_driver import BrowserBridge

    from tests.test_filmed_page_pointer import URL, Wire

    log: list = []
    monkeypatch.setattr(browser_target, "_catalog", lambda pid: (
        {"pid": pid, "incarnation": 1.0}, [{"type": "page", "id": "page-1", "url": URL}]))

    async def browser(url, policy):
        wire = Wire(log)
        return wire, BrowserBridge(wire, 77, 40335, policy=policy)

    monkeypatch.setattr(browser_driver, "bind_footwork_chrome", browser)
    monkeypatch.setattr(browser_driver, "configured_driver", lambda pid: Wire(log))
    _browser_scene(monkeypatch)
    code, out, err = fw("start", "Film the page", "--browser", "--mode", "exclusive_desktop",
                        "--pointer-motion", "filmed", "--rest", "20,40")
    assert code == 0, (out, err)
    assert _state(fw)["filmed"]["content"] == list(CONTENT)
    code, _, err = fw("do", "click", str(_id(out, "Go")), "--no-judge")
    assert code == 0, err
    go = (CONTENT[0] + 40.0 + 80.0 / 2, CONTENT[1] + 100.0 + 30.0 / 2)  # ref rect (40, 100, 80, 30)
    assert _moves(filmed.events)[-1] == go
    assert log[-1] == ("browser_click", "snap-1:1")
    assert _state(fw)["filmed"]["last_pointer"] == list(go)


def test_a_filmed_browser_click_on_a_covered_target_sends_nothing_and_moves_nothing(world, fw, filmed, monkeypatch):
    """FP4: when another element is at the target's centre, do click reports target_unlocated; the pointer
    stays where it was and the page receives no click."""
    from jevdual import browser_driver, browser_target
    from jevdual.browser_driver import BrowserBridge

    from tests.test_filmed_page_pointer import URL, Wire, at

    log: list = []
    monkeypatch.setattr(browser_target, "_catalog", lambda pid: (
        {"pid": pid, "incarnation": 1.0}, [{"type": "page", "id": "page-1", "url": URL}]))

    async def browser(url, policy):
        wire = Wire(log)
        return wire, BrowserBridge(wire, 77, 40335, policy=policy)

    monkeypatch.setattr(browser_driver, "bind_footwork_chrome", browser)
    monkeypatch.setattr(browser_driver, "configured_driver", lambda pid: Wire(log, [at(hit="other")]))
    _browser_scene(monkeypatch)
    code, out, err = fw("start", "Film the page", "--browser", "--mode", "exclusive_desktop",
                        "--pointer-motion", "filmed", "--rest", "20,40")
    assert code == 0, (out, err)
    before = len(filmed.events)
    code, out, err = fw("do", "click", str(_id(out, "Go")), "--no-judge")
    assert "target_unlocated" in out + err and "another element is at its centre" in out + err, (code, out, err)
    assert len(filmed.events) == before
    assert [entry[0] for entry in log if entry[0] != "locate"] == []


@pytest.mark.parametrize(("scene", "why"), [
    ({"front": 501}, "not the frontmost application"),
    ({"url": "https://example.invalid/another-tab"}, "not the session's page"),
    ({"area": (420.0, 370.0, 300.0, 410.0)}, "the page area is 300x410"),
])
def test_a_filmed_browser_click_in_a_changed_scene_sends_nothing_and_moves_nothing(
        world, fw, filmed, monkeypatch, scene, why):
    """FP9: the window on screen must still be the scene the take recorded (the browser in front, its web
    area where it was, showing the session's page) before the pointer moves; otherwise do click reports
    scene_changed and neither the pointer nor the page is touched."""
    from jevdual import browser_driver, browser_target
    from jevdual.browser_driver import BrowserBridge

    from tests.test_filmed_page_pointer import URL, Wire

    log: list = []
    monkeypatch.setattr(browser_target, "_catalog", lambda pid: (
        {"pid": pid, "incarnation": 1.0}, [{"type": "page", "id": "page-1", "url": URL}]))

    async def browser(url, policy):
        wire = Wire(log)
        return wire, BrowserBridge(wire, 77, 40335, policy=policy)

    monkeypatch.setattr(browser_driver, "bind_footwork_chrome", browser)
    monkeypatch.setattr(browser_driver, "configured_driver", lambda pid: Wire(log))
    code, out, err = fw("start", "Film the page", "--browser", "--mode", "exclusive_desktop",
                        "--pointer-motion", "filmed", "--rest", "20,40")
    assert code == 0, (out, err)
    _browser_scene(monkeypatch, **scene)
    before = len(filmed.events)
    code, out, err = fw("do", "click", str(_id(out, "Go")), "--no-judge")
    assert "scene_changed" in out + err and why in out + err, (code, out, err)
    assert len(filmed.events) == before
    assert log == []


def _filmed_page(monkeypatch, fw, log, **wire):
    """A filmed browser session on the page fixture, whose driver answers a click with ``wire``."""
    from jevdual import browser_driver, browser_target
    from jevdual.browser_driver import BrowserBridge

    from tests.test_filmed_page_pointer import URL, Wire

    monkeypatch.setattr(browser_target, "_catalog", lambda pid: (
        {"pid": pid, "incarnation": 1.0}, [{"type": "page", "id": "page-1", "url": URL}]))

    async def browser(url, policy):
        first = Wire(log)
        return first, BrowserBridge(first, 77, 40335, policy=policy)

    monkeypatch.setattr(browser_driver, "bind_footwork_chrome", browser)
    monkeypatch.setattr(browser_driver, "configured_driver", lambda pid: Wire(log, **wire))
    _browser_scene(monkeypatch)
    code, out, err = fw("start", "Film the page", "--browser", "--mode", "exclusive_desktop",
                        "--pointer-motion", "filmed", "--rest", "20,40")
    assert code == 0, (out, err)
    return str(_id(out, "Go"))


def _did(fw) -> dict:
    """The session log's record of the last do."""
    import json

    rows = [json.loads(line) for line in (fw.session / "session.jsonl").read_text().splitlines() if line.strip()]
    return [row for row in rows if row.get("kind") == "do"][-1]


def test_a_click_that_stopped_after_its_press_is_said_by_the_command(world, fw, filmed, monkeypatch):
    """FP38: the bridge's sentence and mark for a click whose press went and whose click event did not
    reach the person, and the receipt does not call the outcome known."""
    from tests.test_filmed_page_pointer import STOPPED

    text = STOPPED.format(why="the ref's node left the filmed point", last="mousedown", count=8)
    go = _filmed_page(monkeypatch, fw, [], action={"effect": "unverifiable", "summary": text}, action_text=text)
    code, out, err = fw("do", "click", go, "--no-judge")
    said = ("driver says unverifiable (click_stopped_after_press: the click stopped after mousedown and no click "
            "event was sent: the ref's node left the filmed point. The press was sent;")
    assert said in out, (code, out, err)
    assert "input outcome unknown after error: click_stopped_after_press" in out and "not sent" not in out
    assert _did(fw)["error"].startswith("click_stopped_after_press: the click stopped after mousedown")


def test_a_click_refused_after_its_own_hover_events_is_said_by_the_command(world, fw, filmed, monkeypatch):
    from tests.test_filmed_page_pointer import UNPRESSED

    text = UNPRESSED.format(why="the ref's node left the filmed point", last="mousemove")
    go = _filmed_page(monkeypatch, fw, [], action={"effect": "refused", "summary": text}, action_text=text)
    code, out, err = fw("do", "click", go, "--no-judge")
    assert "driver says unverifiable (input outcome unknown: browser_action_unavailable the pointer moved; " in out
    assert "the click was then refused: no press or click was sent" in out, (code, out, err)


def test_a_scene_found_changed_when_the_click_returned_is_said_by_the_command(world, fw, filmed, monkeypatch):
    """FP38: the click went and the page's change decides its receipt; that the film may not show the
    pointer on it is said on a line of its own and kept in the log."""
    from jevdual import ax

    log: list = []
    go = _filmed_page(monkeypatch, fw, log)
    monkeypatch.setattr(ax, "web_area_at", lambda x, y: (
        (501, False) if any(entry[0] == "browser_click" for entry in log) else (40335, True)))
    code, out, err = fw("do", "click", go, "--no-judge")
    assert code == 0, (out, err)
    note = "scene_changed_during_delivery: the click was delivered, but when it returned the pointer at "
    assert f"filmed take: {note}" in out and "input outcome unknown" not in out, out
    assert _did(fw)["filmed_note"].startswith(note) and _did(fw)["error"] is None


def test_a_filmed_click_with_nothing_to_say_prints_no_note(world, fw, filmed, monkeypatch):
    go = _filmed_page(monkeypatch, fw, [])
    code, out, err = fw("do", "click", go, "--no-judge")
    assert code == 0 and "filmed take:" not in out and "filmed_note" not in _did(fw), (out, err)
    assert _did(fw)["error"] is None


def test_a_filmed_browser_take_needs_a_web_area(world, fw, filmed, monkeypatch):
    """FP9: a page position maps to the screen from the web area's origin, so a browser take whose window
    shows no web area does not start (a native take still films from the window's frame)."""
    from jevdual import ax, browser_driver, browser_target
    from jevdual.browser_driver import BrowserBridge
    from jevdual.coordination import Coordinator

    from tests.test_filmed_page_pointer import URL, Wire

    monkeypatch.setattr(browser_target, "_catalog", lambda pid: (
        {"pid": pid, "incarnation": 1.0}, [{"type": "page", "id": "page-1", "url": URL}]))

    async def browser(url, policy):
        wire = Wire([])
        return wire, BrowserBridge(wire, 77, 40335, policy=policy)

    monkeypatch.setattr(browser_driver, "bind_footwork_chrome", browser)
    monkeypatch.setattr(ax, "web_area_frame", lambda el: None)
    code, _, err = fw("start", "Film the page", "--browser", "--mode", "exclusive_desktop",
                      "--pointer-motion", "filmed", "--rest", "20,40")
    assert code == 2 and "no web area" in err, err
    assert [r for r in Coordinator().status()["reservations"] if r["state"] == "active"] == []
    assert not (fw.session / "session.json").exists()
