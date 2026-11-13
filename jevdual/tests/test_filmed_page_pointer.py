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
        {"ref": "snap-1:3", "role": "textbox", "name": "City", "value": "Paris", "actions": ["type"],
         "frame": "main", "visibility": "in_viewport"},
    ],
}
GO = (40.0, 100.0, 80.0, 30.0)
GO_CENTRE = (80.0, 115.0)
GO_SCREEN = (500.0, 445.0)  # GO_CENTRE from the content origin (420, 330)
NAME = (10.0, 200.0, 200.0, 24.0)
NAME_CENTRE = (110.0, 212.0)
NAME_SCREEN = (530.0, 542.0)
# what a filmed click on Go does, in order, when nothing refuses: the second locate is asked about the
# pointer's own position, the second scene read and the pointer check are about that position too, the
# click carries it to the driver (FP26), and when the click returns the pointer is checked once more
# and the window's and the page area's frames and what is under the pointer are read again (FP35)
GO_STEPS = [("scene", URL), ("locate", "snap-1:1"), ("approach", (460.0, 430.0, 80.0, 30.0), "Go"),
            ("locate", "snap-1:1", GO_CENTRE), ("scene", URL, GO_SCREEN), ("held", GO_SCREEN),
            ("browser_click", "snap-1:1"), ("held", GO_SCREEN), ("after", GO_SCREEN)]
SENT = 7  # how many of a filmed act's steps end with the page action


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
        "world": "isolated",
        "filmed_delivery": True,
        "cursor": "pointer",
        "focused": False,
        "page_focused": True,
    }
    block.update(changes)
    return block


def focused(box=NAME, **changes):
    """A locate block for a field that has focus, the only kind a filmed take types into."""
    return at(box, focused=True, **changes)


def under(point=GO_CENTRE, hit="target", cursor="pointer"):
    return {"x": point[0], "y": point[1], "hit": hit, "cursor": cursor}


REFUSED = {"status": "refused", "refusal": {"code": "browser_ref_stale", "message": "the ref's node is gone"}}


class Wire:
    """``locates`` is consumed one reply per locate call: a locate block, a whole refusal reply, or an
    exception to raise. A locate asked about a point is answered that the target is there, unless the
    block says otherwise."""

    def __init__(self, log: list, locates: list | None = None, action: dict | None = None,
                 action_text: str | None = None, action_error: bool = False) -> None:
        self.log = log
        self.locates = list(locates or [])
        self.action = action  # the driver's whole reply to the click or the type, when not a success
        self.action_text = action_text  # and its text
        self.action_error = action_error  # and whether the driver flagged it an error

    async def call_tool(self, name, args_json):
        args = json.loads(args_json)
        if name == "get_browser_state" and "locate_ref" in args:
            point = args.get("locate_point")
            self.log.append(("locate", args["locate_ref"], *(((point["x"], point["y"]),) if point else ())))
            block = self.locates.pop(0) if self.locates else at()
            if isinstance(block, Exception):
                raise block
            if "status" not in block and point and "point" not in block:
                block = {**block, "point": {**point, "hit": "target", "cursor": "pointer"}}
            reply = block if "status" in block else {"status": "ok", "mode": "locate", "locate": block}
        elif name == "get_browser_state":
            reply = SNAPSHOT if "tab_id" in args else BOUND
        else:
            if name != "browser_prepare":
                self.log.append((name, args.get("ref") or args.get("url")))
            if name == "browser_click" and hasattr(self.log, "routes"):
                self.log.routes.append(args.get("input_route"))
            if name in ("browser_click", "browser_type") and hasattr(self.log, "sent"):
                self.log.sent.append(args)
            reply = {"status": "ok", "target_id": args.get("target_id"), "tab_id": args.get("tab_id")}
            if self.action is not None and name in ("browser_click", "browser_type"):
                reply = self.action
        text = self.action_text if self.action_text and name in ("browser_click", "browser_type") else "done"
        failed = self.action_error and name in ("browser_click", "browser_type")
        return SimpleNamespace(structured_json=json.dumps(reply), text=text, is_error=failed)

    async def shutdown(self):
        pass


