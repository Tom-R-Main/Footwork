"""Native System 2: closed action set, validation against the menu, the destructive gate, done via the verifier."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from jevdual.arbiter import Arbiter, ArbiterPolicy
from jevdual.desktop import NativeAgent, keyword_gate
from jevdual.desktop_s2 import ChatReply, NativeS2, parse_reply
from jevdual.native import NativeBridge

from tests.test_desktop import FakeDriver, FakeHook, SeqPolicy, _decision, _ids

FIXTURE = Path(__file__).parent / "fixtures" / "native" / "calculator.json"


@pytest.fixture
def stub_sdk(monkeypatch):
    stub = SimpleNamespace(
        GetWindowStateInput=lambda **kw: kw,
        ClickInput=lambda **kw: kw,
        PressKeyInput=lambda **kw: kw,
        ClickPosition=SimpleNamespace(ELEMENT=lambda element_token: ("element", element_token)),
        InputDeliveryMode=SimpleNamespace(BACKGROUND="background", FOREGROUND="foreground"),
        ActionTarget=SimpleNamespace(WINDOW=lambda pid, window_id: ("window", pid, window_id)),
    )
    monkeypatch.setitem(sys.modules, "cua_driver", stub)
    return stub


@pytest.fixture
def snapshot():
    return json.loads(FIXTURE.read_text())


class KeyDriver(FakeDriver):
    async def press_key(self, inp):
        self.calls.append(("press_key", inp))
        return SimpleNamespace(
            action=SimpleNamespace(
                effect=SimpleNamespace(name="UNVERIFIABLE"),
                route=SimpleNamespace(name="SYNTHETIC_EVENTS"),
                evidence=None,
                summary="key",
            ),
            text="",
            is_error=False,
            error_code=None,
        )


class ScriptedChat:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.messages = []

    async def __call__(self, messages):
        self.messages.append(messages)
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return ChatReply(
            content=r if isinstance(r, str) else json.dumps(r), input_tokens=100, output_tokens=20
        )


def _agent(driver, policy, s2, **kw):
    bridge = NativeBridge(driver, pid=1, window_id=2)
    kw.setdefault("task", "Compute 6 times 7")
    kw.setdefault("text_source", lambda task, target, menu: None)
    kw.setdefault("arbiter", Arbiter.from_toml())
    return NativeAgent(bridge, policy, s2=s2, **kw)


def test_parse_reply_accepts_fenced_json_and_rejects_unknown_actions():
    note, action = parse_reply('```json\n{"note": "press six", "action": {"name": "click", "id": 11}}\n```')
    assert note == "press six" and action == {"name": "click", "id": 11}
    with pytest.raises(ValueError):
        parse_reply('{"note": "x", "action": {"name": "teleport"}}')
    with pytest.raises(ValueError):
        parse_reply("no json here")


def test_s2_click_is_validated_against_the_menu_and_executed(snapshot, stub_sdk):
    ids = _ids(snapshot)
    policy = SeqPolicy(_decision("click", ids["6"], tconf=0.1), _decision("done"))
    chat = ScriptedChat({"note": "press 7 instead", "action": {"name": "click", "id": ids["7"]}})
    s2 = NativeS2(chat, policy=ArbiterPolicy.from_toml())
    driver = FakeDriver(snapshot)
    run = asyncio.run(_agent(driver, policy, s2, verifier=FakeHook("accept", "ok")).run())
    assert run.status == "done" and run.s2_steps == 1
    step = run.steps[0]
    assert step.system == "s2" and step.executed[0].params["index"] == ids["7"]
    assert step.memory_line == "press 7 instead" and step.llm_input_tokens == 100
    user = json.loads(chat.messages[0][1]["content"])
    assert user["escalation_reason"].startswith("target_confidence")
    assert user["s1_suggestion"]["target"]["label"] == "6"
    assert all("element_token" not in e for e in user["elements"])


def test_s2_invalid_reply_and_bad_id_fail_closed(snapshot, stub_sdk):
    ids = _ids(snapshot)
    policy = SeqPolicy(
        _decision("click", ids["6"], tconf=0.1), _decision("click", ids["6"], tconf=0.1), _decision("blocked")
    )
    chat = ScriptedChat(
        "I think we should click six",
        {"note": "x", "action": {"name": "click", "id": 9999}},
        {"note": "nothing to do", "action": {"name": "blocked"}},
    )
    s2 = NativeS2(chat)
    driver = FakeDriver(snapshot)
    run = asyncio.run(_agent(driver, policy, s2).run())
    assert run.status == "blocked"  # S1's blocked went to System 2, which agreed
    assert run.steps[0].error.startswith("s2 invalid reply") and not run.steps[0].executed
    assert "not on the menu" in run.steps[1].error
    assert not [n for n, _ in driver.calls if n == "click"]


def test_s2_type_and_key(stub_sdk):
    snap = {
        "snapshot_id": "s1",
        "pid": 1,
        "window_id": 2,
        "app_name": "TextEdit",
        "window_title": "Untitled",
        "elements_complete": True,
        "tree_markdown": "",
        "elements": [
            {"element_index": 0, "role": "AXWindow", "label": "Untitled", "actions": ["AXRaise"]},
            {
                "element_index": 1,
                "role": "AXTextArea",
                "label": "",
                "value": "",
                "parent_index": 0,
                "enabled": True,
            },
        ],
    }
    policy = SeqPolicy(_decision("type", 1, tconf=0.1), _decision("type", 1, tconf=0.1), _decision("blocked"))
    chat = ScriptedChat(
        {"note": "write it", "action": {"name": "type", "id": 1, "text": "hello world"}},
        {"note": "save", "action": {"name": "key", "key": "s", "modifiers": ["cmd"]}},
        {"note": "nothing to do", "action": {"name": "blocked"}},
    )
    driver = KeyDriver(snap)
    run = asyncio.run(_agent(driver, policy, NativeS2(chat), task="Write hello world").run())
    set_calls = [a for n, a in driver.calls if n == "set_value"]
    assert set_calls and set_calls[0]["value"] == "hello world"
    keys = [a for n, a in driver.calls if n == "press_key"]
    assert keys and keys[0]["key"] == "s" and keys[0]["modifiers"] == ["cmd"]
    assert run.steps[1].executed[0].name == "send_keys" and run.steps[1].executed[0].params["keys"] == "cmd+s"


def test_s2_done_goes_through_the_verifier(snapshot, stub_sdk):
    ids = _ids(snapshot)
    policy = SeqPolicy(
        _decision("click", ids["6"], tconf=0.1),
        _decision("click", ids["6"], tconf=0.1),
        _decision("click", ids["6"], tconf=0.1),
    )
    chat = ScriptedChat(
        {"note": "finished", "action": {"name": "done", "answer": "42", "success": True}},
        {"note": "finished", "action": {"name": "done", "answer": "42", "success": True}},
    )
    hook = FakeHook("reject", "display is empty")
    run = asyncio.run(_agent(FakeDriver(snapshot), policy, NativeS2(chat), verifier=hook).run())
    assert run.status == "error" and "done refused 2 times" in run.reason
    assert run.steps[0].verify["band"] == "reject" and not run.steps[0].is_done
    hook = FakeHook("accept", "display shows 42")
    chat = ScriptedChat({"note": "finished", "action": {"name": "done", "answer": "42", "success": True}})
    policy = SeqPolicy(_decision("click", ids["6"], tconf=0.1))
    run = asyncio.run(_agent(FakeDriver(snapshot), policy, NativeS2(chat), verifier=hook).run())
    assert run.status == "done" and run.answer == "42" and run.steps[0].executed[0].name == "done"


def test_keyword_gate_pauses_s2_click_and_authorisation_stands_it_down(snapshot, stub_sdk):
    ids = _ids(snapshot)
    snap = dict(snapshot)
    snap["elements"] = [
        *snapshot["elements"],
        {
            "element_index": 900,
            "element_token": "x:900",
            "role": "AXButton",
            "label": "Delete account",
            "parent_index": 0,
            "actions": ["AXPress"],
            "enabled": True,
        },
    ]
    policy = SeqPolicy(_decision("click", ids["6"], tconf=0.1))
    chat = ScriptedChat({"note": "delete it", "action": {"name": "click", "id": 900}})
    driver = FakeDriver(snap)
    run = asyncio.run(_agent(driver, policy, NativeS2(chat, policy=ArbiterPolicy.from_toml())).run())
    assert run.status == "paused" and "keyword 'delete'" in run.reason
    assert not [n for n, _ in driver.calls if n == "click"]
    # authorised: the same click goes through
    policy = SeqPolicy(_decision("click", ids["6"], tconf=0.1), _decision("blocked"))
    chat = ScriptedChat(
        {"note": "delete it", "action": {"name": "click", "id": 900}},
        {"note": "nothing to do", "action": {"name": "blocked"}},
    )
    driver = FakeDriver(snap)
    s2 = NativeS2(chat, policy=ArbiterPolicy.from_toml(), authorized_actions=("delete account",))
    run = asyncio.run(_agent(driver, policy, s2).run())
    assert [n for n, _ in driver.calls if n == "click"] == ["click"]


def test_judgment_gate_asks_jev_on_s2_clicks_only(snapshot, stub_sdk):
    ids = _ids(snapshot)
    asked = []

    class V:
        async def judge_destructive(self, task, targets, *, url, title):
            asked.append([t["label"] for t in targets])
            return [0.9 if t["label"] == "Equals" else 0.05 for t in targets]

    policy = SeqPolicy(_decision("click", ids["Equals"], tconf=0.1), _decision("click", ids["6"]))
    chat = ScriptedChat({"note": "equals", "action": {"name": "click", "id": ids["Equals"]}})
    s2 = NativeS2(chat, policy=ArbiterPolicy.from_toml(), verifier=V())
    driver = FakeDriver(snapshot)
    run = asyncio.run(_agent(driver, policy, s2, gate=keyword_gate()).run())
    assert run.status == "paused" and "judgment p=0.90" in run.reason
    assert asked == [["Equals"]] and s2.gate_judgments[0]["hit"] == "Equals"
    # S1's own confident click on 6 is not judged (its destructive noul already passed the arbiter)
    policy = SeqPolicy(_decision("click", ids["6"]), _decision("blocked"))
    asked.clear()
    s2.chat = ScriptedChat({"note": "nothing to do", "action": {"name": "blocked"}})
    run = asyncio.run(_agent(FakeDriver(snapshot), policy, s2, gate=keyword_gate()).run())
    assert asked == [] and run.steps[0].executed


def test_s2_transport_failure_is_a_step_error_not_a_crash(snapshot, stub_sdk):
    ids = _ids(snapshot)
    policy = SeqPolicy(_decision("click", ids["6"], tconf=0.1), _decision("blocked"))
    chat = ScriptedChat(RuntimeError("503"), {"note": "nothing to do", "action": {"name": "blocked"}})
    run = asyncio.run(_agent(FakeDriver(snapshot), policy, NativeS2(chat)).run())
    assert run.status == "blocked" and run.steps[0].error.startswith("s2 call failed")
