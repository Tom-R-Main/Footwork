"""A filmed browser take moves the real pointer onto each page target before the page action (FP1).

The bridge, its snapshot projection and Filmed's viewport mapping are real; the driver is a fake wire
and the pointer move is recorded instead of posted.
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
         "visibility": "in_viewport", "rect": {"x": 40.0, "y": 100.0, "width": 80.0, "height": 30.0}},
        {"ref": "snap-1:2", "role": "textbox", "name": "Name", "actions": ["type"], "frame": "main",
         "visibility": "in_viewport", "rect": {"x": 10.0, "y": 200.0, "width": 200.0, "height": 24.0}},
        {"ref": "snap-1:3", "role": "button", "name": "Below", "actions": ["click"], "frame": "main",
         "visibility": "offscreen", "rect": None},
    ],
}


class Wire:
    def __init__(self, log: list) -> None:
        self.log = log

    async def call_tool(self, name, args_json):
        args = json.loads(args_json)
        if name not in ("browser_prepare", "get_browser_state"):
            self.log.append((name, args.get("ref")))
        if name == "get_browser_state":
            reply = SNAPSHOT if "tab_id" in args else BOUND
        else:
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
        return {"kind": "approach", "label": label}

    monkeypatch.setattr(Filmed, "approach", approach)
    return log


def _act(log, operation, label, text=None, *, filmed=True, take_ended=None):
    async def run():
        bridge = BrowserBridge(Wire(log), 42, 7, policy=ExecutionPolicy("exclusive_desktop"))
        if filmed:
            bridge.filmed = Filmed(window=WINDOW, content=CONTENT, take_ended=take_ended)
        await bridge.attach()
        nm = await bridge.observe()
        target = next(c.id for c in nm.menu.candidates if c.label == label)
        return await bridge.act(nm, operation, target, text)

    return asyncio.run(run())


def test_a_filmed_click_travels_to_the_targets_screen_rect_before_the_page_click(take):
    eff = _act(take, "click", "Go")
    assert eff.dispatched is not False
    # viewport (40, 100) plus the content origin (420, 330); width and height carry over
    assert take == [("approach", (460.0, 430.0, 80.0, 30.0), "Go"), ("browser_click", "snap-1:1")]


def test_a_filmed_type_travels_to_the_field_before_typing(take):
    _act(take, "type", "Name", "Ada")
    assert take == [("approach", (430.0, 530.0, 200.0, 24.0), "Name"), ("browser_type", "snap-1:2")]


def test_a_target_without_a_viewport_rect_is_refused_with_nothing_sent(take):
    eff = _act(take, "click", "Below")
    assert (eff.effect, eff.dispatched, eff.error_code) == ("refused", False, "target_unlocated")
    assert take == []


def test_an_ended_take_refuses_the_approach_and_sends_nothing(take):
    eff = _act(take, "click", "Go", take_ended="pointer_moved_idle")
    assert (eff.effect, eff.dispatched, eff.error_code) == ("refused", False, "take_ended")
    assert take == []


def test_an_unfilmed_session_clicks_without_moving_the_pointer(take):
    _act(take, "click", "Go", filmed=False)
    assert take == [("browser_click", "snap-1:1")]


@pytest.mark.parametrize("rect", [
    None, [1, 2, 3, 4], {"x": 1, "y": 2, "width": 3}, {"x": 1, "y": 2, "width": 0, "height": 4},
    {"x": "a", "y": 2, "width": 3, "height": 4}, {"x": float("nan"), "y": 2, "width": 3, "height": 4},
])
def test_a_missing_or_malformed_rect_gives_no_geometry(rect):
    assert browser_driver._viewport_rect(rect) is None


def test_a_well_formed_rect_is_kept_as_floats():
    assert browser_driver._viewport_rect({"x": 1, "y": 2.5, "width": 3, "height": 4}) == (1.0, 2.5, 3.0, 4.0)