class Take(list):
    """The log of one filmed act, and what its stand-ins answer."""

    scenes: list  # one answer per scene read: None (the scene holds), a reason, or an exception
    frames = None  # the answer to the reading after a delivery: None, a reason, or an exception
    posted = 12  # pointer events the approach posts; 0 when the pointer was already on the target
    lands = None  # where the pointer is read after the approach (screen points); default: the centre
    left = False  # the pointer is found away from where it was read: True (at the first check) or the
    #               number of the check that finds it so (2 is the one after the delivery)
    routes: list  # the input route of each click that reached the driver
    sent: list  # the arguments of each click and type that reached the driver


@pytest.fixture
def take(monkeypatch):
    log = Take()
    log.scenes, log.routes, log.sent = [], [], []

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
        if log.left and _kinds(log).count("held") >= int(log.left):
            self.end_take("pointer_moved_idle")
            raise FilmedRefusal("pointer_moved_idle", "someone moved it; the take ended")

    monkeypatch.setattr(Filmed, "approach", approach)
    monkeypatch.setattr(Filmed, "pointer", pointer)
    monkeypatch.setattr(Filmed, "held", held)
    return log


def _act(log, operation, label, text=None, *, locates=None, filmed=True, take_ended=None, scene=True,
         action=None, route=None, session=None, action_text=None, action_error=False):
    def read_scene(filmed, url, point=None, *, delivered=False):
        assert isinstance(filmed, Filmed)
        if delivered:
            log.append(("after", point))
            answer = getattr(log, "frames", None)
        else:
            log.append(("scene", url, *((point,) if point else ())))
            answer = log.scenes.pop(0) if log.scenes else None
        if isinstance(answer, Exception):
            raise answer
        return answer

    async def run():
        bridge = BrowserBridge(Wire(log, locates, action, action_text, action_error), 42, 7,
                               policy=ExecutionPolicy("exclusive_desktop"))
        if filmed:
            bridge.filmed = session or Filmed(window=WINDOW, content=CONTENT, take_ended=take_ended)
            if scene:
                bridge.scene = read_scene
        await bridge.attach()
        nm = await bridge.observe()
        target = next(c.id for c in nm.menu.candidates if c.label == label)
        return await bridge.act(nm, operation, target, text, route=route)

    return asyncio.run(run())


def _kinds(log):
    return [entry[0] for entry in log]


def test_a_filmed_click_checks_locates_travels_and_checks_again_before_the_page_click(take):
    eff = _act(take, "click", "Go")
    assert eff.dispatched is not False
    # viewport (40, 100) plus the content origin (420, 330); width and height carry over; the second
    # locate is asked about the point the pointer was sent to
    assert take == GO_STEPS


NAME_STEPS = [("scene", URL), ("locate", "snap-1:2"), ("approach", (430.0, 530.0, 200.0, 24.0), "Name"),
              ("locate", "snap-1:2", NAME_CENTRE), ("scene", URL, NAME_SCREEN), ("held", NAME_SCREEN),
              ("browser_type", "snap-1:2"), ("held", NAME_SCREEN), ("after", NAME_SCREEN)]


@pytest.mark.parametrize("operation", ["type", "append"])
def test_a_filmed_type_travels_to_the_focused_field_before_typing(take, operation):
    eff = _act(take, operation, "Name", "Ada", locates=[focused(), focused()])
    assert eff.dispatched is not False
    assert take == NAME_STEPS


def test_an_empty_field_that_is_active_in_a_page_without_the_keyboard_is_typed_into(take):
    """FP21: inserting changes no focus when the field is already its document's active element, and a
    document without focus matches no focus style before or after."""
    background = focused(page_focused=False)
    eff = _act(take, "type", "Name", "Ada", locates=[background, background])
    assert eff.dispatched is not False
    assert take == NAME_STEPS


