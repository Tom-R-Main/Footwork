"""Linux bridge boundaries: qualified text, scoped dispatch and uncertain delivery."""

from __future__ import annotations

import asyncio
import json
import sys
from types import SimpleNamespace

import pytest
from jevdual import native
from jevdual.ax import AXError, Frame
from jevdual.posture import ExecutionPolicy, LinuxActivity


def element(index=1, role="text", **extra):
    return {
        "element_index": index,
        "element_token": f"s00000001:{index}",
        "role": role,
        "label": f"Field {index}",
        "enabled": True,
        "frame": {"x": float(index), "y": 20.0, "w": 300.0, "h": 100.0},
        **extra,
    }


def snapshot(*elements, **extra):
    return {
        "snapshot_id": "s00000001",
        "pid": 31,
        "window_id": 73,
        "app_name": "Mousepad",
        "window_title": "note.txt",
        "elements_complete": True,
        "tree_markdown": "",
        "elements": list(elements),
        **extra,
    }


def proof(value="old", *, writable=True, multiline=True):
    return {"value": value, "readable": True, "writable": writable, "multiline": multiline}


def outcome(mode="BACKGROUND"):
    return SimpleNamespace(
        action=SimpleNamespace(
            effect=SimpleNamespace(name="UNVERIFIABLE"),
            route=SimpleNamespace(name="ACCESSIBILITY"),
            delivery=SimpleNamespace(mode=SimpleNamespace(name=mode), delivered_count=1),
            evidence=None,
            summary="input acknowledged",
            error=None,
        ),
        is_error=False,
        error_code=None,
        text="input acknowledged",
    )


class Driver:
    def __init__(self, state=None):
        self.state = state
        self.calls = []
        self.failure = None

    async def get_window_state(self, args):
        self.calls.append(("get_window_state", args))
        return self.state

    async def call_tool(self, name, args):
        self.calls.append((name, json.loads(args)))
        if self.failure:
            raise self.failure
        return outcome("FOREGROUND")

    async def invoke_menu(self, args):
        self.calls.append(("invoke_menu", args))
        if self.failure:
            raise self.failure
        return outcome()


class ExactAX:
    AXError = AXError
    Frame = Frame

    def __init__(self, values=None, capabilities=None):
        self.values = {1: "old"} if values is None else values
        self.capabilities = capabilities or {}
        self.resolved = []
        self.writes = []
        self.write_error = None
        self.corrupt = None

    def resolve(self, pid, window_id, role, frame):
        assert (pid, window_id) == (31, 73)
        self.resolved.append((pid, window_id, role, frame))
        return int(frame.x)

    def text_capabilities(self, target):
        entry = self.capabilities.get(target, {"readable": True, "writable": True, "multiline": True})
        if isinstance(entry, AXError):
            raise entry
        return dict(entry)

    def value(self, target):
        return self.values[target]

    def can_set_value(self, target):
        return self.text_capabilities(target)["writable"] is True

    def set_value_ack(self, target, text):
        self.writes.append((target, text))
        self.values[target] = text if self.corrupt is None else self.corrupt(text)
        if self.write_error:
            raise self.write_error


