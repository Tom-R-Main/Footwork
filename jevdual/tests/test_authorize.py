"""One authorization boundary: every native route (click, type, append, enter, key, hotkey, menu) is
checked before dispatch; a failed judgment is a pause, never an allow (secondary audit, 2026-09-24)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from jevdual.arbiter import Arbiter, ArbiterPolicy
from jevdual.authorize import Authorizer, action_for
from jevdual.desktop import NativeAgent, StepOutcome
from jevdual.desktop_s2 import NativeS2
from jevdual.native import NativeBridge, menu_from_snapshot

from tests.test_desktop import FakeDriver, SeqPolicy, _decision, _ids
from tests.test_desktop_s2 import KeyDriver, ScriptedChat, stub_sdk  # noqa: F401 - fixture

FIXTURE = Path(__file__).parent / "fixtures" / "native" / "calculator.json"


@pytest.fixture
def snapshot():
    return json.loads(FIXTURE.read_text())


def _sheet_snapshot():
    """A TextEdit-like window with a Replace sheet: Return would activate the default button."""
    return {
        "snapshot_id": "s1",
        "pid": 1,
        "window_id": 2,
        "app_name": "TextEdit",
        "window_title": "note.txt",
        "elements_complete": True,
        "tree_markdown": '- [0] AXWindow "note.txt"\n    - AXStaticText = "“note.txt” already exists. Do you want to replace it?"\n',
        "elements": [
            {
                "element_index": 0,
                "element_token": "s1:0",
                "role": "AXWindow",
                "label": "note.txt",
                "actions": ["AXRaise"],
            },
            {
                "element_index": 1,
                "element_token": "s1:1",
                "role": "AXTextArea",
                "label": "",
                "value": "First line.\nA long enough second line.",
                "parent_index": 0,
                "enabled": True,
            },
            {
                "element_index": 2,
                "element_token": "s1:2",
                "role": "AXButton",
                "label": "Replace",
                "parent_index": 0,
                "actions": ["AXPress"],
                "enabled": True,
            },
            {
                "element_index": 3,
                "element_token": "s1:3",
                "role": "AXButton",
                "label": "Cancel",
                "parent_index": 0,
                "actions": ["AXPress"],
                "enabled": True,
            },
        ],
    }


class RecordingDriver(KeyDriver):
    async def invoke_menu(self, inp):
        self.calls.append(("invoke_menu", inp))
        return SimpleNamespace(
            action=SimpleNamespace(
                effect=SimpleNamespace(name="CONFIRMED"),
                route=SimpleNamespace(name="ACCESSIBILITY"),
                evidence=None,
                summary="menu",
            ),
            text="",
            is_error=False,
            error_code=None,
        )


def _menu_stub(monkeypatch):
    import sys

    stub = SimpleNamespace(
        GetWindowStateInput=lambda **kw: kw,
        ClickInput=lambda **kw: kw,
        PressKeyInput=lambda **kw: kw,
        InvokeMenuInput=lambda **kw: kw,
        HotkeyInput=lambda **kw: kw,
        ClickPosition=SimpleNamespace(ELEMENT=lambda element_token: ("element", element_token)),
        InputDeliveryMode=SimpleNamespace(BACKGROUND="background", FOREGROUND="foreground"),
        ActionTarget=SimpleNamespace(WINDOW=lambda pid, window_id: ("window", pid, window_id)),
    )
    monkeypatch.setitem(sys.modules, "cua_driver", stub)


def test_key_routes_read_chord_meaning_and_buttons_on_screen(monkeypatch):
    _menu_stub(monkeypatch)
    nm = menu_from_snapshot(_sheet_snapshot())
    auth = Authorizer(policy=ArbiterPolicy.from_toml())
    # cmd+delete means delete
    a = action_for("hotkey", nm, "s2", keys=("cmd", "delete"))
    assert "keyword 'delete'" in asyncio.run(auth.check(nm, a))
    # Return with a Replace button on screen is a pause; without one it is not
    a = action_for("enter", nm, "s1", target=nm.menu.candidate(1))
    assert "button 'Replace'" in asyncio.run(auth.check(nm, a))
    plain = dict(_sheet_snapshot())
    plain["elements"] = [e for e in plain["elements"] if e.get("label") != "Replace"]
    nm2 = menu_from_snapshot(plain)
    assert asyncio.run(auth.check(nm2, action_for("enter", nm2, "s1", target=nm2.menu.candidate(1)))) is None
    # menu path
    assert "keyword 'move to trash'" in asyncio.run(
        auth.check(nm, action_for("menu", nm, "s2", path=("File", "Move to Trash")))
    )
    # scoped authorisation stands it down
    auth2 = Authorizer(policy=ArbiterPolicy.from_toml(), authorized_actions=("replace",))
    assert asyncio.run(auth2.check(nm, action_for("click", nm, "s2", target=nm.menu.candidate(2)))) is None


def test_replacing_existing_document_content_pauses_and_append_does_not(monkeypatch):
    _menu_stub(monkeypatch)
    nm = menu_from_snapshot(_sheet_snapshot())
    ta = nm.menu.candidate(1)
    assert ta.input_type == "textarea" and "\n" in (ta.value or "")
    auth = Authorizer(policy=ArbiterPolicy.from_toml())
    rep = asyncio.run(auth.check(nm, action_for("type", nm, "s1", target=ta, text="Second line.")))
    assert rep and rep.startswith("replaces")
    assert asyncio.run(auth.check(nm, action_for("append", nm, "s1", target=ta, text="Second line."))) is None
    # typing the same content back, or extending it, is not a replacement
    assert (
        asyncio.run(auth.check(nm, action_for("type", nm, "s1", target=ta, text=ta.value + "\nmore"))) is None
    )


def test_every_s2_route_goes_through_the_agent_boundary(snapshot, monkeypatch):
    """The audit's probe: a denying authorizer with S2 issuing key, hotkey, menu, click, type. Nothing dispatches."""
    _menu_stub(monkeypatch)
    ids = _ids(snapshot)
    replies = [
        {"note": "k", "action": {"name": "key", "key": "Delete", "modifiers": ["cmd"]}},
        {"note": "h", "action": {"name": "hotkey", "keys": ["cmd", "delete"]}},
        {"note": "m", "action": {"name": "menu", "path": ["File", "Move to Trash"]}},
        {"note": "c", "action": {"name": "click", "id": ids["6"]}},
    ]
    seen = []

    def deny(nm, target):
        seen.append(getattr(target, "label", None))
        return "denied by test"

    # a denying extra rule only sees targeted routes; the keyword rules cover the rest
    driver = RecordingDriver(snapshot)
    for reply in replies:
        policy = SeqPolicy(_decision("click", ids["6"], tconf=0.1))
        agent = NativeAgent(
            NativeBridge(driver, pid=1, window_id=2),
            policy,
            task="t",
            text_source=lambda t, c, m: None,
            arbiter=Arbiter.from_toml(),
            s2=NativeS2(ScriptedChat(reply)),
            authorizer=Authorizer(policy=ArbiterPolicy.from_toml(), extra=deny),
        )
        run = asyncio.run(agent.run())
        assert run.status == "paused", (reply, run.reason)
    mutating = [
        n for n, _ in driver.calls if n in ("click", "press_key", "hotkey", "invoke_menu", "set_value")
    ]
    assert mutating == []
    assert seen == ["6"]  # the click reached the extra rule; the key routes were stopped by keywords first