@pytest.mark.parametrize("page_focused", [True, False])
def test_a_filmed_take_does_not_replace_held_text(take, page_focused):
    """Sol round 6: a replacement focuses and selects after the last check, so the pointer's place on
    the field is no longer what was verified. Refused before anything is read or moved."""
    eff = _act(take, "type", "City", "Rome", locates=[focused(page_focused=page_focused)])
    assert (eff.effect, eff.dispatched, eff.error_code, eff.evidence) == ("refused", False, "replace_unfilmed", ())
    assert "types only into an empty field" in eff.summary and "pointer moved" not in eff.summary
    assert take == [] and take.sent == []


def test_an_unfilmed_session_still_replaces_held_text(take):
    _act(take, "type", "City", "Rome", filmed=False)
    assert take == [("browser_type", "snap-1:3")]
    assert take.sent[0]["replace"] is True and "filmed_point" not in take.sent[0]


def test_a_filmed_click_carries_the_pointers_verified_place_to_the_driver(take):
    """FP26: the driver checks that point against the element in the same turn as the click itself."""
    take.lands = (GO_SCREEN[0] + 20.0, GO_SCREEN[1] - 5.0)
    _act(take, "click", "Go")
    assert [(args["input_route"], args["filmed_point"]) for args in take.sent] == [("dom_event", {"x": 100.0, "y": 110.0})]


def test_a_filmed_type_carries_the_pointers_verified_place_and_inserts_without_replacing(take):
    _act(take, "type", "Name", "Ada", locates=[focused(), focused()])
    (args,) = take.sent
    assert (args["filmed_point"], args["mode"], args["replace"], args["text"]) == (
        {"x": NAME_CENTRE[0], "y": NAME_CENTRE[1]}, "insert_text", False, "Ada")


@pytest.mark.parametrize(("operation", "label", "text"), [("click", "Go", None), ("type", "Name", "Ada")])
def test_an_unfilmed_action_carries_no_point(take, operation, label, text):
    _act(take, operation, label, text, filmed=False)
    assert len(take.sent) == 1 and "filmed_point" not in take.sent[0]


@pytest.mark.parametrize(("operation", "label", "text", "steps"), [
    ("click", "Go", None, GO_STEPS), ("type", "Name", "Ada", NAME_STEPS)])
def test_a_pointer_found_elsewhere_when_the_delivery_returns_ends_the_take_and_says_so(
        take, operation, label, text, steps):
    """FP26: nothing on the page can see the pointer leave between the last check and the delivery, so
    it is read again afterwards; the action went, and the effect must not read as filmed proof."""
    take.left = 2
    box = GO if label == "Go" else NAME
    filmed_take = Filmed(window=WINDOW, content=CONTENT)
    eff = _act(take, operation, label, text, locates=[focused(box), focused(box)], session=filmed_take)
    assert eff.effect != "refused" and eff.dispatched is not False
    assert eff.summary.startswith(
        f"the {operation} was delivered, but when it returned the pointer was not where it was verified")
    assert "pointer_moved_idle" in eff.summary and "the take ended" in eff.summary
    assert eff.evidence[-1] == "pointer_left_during_delivery"
    assert take == steps and filmed_take.take_ended == "pointer_moved_idle"


@pytest.mark.parametrize(("operation", "label", "text", "steps"), [
    ("click", "Go", None, GO_STEPS), ("type", "Name", "Ada", NAME_STEPS)])
@pytest.mark.parametrize("answer", ["the page area is 300x450 at 420.0,360.0; the take recorded 300x450 at 420.0,330.0",
                                    ("the pointer at 500.0,445.0 is not over the page of the scene window "
                                     "(another window is there)"),
                                    OSError("no window server")])
def test_a_window_found_elsewhere_when_the_delivery_returns_is_said_and_the_take_goes_on(
        take, operation, label, text, steps, answer):
    """FP26: the driver checks the viewport point Footwork gave it; a window that moved under a still
    pointer makes that point another place on screen, which only the frames can show."""
    take.frames = answer
    box = GO if label == "Go" else NAME
    filmed_take = Filmed(window=WINDOW, content=CONTENT)
    eff = _act(take, operation, label, text, locates=[focused(box), focused(box)], session=filmed_take)
    assert eff.effect != "refused" and eff.dispatched is not False
    assert eff.summary.startswith(f"the {operation} was delivered, but when it returned the ")
    assert (("the take recorded 300x450 at 420.0,330.0" in eff.summary) or ("could not be read (OSError" in eff.summary)
            or ("is not over the page of the scene window" in eff.summary))
    assert eff.evidence[-1] == "scene_changed_during_delivery" and "pointer_left_during_delivery" not in eff.evidence
    assert take == steps and filmed_take.take_ended is None


