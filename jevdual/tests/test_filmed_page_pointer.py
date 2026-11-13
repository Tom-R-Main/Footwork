"""A filmed browser take puts the real pointer on each page target before the page action (FP4, FP9).

The bridge and Filmed's viewport mapping are real; the driver is a fake wire that answers the locate
mode of get_browser_state from a queue, the scene reader answers from a queue, and the pointer move and
the pointer's position afterwards are recorded instead of posted and read.
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest
from jevdual import browser_driver
from jevdual.browser_driver import BrowserBridge
from jevdual.filmed import Filmed, FilmedRefusal
from jevdual.posture import ExecutionPolicy

URL = "https://example.invalid/film"
WINDOW = (420.0, 300.0, 300.0, 480.0)
CONTENT = (420.0, 330.0, 300.0, 450.0)
BOUND = {"status": "ok", "target_id": "target-1", "tabs": [{"tab_id": "tab-1", "active": True, "url": URL}]}
SNAPSHOT = {
    "status": "ok",
    "page": {"url": URL, "title": "Film"},
    "snapshot": {"id": "snap-1", "complete": True},
    "refs": [
        {"ref": "snap-1:1", "role": "button", "name": "Go", "actions": ["click"], "frame": "main",
         "visibility": "in_viewport"},
        {"ref": "snap-1:2", "role": "textbox", "name": "Name", "actions": ["type"], "frame": "main",
         "visibility": "in_viewport"},
    ],
}
GO = (40.0, 100.0, 80.0, 30.0)
GO_CENTRE = (80.0, 115.0)
GO_SCREEN = (500.0, 445.0)  # GO_CENTRE from the content origin (420, 330)
NAME = (10.0, 200.0, 200.0, 24.0)
NAME_CENTRE = (110.0, 212.0)
NAME_SCREEN = (530.0, 542.0)
# what a filmed click on Go does, in order, when nothing refuses: the second locate is asked about the
# pointer's own position, and the second scene read and the pointer check are about that position too
GO_STEPS = [("scene", URL), ("locate", "snap-1:1"), ("approach", (460.0, 430.0, 80.0, 30.0), "Go"),
            ("locate", "snap-1:1", GO_CENTRE), ("scene", URL, GO_SCREEN), ("held", GO_SCREEN),
            ("browser_click", "snap-1:1")]


def at(box=GO, **changes):
    """A locate block for a target the pointer can reach at ``box``, with ``changes`` applied."""
    x, y, w, h = box
    block = {
        "available": True,
        "rect": {"x": x, "y": y, "width": w, "height": h},
        "center": {"x": x + w / 2, "y": y + h / 2},
        "hit": "target",
        "box_center": {"x": x + w / 2, "y": y + h / 2},
        "viewport": {"width": 300.0, "height": 450.0, "zoom": 1.0, "scale": 1.0},
        "visibility_state": "visible",
        "clipped": False,
    }
    block.update(changes)
    return block


def under(point=GO_CENTRE, hit="target"):
    return {"x": point[0], "y": point[1], "hit": hit}


REFUSED = {"status": "refused", "refusal": {"code": "browser_ref_stale", "message": "the ref's node is gone"}}


class Wire:
    """``locates`` is consumed one reply per locate call: a locate block, a whole refusal reply, or an
    exception to raise. A locate asked about a point is answered that the target is there, unless the
    block says otherwise."""

    def __init__(self, log: list, locates: list | None = None, action: dict | None = None) -> None:
        self.log = log
        self.locates = list(locates or [])
        self.action = action  # the driver's whole reply to the click or the type, when not a success

    async def call_tool(self, name, args_json):
        args = json.loads(args_json)
        if name == "get_browser_state" and "locate_ref" in args:
            point = args.get("locate_point")
            self.log.append(("locate", args["locate_ref"], *(((point["x"], point["y"]),) if point else ())))
            block = self.locates.pop(0) if self.locates else at()
            if isinstance(block, Exception):
                raise block
            if "status" not in block and point and "point" not in block:
                block = {**block, "point": {**point, "hit": "target"}}
            reply = block if "status" in block else {"status": "ok", "mode": "locate", "locate": block}
        elif name == "get_browser_state":
            reply = SNAPSHOT if "tab_id" in args else BOUND
        else:
            if name != "browser_prepare":
                self.log.append((name, args.get("ref") or args.get("url")))
            reply = {"status": "ok", "target_id": args.get("target_id"), "tab_id": args.get("tab_id")}
            if self.action is not None and name in ("browser_click", "browser_type"):
                reply = self.action
        return SimpleNamespace(structured_json=json.dumps(reply), text="done", is_error=False)

    async def shutdown(self):
        pass


class Take(list):
    """The log of one filmed act, and what its stand-ins answer."""

    scenes: list  # one answer per scene read: None (the scene holds), a reason, or an exception
    posted = 12  # pointer events the approach posts; 0 when the pointer was already on the target
    lands = None  # where the pointer is read after the approach (screen points); default: the centre
    left = False  # the pointer is found away from where it was read


@pytest.fixture
def take(monkeypatch):
    log = Take()
    log.scenes = []

    async def approach(self, frame, label):
        self.check()
        log.append(("approach", frame, label))
        record = {"kind": "approach", "label": label, "samples": 12, "posted": log.posted}
        self.gestures.append(record)
        self.last_pointer = (frame[0] + frame[2] / 2, frame[1] + frame[3] / 2)
        return record

    async def pointer(self):
        return log.lands or self.last_pointer

    async def held(self, at=None):
        log.append(("held", at))
        if log.left:
            self.end_take("pointer_moved_idle")
            raise FilmedRefusal("pointer_moved_idle", "someone moved it; the take ended")

    monkeypatch.setattr(Filmed, "approach", approach)
    monkeypatch.setattr(Filmed, "pointer", pointer)
    monkeypatch.setattr(Filmed, "held", held)
    return log


def _act(log, operation, label, text=None, *, locates=None, filmed=True, take_ended=None, scene=True,
         action=None):
    def read_scene(filmed, url, point=None):
        assert isinstance(filmed, Filmed)
        log.append(("scene", url, *((point,) if point else ())))
        answer = log.scenes.pop(0) if log.scenes else None
        if isinstance(answer, Exception):
            raise answer
        return answer

    async def run():
        bridge = BrowserBridge(Wire(log, locates, action), 42, 7, policy=ExecutionPolicy("exclusive_desktop"))
        if filmed:
            bridge.filmed = Filmed(window=WINDOW, content=CONTENT, take_ended=take_ended)
            if scene:
                bridge.scene = read_scene
        await bridge.attach()
        nm = await bridge.observe()
        target = next(c.id for c in nm.menu.candidates if c.label == label)
        return await bridge.act(nm, operation, target, text)

    return asyncio.run(run())


def _kinds(log):
    return [entry[0] for entry in log]


def test_a_filmed_click_checks_locates_travels_and_checks_again_before_the_page_click(take):
    eff = _act(take, "click", "Go")
    assert eff.dispatched is not False
    # viewport (40, 100) plus the content origin (420, 330); width and height carry over; the second
    # locate is asked about the point the pointer was sent to
    assert take == GO_STEPS


def test_a_filmed_type_travels_to_the_field_before_typing(take):
    _act(take, "type", "Name", "Ada", locates=[at(NAME), at(NAME)])
    assert take == [("scene", URL), ("locate", "snap-1:2"), ("approach", (430.0, 530.0, 200.0, 24.0), "Name"),
                    ("locate", "snap-1:2", NAME_CENTRE), ("scene", URL, NAME_SCREEN), ("held", NAME_SCREEN),
                    ("browser_type", "snap-1:2")]


def test_a_target_the_pointer_cannot_reach_is_refused_before_anything_moves(take):
    eff = _act(take, "click", "Go", locates=[at(hit="other")])
    assert (eff.effect, eff.dispatched, eff.error_code) == ("refused", False, "target_unlocated")
    assert "another element is at its centre" in eff.summary and "pointer moved" not in eff.summary
    assert eff.evidence == ()
    assert take == GO_STEPS[:2]


@pytest.mark.parametrize(("moved_by", "says"), [(1.0, "moved 1.0 px"), (40.0, "outside it")])
def test_a_target_that_moved_during_the_approach_is_refused_and_says_the_pointer_moved(take, moved_by, says):
    moved = (GO[0], GO[1] + moved_by, GO[2], GO[3])
    eff = _act(take, "click", "Go", locates=[at(), at(moved)])
    assert (eff.effect, eff.dispatched, eff.error_code) == ("refused", False, "target_moved")
    assert eff.summary.startswith("the pointer moved but the click was not sent: ")
    assert says in eff.summary and eff.evidence == ("pointer_moved",)
    assert take == GO_STEPS[:4]


def test_a_target_that_stayed_within_half_a_pixel_is_clicked(take):
    nudged = (GO[0] + 0.3, GO[1] + 0.3, GO[2], GO[3])
    _act(take, "click", "Go", locates=[at(), at(nudged)])
    assert take == GO_STEPS


@pytest.mark.parametrize("second", [
    REFUSED,
    at(hit="other"),
    {"available": False, "reason": "unreadable"},
    at(point=under(hit="other")),
    at(point=under(hit="none")),
    at(point=None),
    at(point=under((81.0, 115.0))),
    at(clipped=True),
    at(visibility_state="hidden"),
    RuntimeError("the wire went away"),
])
def test_a_target_not_confirmed_under_the_pointer_after_the_approach_is_refused(take, second):
    eff = _act(take, "click", "Go", locates=[at(), second])
    assert (eff.dispatched, eff.error_code) == (False, "target_moved")
    assert eff.summary.startswith("the pointer moved but the click was not sent: ")
    assert eff.evidence == ("pointer_moved",)
    assert take == GO_STEPS[:4]


def test_the_page_is_asked_about_where_the_pointer_is_not_where_it_was_sent(take):
    """Sol round 3: a pointer that starts within a point of the centre is not moved, and may sit beside a
    narrow target; the hit test must be of its own position."""
    narrow = (79.5, 100.0, 1.0, 30.0)  # 1 px wide, centre (80, 115)
    take.posted, take.lands = 0, (GO_SCREEN[0] + 0.75, GO_SCREEN[1])
    eff = _act(take, "click", "Go", locates=[at(narrow), at(narrow)])
    assert (eff.dispatched, eff.error_code, eff.evidence) == (False, "target_moved", ())
    assert "the pointer landed at 80.8,115.0, outside it" in eff.summary
    assert take[3] == ("locate", "snap-1:1", (80.75, 115.0)) and _kinds(take)[-1] == "locate"


def test_a_pointer_read_off_centre_but_on_the_target_is_checked_there(take):
    take.lands = (GO_SCREEN[0] + 20.0, GO_SCREEN[1] - 5.0)
    eff = _act(take, "click", "Go")
    assert eff.dispatched is not False
    assert take[3:6] == [("locate", "snap-1:1", (100.0, 110.0)), ("scene", URL, take.lands), ("held", take.lands)]


@pytest.mark.parametrize(("operation", "label", "text"), [("click", "Go", None), ("type", "Name", "Ada")])
@pytest.mark.parametrize("posted", [12, 0])
def test_a_page_action_refused_after_the_approach_says_whether_the_pointer_moved(take, operation, label, text, posted):
    """Sol round 3: the driver or the holder can refuse the action itself after the pointer has
    arrived; that refusal must not read as if nothing had happened."""
    take.posted = posted
    box = GO if label == "Go" else NAME
    eff = _act(take, operation, label, text, locates=[at(box), at(box)], action=REFUSED)
    assert (eff.effect, eff.error_code) == ("refused", "browser_ref_stale")
    assert "the ref's node is gone" in eff.summary
    assert eff.summary.startswith(f"the pointer moved; the {operation} was then refused: ") is bool(posted)
    assert ("pointer_moved" in eff.evidence) is bool(posted)
    assert _kinds(take)[-1] in ("browser_click", "browser_type")


def test_a_refusal_after_an_approach_that_posted_nothing_does_not_say_the_pointer_moved(take):
    take.posted = 0  # the pointer was already on the target
    eff = _act(take, "click", "Go", locates=[at(), at(hit="other")])
    assert (eff.dispatched, eff.error_code, eff.evidence) == (False, "target_moved", ())
    assert "pointer moved" not in eff.summary


@pytest.mark.parametrize("first", [REFUSED, RuntimeError("the wire went away")])
def test_a_first_locate_that_is_refused_or_fails_withholds_the_action(take, first):
    eff = _act(take, "click", "Go", locates=[first])
    assert (eff.effect, eff.dispatched, eff.error_code, eff.evidence) == ("refused", False, "target_unlocated", ())
    assert ("the ref's node is gone" in eff.summary) or ("the locate call failed (RuntimeError" in eff.summary)
    assert take == GO_STEPS[:2]


@pytest.mark.parametrize("answer", ["the browser is not the frontmost application", OSError("no window server")])
def test_a_changed_scene_is_refused_before_the_page_is_asked_anything(take, answer):
    take.scenes = [answer]
    eff = _act(take, "click", "Go")
    assert (eff.effect, eff.dispatched, eff.error_code, eff.evidence) == ("refused", False, "scene_changed", ())
    assert ("not the frontmost" in eff.summary) or ("could not be read (OSError" in eff.summary)
    assert take == GO_STEPS[:1]


def test_a_scene_that_changed_during_the_approach_is_refused_and_says_the_pointer_moved(take):
    take.scenes = [None, "the pointer at 500.0,445.0 is not over the page of the scene window (another window is there)"]
    eff = _act(take, "click", "Go")
    assert (eff.dispatched, eff.error_code, eff.evidence) == (False, "scene_changed", ("pointer_moved",))
    assert eff.summary.startswith("the pointer moved but the click was not sent: the pointer at 500.0,445.0 is not")
    assert take == GO_STEPS[:5]


def test_a_filmed_bridge_with_no_scene_reader_refuses(take):
    eff = _act(take, "click", "Go", scene=False)
    assert (eff.effect, eff.dispatched, eff.error_code) == ("refused", False, "scene_changed")
    assert take == []


def test_a_pointer_that_left_its_landing_point_ends_the_take_and_withholds_the_action(take):
    take.left = True
    eff = _act(take, "click", "Go")
    assert (eff.dispatched, eff.error_code, eff.evidence) == (False, "pointer_moved_idle", ("pointer_moved",))
    assert take == GO_STEPS[:6]


def test_an_ended_take_refuses_without_asking_the_page_anything(take):
    eff = _act(take, "click", "Go", take_ended="pointer_moved_idle")
    assert (eff.effect, eff.dispatched, eff.error_code) == ("refused", False, "take_ended")
    assert take == []


def test_an_ended_take_refuses_a_navigation_too(take):
    async def run():
        bridge = BrowserBridge(Wire(take), 42, 7, policy=ExecutionPolicy("exclusive_desktop"))
        bridge.filmed = Filmed(window=WINDOW, content=CONTENT, take_ended="pointer_moved_idle")
        await bridge.attach()
        return await bridge.navigate(URL + "/next")

    eff = asyncio.run(run())
    assert (eff.effect, eff.dispatched, eff.error_code) == ("refused", False, "take_ended")
    assert take == []


def test_an_unfilmed_session_clicks_without_locating_or_moving_the_pointer(take):
    _act(take, "click", "Go", filmed=False)
    assert take == [("browser_click", "snap-1:1")]


def test_a_reachable_target_gives_its_rectangle():
    assert browser_driver.located_rect(at()) == (GO, "")
    assert browser_driver.located_rect(at(hit="descendant")) == (GO, "")
    assert browser_driver.located_rect(at(point=under()), GO_CENTRE) == (GO, "")
    assert browser_driver.located_rect(at(point=under(hit="descendant")), GO_CENTRE) == (GO, "")
    # a point is only looked at when one was asked about
    assert browser_driver.located_rect(at(point=under(hit="other"))) == (GO, "")


@pytest.mark.parametrize(("locate", "why"), [
    (None, "no position"),
    ({"available": False, "reason": "child_frame"}, "child_frame"),
    (at(viewport={"width": 300.0, "height": 450.0, "zoom": 1.25, "scale": 1.0}), "zoom 1.25"),
    (at(viewport={"width": 300.0, "height": 450.0, "zoom": 1.0, "scale": 2.0}), "pinch scale 2"),
    (at(viewport={"width": 300.0, "height": 450.0, "zoom": None, "scale": None}), "did not report"),
    (at(viewport=None), "did not report"),
    (at((40.0, 440.0, 80.0, 30.0)), "not wholly in view"),
    (at((-10.0, 100.0, 80.0, 30.0)), "not wholly in view"),
    (at(hit="other"), "another element"),
    (at(hit="none"), "nothing is at its centre"),
    (at(box_center=None), "without page script"),
    (at(box_center={"x": 85.0, "y": 115.0}), "without page script"),
    (at(rect={"x": 40.0, "y": 100.0, "width": 0.0, "height": 30.0}), "no usable rectangle"),
    (at(rect={"x": "a", "y": 100.0, "width": 80.0, "height": 30.0}), "no usable rectangle"),
    (at(rect={"x": float("nan"), "y": 100.0, "width": 80.0, "height": 30.0}), "no usable rectangle"),
    (at(rect={"x": True, "y": 100.0, "width": 80.0, "height": 30.0}), "no usable rectangle"),
    (at(visibility_state="hidden"), "not showing"),
    (at(visibility_state="prerender"), "not showing"),
    (at(visibility_state=None), "whether the page is showing"),
    (at(clipped=True), "container hides part of it"),
    (at(clipped=None), "whether a container clips it"),
    (at(clipped="no"), "whether a container clips it"),
])
def test_a_target_a_pointer_cannot_be_put_on_gives_no_rectangle_and_says_why(locate, why):
    rect, reason = browser_driver.located_rect(locate)
    assert rect is None and why in reason, reason


@pytest.mark.parametrize(("locate", "why"), [
    (at(), "what is where the pointer landed"),
    (at(point=None), "what is where the pointer landed"),
    (at(point={"x": 80.0, "y": "a", "hit": "target"}), "what is where the pointer landed"),
    (at(point=under((80.5, 115.0))), "what is where the pointer landed"),
    (at(point=under(hit="other")), "another element is under the pointer"),
    (at(point=under(hit="none")), "nothing of the page is under the pointer"),
    (at(point=under(hit=None)), "nothing of the page is under the pointer"),
    (at((40.0, 120.0, 80.0, 30.0), point=under()), "outside it"),
    (at((90.0, 100.0, 80.0, 30.0), point=under()), "outside it"),
])
def test_a_landing_point_that_is_not_on_the_target_gives_no_rectangle_and_says_why(locate, why):
    rect, reason = browser_driver.located_rect(locate, GO_CENTRE)
    assert rect is None and why in reason, reason


def test_the_locate_operation_is_a_read_of_one_ref_and_optionally_one_point():
    from jevdual.browser_session_holder import OPERATIONS, SENDING
    from jevdual.effectors.cua import CuaBrowserOperations

    calls: list = []

    class Driver:
        async def call_tool(self, name, args_json):
            calls.append((name, json.loads(args_json)))
            return SimpleNamespace(structured_json=json.dumps({"status": "ok", "locate": at()}), text="", is_error=False)

    operations = CuaBrowserOperations(Driver(), session="s")
    reply = asyncio.run(operations.locate(target_id="t", tab_id="b", ref="r"))
    asyncio.run(operations.locate(target_id="t", tab_id="b", ref="r", point=[80, 115.5]))
    base = {"session": "s", "target_id": "t", "tab_id": "b", "locate_ref": "r"}
    assert calls == [("get_browser_state", base),
                     ("get_browser_state", {**base, "locate_point": {"x": 80.0, "y": 115.5}})]
    assert reply.payload["locate"]["hit"] == "target"
    assert OPERATIONS["locate"] == {"target_id", "tab_id", "ref", "point"} and "locate" not in SENDING
    assert (browser_driver.LOCATE_TOLERANCE_PX, browser_driver.DRIFT_TOLERANCE_PX) == (2.0, 0.5)


def test_the_held_route_carries_the_point_to_the_holder():
    from jevdual.browser_session_holder import OPERATIONS, RemoteBrowserOperations
    from jevdual.effectors.base import BrowserRefusal, BrowserReply

    sent: list = []

    answers = [BrowserReply(status="ok", text="", is_error=False), BrowserReply(status="ok", text="", is_error=False), BrowserReply(
        status="refused", text="holder_request_invalid", is_error=True, dispatched=False,
        refusal=BrowserRefusal(code="holder_request_invalid", message="holder_request_invalid"))]

    async def op(self, method, **args):
        sent.append((method, args))
        return answers.pop(0)

    operations = RemoteBrowserOperations.__new__(RemoteBrowserOperations)
    operations._op = op.__get__(operations)
    asyncio.run(operations.locate(target_id="t", tab_id="b", ref="r"))
    asyncio.run(operations.locate(target_id="t", tab_id="b", ref="r", point=(80, 115.5)))
    assert sent == [("locate", {"target_id": "t", "tab_id": "b", "ref": "r", "point": None}),
                    ("locate", {"target_id": "t", "tab_id": "b", "ref": "r", "point": [80.0, 115.5]})]
    assert all(set(args) == OPERATIONS["locate"] for _, args in sent)
    # a holder started by an older build rejects the request's fields: say so, and that nothing was sent
    old = asyncio.run(operations.locate(target_id="t", tab_id="b", ref="r"))
    assert old.refused and old.dispatched is False and old.refusal.code == "holder_request_invalid"
    assert "an older build started it" in old.refusal.message and "start a new session" in old.text


# ---- the scene reader


def _scene(monkeypatch, *, front=42, main=True, window=WINDOW, area=(CONTENT, URL), error=False, url=URL,
           point=None, over=(7, True)):
    from jevdual import ax, posture
    from jevdual.filmed import browser_scene_change

    def element(pid, window_id):
        assert (pid, window_id) == (42, 7)
        if error:
            raise ax.AXError("window_missing", "pid 42 has no AX window 7")
        return "window"

    monkeypatch.setattr(posture, "frontmost_pid", lambda: front)
    monkeypatch.setattr(ax, "window_element", element)
    monkeypatch.setattr(ax, "frame_of", lambda el: ax.Frame(*window) if window else None)
    monkeypatch.setattr(ax, "is_main", lambda el: main)
    monkeypatch.setattr(ax, "web_area", lambda el: None if area is None else (
        ax.Frame(*area[0]) if area[0] else None, area[1]))

    def at_point(x, y):
        assert (x, y) == point
        return over

    monkeypatch.setattr(ax, "web_area_at", at_point)
    return browser_scene_change(42, 7, Filmed(window=WINDOW, content=CONTENT), url, point)


def test_the_recorded_scene_holds_while_nothing_changed(monkeypatch):
    assert _scene(monkeypatch) is None
    # a fragment is not another page; float noise is not another place
    assert _scene(monkeypatch, area=(CONTENT, URL + "#step-2")) is None
    assert _scene(monkeypatch, url=URL + "#top") is None
    assert _scene(monkeypatch, window=(420.004, 300.0, 300.0, 480.0), area=((420.004, 330.0, 300.0, 450.0), URL)) is None
    # with the pointer's position: the page of this window is what a native hit test finds there
    assert _scene(monkeypatch, point=GO_SCREEN) is None


@pytest.mark.parametrize(("changed", "why"), [
    ({"front": 99}, "not the frontmost application (pid 99 is)"),
    ({"front": None}, "not the frontmost application"),
    ({"error": True}, "could not be read (pid 42 has no AX window 7)"),
    ({"main": False}, "not the browser's main window"),
    ({"main": None}, "not the browser's main window"),
    ({"window": (500.0, 300.0, 300.0, 480.0)}, "the scene window is 300x480 at 500.0,300.0"),
    # Sol round 4: the page is mapped to the screen from the recorded origin, so 0.4 pt is another place
    ({"window": (420.4, 300.0, 300.0, 480.0), "area": ((420.4, 330.0, 300.0, 450.0), URL)},
     "the scene window is 300x480 at 420.4,300.0"),
    ({"area": ((420.4, 330.0, 300.0, 450.0), URL)}, "the page area is 300x450 at 420.4,330.0"),
    ({"window": (420.0, 300.0, 300.0, 520.0)}, "the scene window is 300x520"),
    ({"window": None}, "without a frame"),
    ({"area": None}, "shows no web area"),
    ({"area": (None, URL)}, "shows no web area"),
    ({"area": ((420.0, 370.0, 300.0, 410.0), URL)}, "the page area is 300x410 at 420.0,370.0"),
    ({"area": (CONTENT, "https://example.invalid/other")}, "not the session's page"),
    ({"area": (CONTENT, None)}, "'no address'"),
    ({"url": None}, "not the session's page"),
    ({"point": GO_SCREEN, "over": (7, False)}, "is not over the page of the scene window (something that is not the page"),
    ({"point": GO_SCREEN, "over": (99, True)}, "is not over the page of the scene window (another window is there)"),
    ({"point": GO_SCREEN, "over": (99, False)}, "another window is there"),
    ({"point": GO_SCREEN, "over": (None, False)}, "something that is not the page"),
    ({"point": GO_SCREEN, "over": (None, True)}, "something that is not the page"),
])
def test_a_changed_scene_is_named(monkeypatch, changed, why):
    reason = _scene(monkeypatch, **changed)
    assert reason and why in reason, reason


def test_the_web_area_is_read_with_its_address(monkeypatch):
    from jevdual import ax

    tree = {
        "window": {"AXRole": "AXWindow", "AXChildren": ["toolbar", "group"]},
        "toolbar": {"AXRole": "AXToolbar"},
        "group": {"AXRole": "AXGroup", "AXChildren": ["web"]},
        "web": {"AXRole": "AXWebArea", "AXURL": URL},
    }
    monkeypatch.setattr(ax, "_attr", lambda el, name: tree[el].get(name))
    monkeypatch.setattr(ax, "frame_of", lambda el: ax.Frame(*CONTENT) if el == "web" else None)
    assert ax.web_area("window") == (ax.Frame(*CONTENT), URL)
    assert ax.web_area_frame("window") == ax.Frame(*CONTENT)
    tree["web"]["AXURL"] = SimpleNamespace(absoluteString=lambda: "file:///tmp/page.html")
    assert ax.web_area("window") == (ax.Frame(*CONTENT), "file:///tmp/page.html")
    tree["web"]["AXURL"] = None
    assert ax.web_area("window") == (ax.Frame(*CONTENT), None)
    tree["group"]["AXChildren"] = []
    assert ax.web_area("window") is None and ax.web_area_frame("window") is None
    tree["window"]["AXMain"] = True
    assert ax.is_main("window") is True and ax.is_main("toolbar") is None


def test_the_pointer_check_refuses_and_ends_the_take_when_the_pointer_was_moved(monkeypatch):
    from jevdual import drag

    where = {"pointer": (500.0, 445.0)}
    monkeypatch.setattr(drag, "QuartzPoster", lambda: SimpleNamespace(location=lambda: where["pointer"]))
    filmed = Filmed(window=WINDOW, content=CONTENT, last_pointer=(500.0, 445.0))
    assert asyncio.run(filmed.pointer()) == (500.0, 445.0)
    asyncio.run(filmed.held())
    where["pointer"] = (501.5, 445.0)  # within the take's continuity tolerance of 2 points
    asyncio.run(filmed.held())
    assert asyncio.run(filmed.pointer()) == (501.5, 445.0)
    asyncio.run(filmed.held((501.5, 445.0)))  # exactly where it was read
    assert filmed.take_ended is None
    # continuity is not proof the pointer is still on the target (Sol round 4): 0.3 pt from the position
    # the page was asked about is a position nothing verified, and ends the take
    moved = Filmed(window=WINDOW, content=CONTENT, last_pointer=(500.0, 445.0))
    with pytest.raises(FilmedRefusal) as away:
        asyncio.run(moved.held((501.2, 445.0)))
    assert away.value.code == "pointer_moved_idle" and moved.take_ended == "pointer_moved_idle"
    where["pointer"] = (530.0, 445.0)
    with pytest.raises(FilmedRefusal) as refused:
        asyncio.run(filmed.held())
    assert refused.value.code == "pointer_moved_idle" and filmed.take_ended == "pointer_moved_idle"
    with pytest.raises(FilmedRefusal) as again:
        asyncio.run(filmed.held())
    assert again.value.code == "take_ended"