def test_judgment_failure_pauses_not_allows(snapshot, monkeypatch):
    _menu_stub(monkeypatch)
    ids = _ids(snapshot)

    async def broken(task, targets, url, title):
        raise RuntimeError("503")

    policy = SeqPolicy(_decision("click", ids["6"], tconf=0.1))
    chat = ScriptedChat({"note": "six", "action": {"name": "click", "id": ids["6"]}})
    auth = Authorizer(policy=ArbiterPolicy.from_toml(), judge=broken)
    driver = FakeDriver(snapshot)
    agent = NativeAgent(
        NativeBridge(driver, pid=1, window_id=2),
        policy,
        task="t",
        text_source=lambda t, c, m: None,
        arbiter=Arbiter.from_toml(),
        s2=NativeS2(chat),
        authorizer=auth,
    )
    run = asyncio.run(agent.run())
    assert run.status == "paused" and "judgment unavailable" in run.reason
    assert not [n for n, _ in driver.calls if n == "click"]
    assert auth.judgments and "error" in auth.judgments[0]
    # the keyword fallback is opt-in
    auth = Authorizer(policy=ArbiterPolicy.from_toml(), judge=broken, on_judgment_failure="keyword")
    policy = SeqPolicy(_decision("click", ids["6"], tconf=0.1), _decision("blocked"))
    chat = ScriptedChat(
        {"note": "six", "action": {"name": "click", "id": ids["6"]}},
        {"note": "n", "action": {"name": "blocked"}},
    )
    driver = FakeDriver(snapshot)
    agent = NativeAgent(
        NativeBridge(driver, pid=1, window_id=2),
        policy,
        task="t",
        text_source=lambda t, c, m: None,
        arbiter=Arbiter.from_toml(),
        s2=NativeS2(chat),
        authorizer=auth,
    )
    asyncio.run(agent.run())
    assert [n for n, _ in driver.calls if n == "click"] == ["click"]


def test_execute_records_proposal_and_page_text_in_trace(snapshot, monkeypatch, tmp_path):
    from jevdual.trace import TraceWriter, read_trace

    _menu_stub(monkeypatch)
    ids = _ids(snapshot)
    trace = TraceWriter(tmp_path / "t.jsonl")
    agent = NativeAgent(
        NativeBridge(FakeDriver(snapshot), pid=1, window_id=2),
        SeqPolicy(_decision("click", ids["6"]), _decision("blocked")),
        task="t",
        text_source=lambda t, c, m: None,
        trace=trace,
        run_id="r",
    )
    asyncio.run(agent.run())
    trace.close()
    _, steps = read_trace(tmp_path / "t.jsonl")
    assert steps[0].proposed[0].name == "click" and steps[0].proposed[0].params["label"] == "6"
    assert steps[0].page_text and "1,248" in steps[0].page_text
    out = StepOutcome(step=1, system="s1", menu=None)
    assert out.proposed == []