def test_both_findings_after_a_delivery_are_said(take):
    take.left, take.frames = 2, "the scene window is 300x480 at 400.0,300.0; the take recorded 300x480 at 420.0,300.0"
    eff = _act(take, "click", "Go")
    assert eff.evidence[-2:] == ("pointer_left_during_delivery", "scene_changed_during_delivery")
    assert "the take ended; and the scene window is 300x480 at 400.0,300.0" in eff.summary
    assert take == GO_STEPS


def test_a_page_action_the_driver_refused_is_not_followed_by_a_pointer_check(take):
    eff = _act(take, "click", "Go", action=REFUSED)
    assert eff.effect == "refused" and take == GO_STEPS[:SENT]


@pytest.mark.parametrize("operation", ["type", "append"])
@pytest.mark.parametrize(("first", "says"), [
    (at(NAME), "does not have focus; click it first"),
    (at(NAME, page_focused=False), "does not have focus; click it first"),
    (at(NAME, focused=None), "did not say whether it has focus"),
    ({k: v for k, v in at(NAME).items() if k not in ("focused", "page_focused")}, "did not say whether it has focus"),
])
def test_a_field_without_focus_is_not_typed_into_and_nothing_moves(take, operation, first, says):
    """Sol round 5: the driver focuses a field before it types, and a field can move when it gains
    focus, after the pointer was verified on it. Only a field that already has focus is typed into."""
    eff = _act(take, operation, "Name", "Ada", locates=[first])
    assert (eff.effect, eff.dispatched, eff.error_code, eff.evidence) == ("refused", False, "target_unfocused", ())
    assert says in eff.summary and "pointer moved" not in eff.summary
    assert take == NAME_STEPS[:2]


def test_a_field_that_lost_focus_during_the_approach_is_not_typed_into(take):
    eff = _act(take, "type", "Name", "Ada", locates=[focused(), at(NAME)])
    assert (eff.dispatched, eff.error_code, eff.evidence) == (False, "target_unfocused", ("pointer_moved",))
    assert eff.summary.startswith("the pointer moved but the type was not sent: 'Name' lost focus while the pointer")
    assert take == NAME_STEPS[:4] and take.sent == []


def test_a_click_does_not_need_its_target_focused(take):
    nowhere = {"focused": False, "page_focused": False}
    _act(take, "click", "Go", locates=[at(**nowhere), at(**nowhere)])
    assert take == GO_STEPS and take.routes == ["dom_event"]


def test_a_filmed_click_by_the_trusted_route_is_refused_before_anything_is_read_or_moved(take):
    """Sol round 5: the trusted route presses at the content-box centre, not the verified point."""
    eff = _act(take, "click", "Go", route="trusted")
    assert (eff.effect, eff.dispatched, eff.error_code, eff.evidence) == ("refused", False, "route_unfilmed", ())
    assert "leave out --route trusted" in eff.summary and "pointer moved" not in eff.summary
    assert take == [] and take.routes == []


def test_a_filmed_click_by_the_dom_route_named_outright_goes_as_the_default_does(take):
    _act(take, "click", "Go", route="dom_event")
    assert take == GO_STEPS and take.routes == ["dom_event"]


def test_an_unfilmed_session_still_sends_a_trusted_click(take):
    _act(take, "click", "Go", filmed=False, route="trusted")
    assert take == [("browser_click", "snap-1:1")] and take.routes == ["trusted"]