@pytest.fixture(autouse=True)
def linux_sdk(monkeypatch):
    # Replace this module's binding, not process-wide sys.platform.
    monkeypatch.setattr(native, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setitem(sys.modules, "cua_driver", SimpleNamespace(
        GetWindowStateInput=lambda **kw: kw,
        InvokeMenuInput=lambda **kw: kw,
    ))


def bridge(driver=None, *, mode="background_only", ax=None):
    return native.NativeBridge(
        driver or Driver(), 31, 73, session="linux-test-session", ax=ax or ExactAX(),
        policy=ExecutionPolicy(mode, activity=LinuxActivity()),
    )


@pytest.mark.parametrize("change,refused", [
    ({}, True),
    ({"structured_json": json.dumps({
        "code": "foreground_unavailable", "effect": "none", "detail": "blocked",
        "suggestion": "confirm", "hint": "advisory", "next_call": {"tool": "never_execute"},
    })}, True),
    ({"structured_json": json.dumps({
        "code": "foreground_unavailable", "effect": "none", "detail": "blocked",
        "suggestion": "confirm", "delivered_count": 1,
    })}, False),
    ({"is_error": False}, False),
    ({"error_code": "transport_lost"}, False),
    ({"structured_json": None}, False),
    ({"structured_json": "{"}, False),
    ({"structured_json": "[]"}, False),
    ({"structured_json": '{"code":"foreground_unavailable","effect":"unverifiable"}'}, False),
    ({"structured_json": '{"code":"foreground_timeout","effect":"none"}'}, False),
    ({"action": outcome().action}, False),
])
def test_linux_save_structured_preinput_refusal_preserves_uncertainty(change, refused):
    target = bridge(mode="exclusive_desktop")
    calls = []
    result = SimpleNamespace(
        action=None, is_error=True, error_code="foreground_unavailable",
        text="activation failed; no input was sent",
        structured_json=json.dumps({
            "code": "foreground_unavailable", "effect": "none",
            "detail": "activation failed; no input was sent",
            "suggestion": "Confirm the bound window",
        }),
    )
    for key, value in change.items():
        setattr(result, key, value)

    async def reply(name, args):
        calls.append((name, json.loads(args)))
        return result

    target.driver.call_tool = reply
    effect = asyncio.run(target.hotkey(bound_text(target), ["ctrl", "s"]))
    assert len(calls) == 1
    assert effect.dispatched is not refused
    if refused:
        assert effect.effect == "refused" and effect.delivered_count == 0
        assert effect.delivery_basis == "qualified_gate" and effect.readback is None
    else:
        assert effect.effect == "unverifiable"
        assert effect.delivered_count == (1 if "action" in change else None)


def bound_text(target, *, value="old", supplied_proof=True):
    menu = native.menu_from_snapshot(
        snapshot(element(value="UPSTREAM PREVIEW")),
        linux_text={1: proof(value)} if supplied_proof else {},
    )
    target.last = menu
    return menu


def test_observe_qualifies_exact_text_and_keeps_unqualified_fields_passive():
    state = snapshot(
        element(1, value="UPSTREAM PREVIEW"),
        element(2, role="entry", actions=["activate", "buffer.delete-line"], value="untrusted"),
        element(3, role="entry", value="untrusted"),
        element(4, role="password text", value="secret-placeholder"),
        element(5, role="entry", frame=None, value="untrusted"),
    )
    ax = ExactAX(
        {1: "exact  \n\t", 2: "readonly", 3: "unused"},
        {2: {"readable": True, "writable": False, "multiline": False},
         3: AXError("element_ambiguous", "ambiguous field")},
    )
    driver = Driver(state)
    menu = asyncio.run(bridge(driver, ax=ax).observe())
    assert menu.values == {1: "exact  \n\t", 2: "readonly"}
    assert menu.menu.candidate(1).operations == ("type", "enter", "append")
    assert menu.menu.candidate(2).operations == ()
    assert menu.menu.candidate(3).operations == ()
    assert menu.menu.candidate(5).operations == ()
    assert menu.menu.candidate(4) is None
    assert {int(call[3].x) for call in ax.resolved} == {1, 2, 3}
    assert "secret-placeholder" not in repr(menu)
    assert "UPSTREAM PREVIEW" not in repr(menu)
    assert driver.calls[0][1]["pid"] == 31
    assert driver.calls[0][1]["window_id"] == 73
    assert driver.calls[0][1]["full_output"] is True


def test_projection_never_turns_malicious_actions_into_input():
    menu = native.menu_from_snapshot(snapshot(
        element(1, role="push button", actions=["buffer.delete-line"]),
        element(2, role="entry", actions=["clipboard.paste", "activate"]),
        element(3, role="paragraph", actions=["buffer.delete-line"]),
        element(4, role="push button", actions=["buffer.delete-line", "gtk.Activate"]),
    ), linux_text={})
    assert menu.menu.candidate(1).operations == ()
    assert menu.menu.candidate(2).operations == ()
    assert menu.menu.candidate(3) is None
    assert menu.menu.candidate(4).operations == ("click",)
    assert [c.id for c in menu.menu.by_operation["click"]] == [4]
    assert "type" not in menu.menu.by_operation


def test_long_exact_values_preserve_whitespace_independently_of_model_preview():
    text = "α\t  line\n" * 700 + " \n\t  "
    menu = native.menu_from_snapshot(snapshot(element(value="TRUNCATED SDK VALUE")), linux_text={1: proof(text)})
    assert len(text) > 4096
    assert menu.values[1] == text
    assert menu.menu.candidate(1).value != text
    assert "TRUNCATED SDK VALUE" not in repr(menu)
    assert menu.menu.candidate(1).input_type == "textarea"


def test_empty_linux_qualification_preserves_synthetic_mac_snapshot():
    state = snapshot(element(role="AXTextArea", value="mac text  \n"), app_name="TextEdit")
    assert native.menu_from_snapshot(state, linux_text={}) == native.menu_from_snapshot(state)


def test_linux_exclusive_hotkey_has_exact_scope_and_no_mac_foreground_tracking(monkeypatch):
    driver = Driver()
    target = bridge(driver, mode="exclusive_desktop")
    menu = bound_text(target)

    def forbidden(*_args, **_kwargs):
        pytest.fail("Linux exclusive input must not invoke Mac foreground or restoration")

    monkeypatch.setattr(target, "_front_and_key", forbidden)
    monkeypatch.setattr(target.policy, "before_foreground", forbidden)
    monkeypatch.setattr(target.policy, "after_foreground", forbidden)
    result = asyncio.run(target.hotkey(menu, ["ctrl", "a"]))
    assert driver.calls == [("hotkey", {
        "keys": ["ctrl", "a"], "pid": 31, "window_id": 73,
        "delivery_mode": "foreground", "session": "linux-test-session",
    })]
    assert result.delivery == result.driver_delivery == "foreground"
    assert result.delivered_count == 1
    assert result.effect == "unverifiable"
    assert not result.foreground
    assert target.policy.foreground_log == []
    assert target.last is None


@pytest.mark.parametrize("mode,code", [
    ("background_only", "requires_foreground"),
    ("foreground_permitted", "platform_posture_unavailable"),
])
def test_linux_hotkey_refused_without_exclusive_posture(mode, code):
    target = bridge(mode=mode)
    result = asyncio.run(target.hotkey(bound_text(target), ["ctrl", "a"]))
    assert result.effect == "refused" and result.error_code == code
    assert result.dispatched is False
    assert target.driver.calls == []


def test_linux_menu_uses_background_scoped_sdk_without_mac_activation(monkeypatch):
    target = bridge()

    def forbidden(*_args, **_kwargs):
        pytest.fail("Linux menu must not use the Mac foreground path")

    monkeypatch.setattr(target, "_front_and_key", forbidden)
    result = asyncio.run(target.menu(bound_text(target), ["File", "Open"]))
    assert target.driver.calls == [("invoke_menu", {
        "pid": 31, "window_id": 73, "path": ["File", "Open"], "session": "linux-test-session",
    })]
    assert result.delivery == result.driver_delivery == "background"
    assert result.effect == "unverifiable"
    assert not result.foreground


def test_linux_menu_uncertain_dispatch_is_not_retried():
    target = bridge()
    target.driver.failure = TimeoutError("reply lost after menu dispatch")
    result = asyncio.run(target.menu(bound_text(target), ["File", "Open"]))
    assert result.effect == "unverifiable" and result.dispatched
    assert result.delivered_count is None
    assert len(target.driver.calls) == 1


@pytest.mark.parametrize("new_value,writable", [("concurrent edit", True), ("old ", True), ("old", False)])
def test_linux_type_refuses_changed_or_readonly_field_without_write(new_value, writable):
    ax = ExactAX({1: new_value}, {1: {"readable": True, "writable": writable, "multiline": True}})
    target = bridge(ax=ax)
    result = asyncio.run(target.act(bound_text(target), "type", 1, "replacement"))
    assert result.effect == "refused" and not result.dispatched
    assert result.error_code == "precondition_changed"
    assert ax.writes == target.driver.calls == []


@pytest.mark.parametrize("corrupt,effect", [(False, "confirmed"), (True, "partial")])
def test_linux_type_compares_complete_exact_readback(corrupt, effect):
    ax = ExactAX()
    if corrupt:
        ax.corrupt = str.rstrip
    target = bridge(ax=ax)
    text = "replacement α\n\t  "
    result = asyncio.run(target.act(bound_text(target), "type", 1, text))
    assert result.effect == effect
    assert result.delivered_count == 1
    assert result.delivery_basis == "ax_set_value_ack"
    assert ax.writes == [(1, text)]
    assert target.driver.calls == []


def test_linux_type_lost_ack_is_uncertain_and_never_retried():
    ax = ExactAX()
    ax.write_error = AXError("reply_lost", "the write may have landed")
    target = bridge(ax=ax)
    menu = bound_text(target)
    result = asyncio.run(target.act(menu, "type", 1, "replacement"))
    assert result.effect == "unverifiable" and result.dispatched
    assert result.delivered_count is None
    assert ax.writes == [(1, "replacement")]
    assert ax.values[1] == "replacement"
    assert target.driver.calls == []
    with pytest.raises(native.NativeBridgeError) as exc:
        asyncio.run(target.act(menu, "type", 1, "replacement"))
    assert exc.value.reason == "stale"
    assert len(ax.writes) == 1


def test_linux_save_shortcut_preserves_control_and_super_meanings():
    assert native.is_save(["ctrl", "s"])
    assert native.is_save(["CONTROL", "S"])
    assert not native.is_save(["cmd", "s"])
    assert not native.is_save(["command", "s"])
    assert not native.is_save(["ctrl", "shift", "s"])
    assert native.is_save(path=["File", "Save"])
