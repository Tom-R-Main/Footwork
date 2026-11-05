"""An empty web text field is empty, not its placeholder (notebook FT1).

CUA's tree builder reports AXPlaceholderValue as the value when AXValue is empty
(platform-macos ax/tree.rs:500-503). Footwork reads the field itself before trusting that.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

pytest.importorskip("cua_driver")

from jevdual import native
from jevdual.native import NativeBridge
from jevdual.posture import ExecutionPolicy

from tests.test_posture import Activity, FakeDriver

pytestmark = pytest.mark.usefixtures("mac_native_contract")


class AX:
    """Real AX attributes per field frame: (AXValue, AXPlaceholderValue)."""

    AXError = native.NativeBridgeError  # any exception type the bridge catches

    def __init__(self, fields):
        self.fields = fields
        self.Frame = lambda x, y, w, h: (x, y, w, h)

    def resolve(self, pid, wid, role, frame):
        return self.fields[frame]

    def value(self, el):
        return el[0]

    def placeholder(self, el):
        return el[1]


def _snapshot():
    return SimpleNamespace(
        snapshot_id="s00000001",
        app_name="Google Chrome",
        window_title="DemoGeek",
        pid=1,
        window_id=2,
        elements_complete=True,
        tree_markdown="",
        elements=[
            {"element_index": 0, "role": "AXWindow", "label": "DemoGeek", "element_token": "s00000001:0"},
            {
                "element_index": 1,
                "role": "AXTextArea",
                "label": "Message",
                "value": "Describe what to film…",
                "element_token": "s00000001:1",
                "frame": {"x": 40.0, "y": 800.0, "w": 300.0, "h": 40.0},
                "actions": ["AXShowMenu"],
                "in_web_content": True,
            },
            {
                "element_index": 2,
                "role": "AXTextField",
                "label": "Title",
                "value": "Relay demo",
                "element_token": "s00000001:2",
                "frame": {"x": 40.0, "y": 100.0, "w": 300.0, "h": 30.0},
                "actions": ["AXShowMenu"],
                "in_web_content": True,
            },
        ],
    )


def test_an_empty_web_field_reports_no_value_and_a_filled_one_keeps_its_text(monkeypatch):
    monkeypatch.setattr(native, "sys", SimpleNamespace(platform="darwin"))
    ax = AX(
        {
            (40.0, 800.0, 300.0, 40.0): ("", "Describe what to film…"),
            (40.0, 100.0, 300.0, 30.0): ("Relay demo", "Untitled"),
        }
    )
    bridge = NativeBridge(
        FakeDriver(_snapshot()), 1, 2, policy=ExecutionPolicy("exclusive_desktop", activity=Activity()), ax=ax
    )
    nm = asyncio.run(bridge.observe())
    message = next(c for c in nm.menu.candidates if c.label == "Message")
    title = next(c for c in nm.menu.candidates if c.label == "Title")
    assert nm.values.get(message.id, "") == "" and not message.value
    assert nm.values[title.id] == "Relay demo" and title.value == "Relay demo"