@pytest.mark.parametrize("marker", [None, False, "true", 1, "absent"])
def test_a_driver_that_does_not_say_it_checks_the_pointer_at_delivery_is_refused_before_anything_moves(take, marker):
    """FP30: an older driver takes the pointer's position with a click and ignores it."""
    block = at(filmed_delivery=marker)
    if marker == "absent":
        del block["filmed_delivery"]
    eff = _act(take, "click", "Go", locates=[block])
    assert (eff.effect, eff.dispatched, eff.error_code, eff.evidence) == ("refused", False, "target_unlocated", ())
    assert "does not say it checks the pointer's position when it delivers" in eff.summary
    assert take == GO_STEPS[:2] and take.sent == []
    del take[:]
    eff = _act(take, "type", "Name", "Ada", locates=[focused(), {**block, "rect": focused()["rect"],
                                                                 "center": focused()["center"],
                                                                 "box_center": focused()["box_center"], "focused": True}])
    assert (eff.dispatched, eff.error_code, eff.evidence) == (False, "target_moved", ("pointer_moved",))
    assert take == NAME_STEPS[:4] and take.sent == []


def test_a_page_that_hides_the_pointer_over_its_target_is_refused_before_anything_moves(take):
    """Sol round 7: with cursor none the pointer's position shows nothing on film."""
    eff = _act(take, "click", "Go", locates=[at(cursor="none")])
    assert (eff.effect, eff.dispatched, eff.error_code, eff.evidence) == ("refused", False, "target_unlocated", ())
    assert "hides or replaces the pointer over it (cursor: none)" in eff.summary and "pointer moved" not in eff.summary
    assert take == GO_STEPS[:2] and take.sent == []
    del take[:]
    # shown over the centre, hidden where the pointer then is (a child with its own cursor)
    eff = _act(take, "click", "Go", locates=[at(), at(point=under(cursor="none"))])
    assert (eff.dispatched, eff.error_code, eff.evidence) == (False, "target_moved", ("pointer_moved",))
    assert "hides or replaces the pointer where it landed" in eff.summary
    assert take == GO_STEPS[:4] and take.sent == []


@pytest.mark.parametrize("cursor", ["auto", "default", "pointer", "text", "grab", "-webkit-grab"])
def test_a_keyword_cursor_shows_the_pointer(cursor):
    assert browser_driver.pointer_shown(cursor)


@pytest.mark.parametrize("cursor", ["none", 'url("x.png") 4 4, auto', "pointer, auto", "", "Pointer", None, 7, True])
def test_no_other_cursor_shows_it(cursor):
    assert not browser_driver.pointer_shown(cursor)


STOPPED = ("sent part of a synthetic DOM click on snap-1:1 in tab-b0e626b5-9e58-4f02-a686-dd195b85efa6: {why} after "
           "{last}, so the rest of the sequence was not sent and no click event was; {count} events were sent and "
           "application effect is unverifiable. Refresh page state and verify the expected postcondition")


@pytest.mark.parametrize(("why", "last"), [
    ("the ref's node left the filmed point", "mousedown"),
    ("the ref's node left the filmed point", "pointerup"),
    ("the page hid or replaced the pointer over the ref's node", "mousedown"),
])
def test_a_click_that_stopped_after_its_press_says_the_press_went_and_no_click_did(take, why, last):
    """Sol round 7: a control that moves when pressed is pressed and not clicked. The driver's own text
    is longer than a summary keeps; the bridge says it in one sentence and marks the effect."""
    text = STOPPED.format(why=why, last=last, count=8)
    eff = _act(take, "click", "Go", action={"effect": "unverifiable", "summary": text}, action_text=text)
    assert eff.effect == "unverifiable" and eff.dispatched is not False
    assert eff.summary.startswith(f"the click stopped after {last} and no click event was sent: {why}. The press was sent")
    assert eff.evidence[-1] == "click_stopped_after_press"
    assert take == GO_STEPS  # the pointer and the scene are still read afterwards


def test_a_stopped_click_outside_a_filmed_take_and_an_ordinary_click_keep_the_drivers_words(take):
    text = STOPPED.format(why="the ref's node left the filmed point", last="mousedown", count=8)
    eff = _act(take, "click", "Go", filmed=False, action={"effect": "unverifiable", "summary": text}, action_text=text)
    assert eff.summary == text[:200] and "click_stopped_after_press" not in eff.evidence
    del take[:]
    eff = _act(take, "click", "Go", action_text="clicked snap-1:1")
    assert "click_stopped_after_press" not in eff.evidence and "stopped" not in eff.summary


