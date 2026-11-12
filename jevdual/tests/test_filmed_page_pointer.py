"""A filmed browser take puts the real pointer on each page target before the page action (FP4).

The bridge and Filmed's viewport mapping are real; the driver is a fake wire that answers the locate
mode of get_browser_state from a queue, and the pointer move is recorded instead of posted.
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest
from jevdual import browser_driver
from jevdual.browser_driver import BrowserBridge
from jevdual.filmed import Filmed
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
NAME = (10.0, 200.0, 200.0, 24.0)


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
    }
    block.update(changes)
    return block


REFUSED = {"status": "refused", "refusal": {"code": "browser_ref_stale", "message": "the ref's node is gone"}}


class Wire:
    """``locates`` is consumed one reply per locate call: a locate block, or a whole refusal reply."""

    def __init__(self, log: list, locates: list | None = None) -> None:
        self.log = log
        self.locates = list(locates or [])

    async def call_tool(self, name, args_json):
        args = json.loads(args_json)
        if name == "get_browser_state" and "locate_ref" in args:
            self.log.append(("locate", args["locate_ref"]))
            block = self.locates.pop(0) if self.locates else at()
            reply = block if "status" in block else {"status": "ok", "mode": "locate", "locate": block}
        elif name == "get_browser_state":
            reply = SNAPSHOT if "tab_id" in args else BOUND
        else:
            if name != "browser_prepare":
                self.log.append((name, args.get("ref") or args.get("url")))
            reply = {"status": "ok", "target_id": args.get("target_id"), "tab_id": args.get("tab_id")}
        return SimpleNamespace(structured_json=json.dumps(reply), text="done", is_error=False)

    async def shutdown(self):
        pass


@pytest.fixture
def take(monkeypatch):
    log: list = []

    async def approach(self, frame, label):
        self.check()
        log.append(("approach", frame, label))
        record = {"kind": "approach", "label": label, "samples": 12}
        self.gestures.append(record)
        return record

    monkeypatch.setattr(Filmed, "approach", approach)
    return log


def _act(log, operation, label, text=None, *, locates=None, filmed=True, take_ended=None):
    async def run():
        bridge = BrowserBridge(Wire(log, locates), 42, 7, policy=ExecutionPolicy("exclusive_desktop"))
        if filmed:
            bridge.filmed = Filmed(window=WINDOW, content=CONTENT, take_ended=take_ended)
        await bridge.attach()
        nm = await bridge.observe()
        target = next(c.id for c in nm.menu.candidates if c.label == label)
        return await bridge.act(nm, operation, target, text)

    return asyncio.run(run())


def test_a_filmed_click_locates_travels_and_locates_again_before_the_page_click(take):
    eff = _act(take, "click", "Go")
    assert eff.dispatched is not False
    # viewport (40, 100) plus the content origin (420, 330); width and height carry over
    assert take == [("locate", "snap-1:1"), ("approach", (460.0, 430.0, 80.0, 30.0), "Go"),
                    ("locate", "snap-1:1"), ("browser_click", "snap-1:1")]


def test_a_filmed_type_travels_to_the_field_before_typing(take):
    _act(take, "type", "Name", "Ada", locates=[at(NAME), at(NAME)])
    assert take == [("locate", "snap-1:2"), ("approach", (430.0, 530.0, 200.0, 24.0), "Name"),
                    ("locate", "snap-1:2"), ("browser_type", "snap-1:2")]


def test_a_target_the_pointer_cannot_reach_is_refused_before_anything_moves(take):
    eff = _act(take, "click", "Go", locates=[at(hit="other")])
    assert (eff.effect, eff.dispatched, eff.error_code) == ("refused", False, "target_unlocated")
    assert "another element is at its centre" in eff.summary and "pointer moved" not in eff.summary
    assert eff.evidence == ()
    assert take == [("locate", "snap-1:1")]


def test_a_target_that_moved_during_the_approach_is_refused_and_says_the_pointer_moved(take):
    moved = (GO[0], GO[1] + 40.0, GO[2], GO[3])
    eff = _act(take, "click", "Go", locates=[at(), at(moved)])
    assert (eff.effect, eff.dispatched, eff.error_code) == ("refused", False, "target_moved")
    assert eff.summary.startswith("the pointer moved but the click was not sent: ")
    assert "moved 40 px" in eff.summary and eff.evidence == ("pointer_moved",)
    assert [entry[0] for entry in take] == ["locate", "approach", "locate"]


def test_a_target_within_tolerance_after_the_approach_is_clicked(take):
    nudged = (GO[0] + 1.0, GO[1] + 1.0, GO[2], GO[3])
    _act(take, "click", "Go", locates=[at(), at(nudged)])
    assert take[-1] == ("browser_click", "snap-1:1")


@pytest.mark.parametrize("second", [REFUSED, at(hit="other"), {"available": False, "reason": "unreadable"}])
def test_a_target_not_found_under_the_pointer_after_the_approach_is_refused(take, second):
    eff = _act(take, "click", "Go", locates=[at(), second])
    assert (eff.dispatched, eff.error_code) == (False, "target_moved")
    assert eff.evidence == ("pointer_moved",)
    assert [entry[0] for entry in take] == ["locate", "approach", "locate"]


def test_a_driver_refusal_of_the_first_locate_withholds_the_action(take):
    eff = _act(take, "click", "Go", locates=[REFUSED])
    assert (eff.dispatched, eff.error_code) == (False, "target_unlocated")
    assert "the ref's node is gone" in eff.summary
    assert take == [("locate", "snap-1:1")]


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
])
def test_a_target_a_pointer_cannot_be_put_on_gives_no_rectangle_and_says_why(locate, why):
    rect, reason = browser_driver.located_rect(locate)
    assert rect is None and why in reason, reason


def test_the_locate_operation_is_a_read_of_one_ref():
    from jevdual.browser_session_holder import OPERATIONS, SENDING
    from jevdual.effectors.cua import CuaBrowserOperations

    calls: list = []

    class Driver:
        async def call_tool(self, name, args_json):
            calls.append((name, json.loads(args_json)))
            return SimpleNamespace(structured_json=json.dumps({"status": "ok", "locate": at()}), text="", is_error=False)

    reply = asyncio.run(CuaBrowserOperations(Driver(), session="s").locate(target_id="t", tab_id="b", ref="r"))
    assert calls == [("get_browser_state", {"session": "s", "target_id": "t", "tab_id": "b", "locate_ref": "r"})]
    assert reply.payload["locate"]["hit"] == "target"
    assert OPERATIONS["locate"] == {"target_id", "tab_id", "ref"} and "locate" not in SENDING
    assert browser_driver.LOCATE_TOLERANCE_PX == 2.0