UNPRESSED = ("refused (browser_action_unavailable): no press or click was sent: {why} after {last} (6 hover and move "
             "events were sent)")


@pytest.mark.parametrize("why", ["the ref's node left the filmed point",
                                 "the page hid or replaced the pointer over the ref's node"])
def test_a_click_refused_after_its_own_hover_events_begins_by_saying_no_press_went(take, why):
    """FP38, FP44: hover events reached the page, so this is not "not sent"; the session prints a
    hundred characters of a refusal's summary, and the driver's text begins with the fact that matters."""
    text = UNPRESSED.format(why=why, last="mousemove")
    eff = _act(take, "click", "Go", action={"effect": "refused", "summary": text}, action_text=text)
    assert (eff.effect, eff.error_code) == ("refused", "browser_action_unavailable") and eff.dispatched is not False
    assert eff.summary.startswith("the pointer moved; the click was then refused: no press or click was sent: " + why)
    assert "no press or click was sent" in eff.summary[:100]


def test_every_mark_the_bridge_adds_to_a_delivery_that_went_is_one_the_session_says(take):
    """FP38: the session prints the marks named in ``filmed.PAGE_MARKS``; a mark the bridge adds and the
    list lacks would be dropped again."""
    from jevdual.filmed import PAGE_MARKS

    text = STOPPED.format(why="the ref's node left the filmed point", last="mousedown", count=8)
    take.left, take.frames = 2, "the page area is 300x450 at 420.0,360.0; the take recorded 300x450 at 420.0,330.0"
    eff = _act(take, "click", "Go", action={"effect": "unverifiable", "summary": text}, action_text=text)
    assert eff.evidence == ("click_stopped_after_press", "pointer_left_during_delivery", "scene_changed_during_delivery")
    assert set(eff.evidence) <= set(PAGE_MARKS)
    # the click that did not complete is said first, then what was found when it returned
    assert eff.summary.startswith("the click stopped after mousedown and no click event was sent: ")
    assert "observe before acting again. When it returned, the pointer was not where it was verified" in eff.summary


@pytest.mark.parametrize("world", [None, "main", True])
def test_a_locate_the_page_could_have_answered_for_is_refused_before_anything_moves(take, world):
    """Sol round 5: read in the page's own script world, the hit test is the page's word."""
    eff = _act(take, "click", "Go", locates=[at(world=world)])
    assert (eff.effect, eff.dispatched, eff.error_code, eff.evidence) == ("refused", False, "target_unlocated", ())
    assert "out of reach of the page's own script" in eff.summary
    assert take == GO_STEPS[:2]


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
    at(world=None, point=under()),
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
    assert take[-2:] == [("held", take.lands), ("after", take.lands)]


@pytest.mark.parametrize(("operation", "label", "text"), [("click", "Go", None), ("type", "Name", "Ada")])
@pytest.mark.parametrize("posted", [12, 0])
def test_a_page_action_refused_after_the_approach_says_whether_the_pointer_moved(take, operation, label, text, posted):
    """Sol round 3: the driver or the holder can refuse the action itself after the pointer has
    arrived; that refusal must not read as if nothing had happened."""
    take.posted = posted
    box = GO if label == "Go" else NAME
    eff = _act(take, operation, label, text, locates=[focused(box), focused(box)], action=REFUSED)
    assert (eff.effect, eff.error_code) == ("refused", "browser_ref_stale")
    assert "the ref's node is gone" in eff.summary
    assert eff.summary.startswith(f"the pointer moved; the {operation} was then refused: ") is bool(posted)
    assert ("pointer_moved" in eff.evidence) is bool(posted)
    assert _kinds(take)[-1] in ("browser_click", "browser_type")  # no pointer check after a refusal


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
    assert take == GO_STEPS[:6] and take.sent == []


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
    (at(world=None), "out of reach of the page's own script"),
    (at(world="main"), "out of reach of the page's own script"),
    ({k: v for k, v in at().items() if k != "world"}, "out of reach of the page's own script"),
    (at(cursor="none"), "hides or replaces the pointer over it (cursor: none)"),
    (at(cursor='url("x.png") 4 4, auto'), "hides or replaces the pointer over it (cursor: url("),
    (at(cursor="pointer, auto"), "hides or replaces the pointer over it"),
    (at(cursor=None), "did not say what the pointer looks like over it"),
    (at(cursor=7), "hides or replaces the pointer over it"),
    ({k: v for k, v in at().items() if k != "cursor"}, "did not say what the pointer looks like over it"),
    (at((40.0, 440.0, 80.0, 30.0)), "a target the film shows whole"),
    (at(clipped=True), "a target the film shows whole"),
    (at(filmed_delivery=None), "checks the pointer's position when it delivers"),
    (at(filmed_delivery="yes"), "checks the pointer's position when it delivers"),
    ({k: v for k, v in at().items() if k != "filmed_delivery"}, "checks the pointer's position when it delivers"),
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
    (at(point=under(cursor="none")), "hides or replaces the pointer where it landed (cursor: none)"),
    (at(point=under(cursor='url("x.png"), auto')), "hides or replaces the pointer where it landed"),
    (at(point=under(cursor=None)), "did not say what the pointer looks like where it landed"),
    (at(point={"x": 80.0, "y": 115.0, "hit": "target"}), "did not say what the pointer looks like where it landed"),
    (at((40.0, 120.0, 80.0, 30.0), point=under()), "outside it"),
    (at((90.0, 100.0, 80.0, 30.0), point=under()), "outside it"),
])
def test_a_landing_point_that_is_not_on_the_target_gives_no_rectangle_and_says_why(locate, why):
    rect, reason = browser_driver.located_rect(locate, GO_CENTRE)
    assert rect is None and why in reason, reason


def test_focus_is_the_fields_own():
    """FP26: the filmed insert focuses nothing and inserts only into the active element, so the page
    having the keyboard no longer matters, and the driver need not report it."""
    assert browser_driver.unfocused(focused()) is None
    assert browser_driver.unfocused(focused(page_focused=False)) is None
    assert browser_driver.unfocused(focused(page_focused=None)) is None
    for block in (at(), at(page_focused=False), at(focused="yes"), at(focused=1, page_focused=1), at(focused=None),
                  None, {}):
        assert browser_driver.unfocused(block)


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


def test_the_held_route_carries_a_filmed_point_only_when_there_is_one():
    """FP26: an unfilmed click or type is the request every holder serves; a filmed one adds a field,
    which a holder started by an older build rejects, and that is said with nothing sent."""
    from jevdual.browser_session_holder import OPERATIONS, OPTIONAL, RemoteBrowserOperations
    from jevdual.effectors.base import BrowserRefusal, BrowserReply

    sent: list = []
    stale = BrowserReply(status="refused", text="holder_request_invalid", is_error=True, dispatched=False,
                         refusal=BrowserRefusal(code="holder_request_invalid", message="holder_request_invalid"))
    answers: list = []

    async def op(self, method, **args):
        sent.append((method, args))
        return answers.pop(0) if answers else BrowserReply(status="ok", text="", is_error=False)

    operations = RemoteBrowserOperations.__new__(RemoteBrowserOperations)
    operations._op = op.__get__(operations)
    click = {"target_id": "t", "tab_id": "b", "ref": "r", "input_route": "dom_event"}
    kind = {"target_id": "t", "tab_id": "b", "ref": "r", "text": "Ada", "replace": False}
    asyncio.run(operations.click(**click))
    asyncio.run(operations.type_text(**kind))
    asyncio.run(operations.click(**click, filmed_point=(80, 115.5)))
    asyncio.run(operations.type_text(**kind, filmed_point=(110, 212)))
    assert sent == [("click", click), ("type_text", kind),
                    ("click", {**click, "filmed_point": [80.0, 115.5]}),
                    ("type_text", {**kind, "filmed_point": [110.0, 212.0]})]
    assert set(sent[0][1]) == OPERATIONS["click"] and set(sent[1][1]) == OPERATIONS["type_text"]
    assert OPTIONAL == {"click": {"filmed_point"}, "type_text": {"filmed_point"}}
    for call, what in ((operations.click(**click, filmed_point=(80, 115.5)), "filmed click"),
                       (operations.type_text(**kind, filmed_point=(110, 212)), "filmed type")):
        answers.append(stale)
        old = asyncio.run(call)
        assert old.refused and old.dispatched is False and old.refusal.code == "holder_request_invalid"
        assert f"does not serve this {what} request (an older build started it)" in old.refusal.message
        assert old.refusal.detail["delivery"] == "not_sent"
    # the same code on an unfilmed request is the holder's own word and is passed on as it came
    answers.append(stale)
    assert asyncio.run(operations.click(**click)) is stale


def test_the_driver_is_sent_the_point_as_x_and_y_only_when_filmed():
    from jevdual.effectors.cua import CuaBrowserOperations

    calls: list = []

    class Driver:
        async def call_tool(self, name, args_json):
            calls.append((name, json.loads(args_json)))
            return SimpleNamespace(structured_json=json.dumps({"status": "ok"}), text="", is_error=False)

    operations = CuaBrowserOperations(Driver(), session="s")
    base = {"session": "s", "target_id": "t", "tab_id": "b", "ref": "r"}
    asyncio.run(operations.click(target_id="t", tab_id="b", ref="r", input_route="dom_event"))
    asyncio.run(operations.click(target_id="t", tab_id="b", ref="r", input_route="dom_event", filmed_point=[80, 115.5]))
    asyncio.run(operations.type_text(target_id="t", tab_id="b", ref="r", text="Ada", replace=False))
    asyncio.run(operations.type_text(target_id="t", tab_id="b", ref="r", text="Ada", replace=False,
                                     filmed_point=(110, 212)))
    typed = {**base, "text": "Ada", "mode": "insert_text", "replace": False}
    assert calls == [("browser_click", {**base, "input_route": "dom_event"}),
                     ("browser_click", {**base, "input_route": "dom_event", "filmed_point": {"x": 80.0, "y": 115.5}}),
                     ("browser_type", typed),
                     ("browser_type", {**typed, "filmed_point": {"x": 110.0, "y": 212.0}})]


# ---- the scene reader


def _scene(monkeypatch, *, front=42, main=True, window=WINDOW, area=(CONTENT, URL), error=False, url=URL,
           point=None, over=(7, True), delivered=False):
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
    return browser_scene_change(42, 7, Filmed(window=WINDOW, content=CONTENT), url, point, delivered=delivered)


def test_the_reading_after_a_delivery_looks_at_the_frames_and_under_the_pointer_and_nothing_else(monkeypatch):
    """FP26, FP35: after a delivery the action's own effects may have changed the address, the main
    window and the frontmost application; where the page is and what is under the pointer still say
    whether the pointer was on the page."""
    after_a_click = {"front": 99, "main": False, "area": (CONTENT, URL + "/next"), "url": URL, "delivered": True}
    assert _scene(monkeypatch, **after_a_click) is None
    assert _scene(monkeypatch, front=99, main=False, area=(CONTENT, None), url=None, delivered=True) is None
    here = {"point": GO_SCREEN}
    assert _scene(monkeypatch, **after_a_click | here) is None
    assert "(another window is there)" in _scene(monkeypatch, **after_a_click | here | {"over": (9, True)})
    assert "(something that is not the page is there)" in _scene(monkeypatch, **after_a_click | here | {"over": (7, False)})
    moved = (WINDOW[0] - 20.0, *WINDOW[1:])
    assert "the scene window is 300x480 at 400.0,300.0" in _scene(monkeypatch, **after_a_click | {"window": moved})
    shifted = ((CONTENT[0], CONTENT[1] + 30.0, *CONTENT[2:]), URL)
    assert "the page area is 300x450 at 420.0,360.0" in _scene(monkeypatch, **after_a_click | {"area": shifted})
    assert "shows no web area" in _scene(monkeypatch, **after_a_click | {"area": None})
    assert "could not be read" in _scene(monkeypatch, error=True, delivered=True)
    assert "without a frame" in _scene(monkeypatch, window=None, delivered=True)


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
