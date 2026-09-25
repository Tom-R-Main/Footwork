"""Native menu builder and bridge over a recorded Cua Driver snapshot (macOS Calculator)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from jevdual.native import (
    NativeBridge,
    NativeBridgeError,
    NativeEffect,
    effect_from_action_result,
    menu_from_snapshot,
)

FIXTURE = Path(__file__).parent / "fixtures" / "native" / "calculator.json"


@pytest.fixture(scope="module")
def snapshot() -> dict:
    return json.loads(FIXTURE.read_text())


def test_menu_excludes_menu_bar_and_window_by_default(snapshot):
    nm = menu_from_snapshot(snapshot)
    assert nm.snapshot_id == "s00000001"
    assert nm.app_name == "Calculator"
    assert nm.menu.url == "app://Calculator"
    roles = {c.role for c in nm.menu.candidates}
    assert "menuitem" not in roles and "menubar" not in roles
    assert nm.menu.omitted["menu_bar"] > 100
    assert all(c.role != "window" for c in nm.menu.candidates)
    # every candidate has a token and the token names the snapshot
    assert set(nm.tokens) == {c.id for c in nm.menu.candidates}
    assert all(t.startswith("s00000001:") for t in nm.tokens.values())


def test_buttons_are_click_candidates_with_labels(snapshot):
    nm = menu_from_snapshot(snapshot)
    labels = {c.label: c for c in nm.menu.candidates}
    for name in ("All Clear", "6", "Multiply", "7", "Equals"):
        assert name in labels, name
        assert labels[name].role == "button"
        assert labels[name].operations == ("click",)
    assert nm.menu.by_operation["click"]


def test_page_text_is_the_display_static_text(snapshot):
    nm = menu_from_snapshot(snapshot)
    # invisible direction marks are stripped; the display shows the expression and the result
    assert "‎" not in nm.menu.page_text
    assert "1,248" in nm.menu.page_text
    assert "584+664" in nm.menu.page_text


def test_include_menu_bar_adds_menu_items(snapshot):
    nm = menu_from_snapshot(snapshot, include_menu_bar=True)
    items = [c for c in nm.menu.candidates if c.role == "menuitem"]
    assert items and all("click" in c.operations for c in items)
    assert any(c.section for c in items)  # menu items carry their menu as section


def test_incomplete_snapshot_is_reported_in_omitted(snapshot):
    nm = menu_from_snapshot(snapshot)
    assert nm.elements_complete is False
    assert nm.menu.omitted.get("elements_incomplete") == 1


def test_text_field_mapping_and_sensitive_value():
    snap = {
        "snapshot_id": "s0000000a",
        "pid": 1,
        "window_id": 2,
        "app_name": "Demo",
        "window_title": "Sign in",
        "elements_complete": True,
        "tree_markdown": '- [0] AXWindow "Sign in"\n    - AXStaticText = "Welcome back"\n',
        "elements": [
            {
                "element_index": 0,
                "element_token": "s0000000a:0",
                "role": "AXWindow",
                "label": "Sign in",
                "actions": ["AXRaise"],
            },
            {
                "element_index": 1,
                "element_token": "s0000000a:1",
                "role": "AXGroup",
                "label": "Credentials",
                "parent_index": 0,
            },
            {
                "element_index": 2,
                "element_token": "s0000000a:2",
                "role": "AXTextField",
                "label": "Username",
                "value": "tom",
                "parent_index": 1,
                "enabled": True,
            },
            {
                "element_index": 3,
                "element_token": "s0000000a:3",
                "role": "AXSecureTextField",
                "label": "Password",
                "value": "hunter2",
                "parent_index": 1,
                "enabled": True,
            },
            {
                "element_index": 4,
                "element_token": "s0000000a:4",
                "role": "AXCheckBox",
                "label": "Remember me",
                "value": "1",
                "parent_index": 1,
                "actions": ["AXPress"],
            },
            {
                "element_index": 5,
                "element_token": "s0000000a:5",
                "role": "AXButton",
                "label": "Sign In",
                "parent_index": 0,
                "actions": ["AXPress"],
                "enabled": False,
            },
            {
                "element_index": 6,
                "element_token": "s0000000a:6",
                "role": "AXStaticText",
                "label": "footer",
                "parent_index": 0,
                "actions": [],
            },
        ],
    }
    nm = menu_from_snapshot(snap)
    by = {c.label: c for c in nm.menu.candidates}
    assert by["Username"].role == "textbox" and by["Username"].value == "tom"
    assert by["Username"].operations == ("type", "enter")
    assert by["Username"].section == "Credentials"
    assert by["Password"].value is None and by["Password"].input_type == "password"
    assert by["Remember me"].checked is True
    assert "Sign In" not in by and nm.menu.omitted["disabled"] == 1
    assert "footer" not in by and nm.menu.omitted["unmapped_role"] == 2  # footer and the AXGroup
    assert nm.menu.page_text == "Welcome back\ntom"  # static text, then text-field values
    assert set(nm.menu.by_operation) == {"type", "enter", "click"}


def test_effect_from_action_result_reads_driver_words():
    ev = SimpleNamespace(kind=SimpleNamespace(name="VALUE_READBACK"), detail="value read back as 42")
    action = SimpleNamespace(
        effect=SimpleNamespace(name="CONFIRMED"),
        route=SimpleNamespace(name="ACCESSIBILITY"),
        evidence=[ev],
        summary="Pressed 6",
    )
    eff = effect_from_action_result("click", 11, "6", action)
    assert eff.effect == "confirmed" and eff.route == "accessibility" and eff.ok
    assert eff.evidence == ("value_readback: value read back as 42",)
    wrapped = SimpleNamespace(action=action, text="ok", is_error=False, error_code=None)
    assert effect_from_action_result("type", 2, "Username", wrapped).effect == "confirmed"
    bad = SimpleNamespace(action=None, text="nope", is_error=True, error_code="background_unavailable")
    eff = effect_from_action_result("click", 1, "x", bad)
    assert eff.effect == "refused" and not eff.ok and eff.error_code == "background_unavailable"


class _FakeDriver:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.calls: list[tuple[str, object]] = []

    async def get_window_state(self, inp):
        self.calls.append(("get_window_state", inp))
        return self.snapshot

    async def click(self, inp):
        self.calls.append(("click", inp))
        return SimpleNamespace(
            effect=SimpleNamespace(name="CONFIRMED"),
            route=SimpleNamespace(name="ACCESSIBILITY"),
            evidence=None,
            summary="pressed",
        )

    async def call_tool(self, name, args_json):
        self.calls.append((name, json.loads(args_json)))
        return SimpleNamespace(
            action=SimpleNamespace(
                effect=SimpleNamespace(name="CONFIRMED"),
                route=SimpleNamespace(name="ACCESSIBILITY"),
                evidence=None,
                summary="set",
            ),
            text="",
            is_error=False,
            error_code=None,
        )


def test_bridge_refuses_stale_menu_and_dispatches_by_token(snapshot, monkeypatch):
    from jevdual import native

    fake = _FakeDriver(snapshot)
    bridge = NativeBridge(fake, pid=snapshot["pid"], window_id=snapshot["window_id"])
    # stub the SDK types the bridge imports lazily
    import sys

    stub = SimpleNamespace(
        GetWindowStateInput=lambda **kw: kw,
        ClickInput=lambda **kw: kw,
        ClickPosition=SimpleNamespace(ELEMENT=lambda element_token: ("element", element_token)),
        InputDeliveryMode=SimpleNamespace(BACKGROUND="background", FOREGROUND="foreground"),
        ActionTarget=SimpleNamespace(WINDOW=lambda pid, window_id: ("window", pid, window_id)),
    )
    monkeypatch.setitem(sys.modules, "cua_driver", stub)

    nm = asyncio.run(bridge.observe())
    six = next(c for c in nm.menu.candidates if c.label == "6")
    eff = asyncio.run(bridge.act(nm, "click", six.id))
    assert isinstance(eff, NativeEffect) and eff.effect == "confirmed" and eff.label == "6"
    name, inp = fake.calls[-1]
    assert (
        name == "click"
        and inp["position"] == ("element", nm.tokens[six.id])
        and inp["delivery_mode"] == "background"
    )
    # a second act on the same snapshot is stale until reobserved
    with pytest.raises(NativeBridgeError) as e:
        asyncio.run(bridge.act(nm, "click", six.id))
    assert e.value.reason == "stale"
    nm2 = asyncio.run(bridge.observe())
    with pytest.raises(NativeBridgeError) as e:
        asyncio.run(bridge.act(nm2, "type", six.id, "x"))
    assert e.value.reason == "unknown_operation"
    assert native.menu_from_snapshot(snapshot).snapshot_id == nm2.snapshot_id


def test_bridge_menu_and_hotkey_go_foreground_and_record_it(snapshot, monkeypatch):
    import sys

    calls = []

    class D(_FakeDriver):
        async def call_tool(self, name, args_json):
            calls.append((name, json.loads(args_json)))
            return SimpleNamespace(
                action=SimpleNamespace(
                    effect=SimpleNamespace(name="UNVERIFIABLE"),
                    route=SimpleNamespace(name="SYNTHETIC_EVENTS"),
                    evidence=None,
                    summary="chord",
                ),
                text="",
                is_error=False,
                error_code=None,
            )

        async def invoke_menu(self, inp):
            calls.append(("invoke_menu", inp))
            return SimpleNamespace(
                action=SimpleNamespace(
                    effect=SimpleNamespace(name="CONFIRMED"),
                    route=SimpleNamespace(name="ACCESSIBILITY"),
                    evidence=None,
                    summary="File > Save",
                ),
                text="",
                is_error=False,
                error_code=None,
            )

    stub = SimpleNamespace(
        GetWindowStateInput=lambda **kw: kw,
        InvokeMenuInput=lambda **kw: kw,
        HotkeyInput=lambda **kw: kw,
        ActionTarget=SimpleNamespace(WINDOW=lambda pid, window_id: ("window", pid, window_id)),
    )
    monkeypatch.setitem(sys.modules, "cua_driver", stub)
    bridge = NativeBridge(D(snapshot), pid=1, window_id=2)
    nm = asyncio.run(bridge.observe())
    eff = asyncio.run(bridge.menu(nm, ["File", "Save"]))
    assert eff.effect == "confirmed" and eff.summary.startswith("foreground")
    assert (
        calls[0][0] == "bring_to_front"
        and calls[1][0] == "invoke_menu"
        and calls[1][1]["path"] == ["File", "Save"]
    )
    with pytest.raises(NativeBridgeError):  # one action per snapshot
        asyncio.run(bridge.menu(nm, ["File", "Save"]))
    nm = asyncio.run(bridge.observe())
    eff = asyncio.run(bridge.hotkey(nm, ["cmd", "s"]))
    assert eff.effect == "unverifiable" and eff.label == "cmd+s" and "foreground" in eff.summary


def test_page_text_reads_chrome_static_text_with_trailing_attribute_blocks():
    """P0 (2026-09-25): Chrome's markdown lines end in ``[actions=[...]]``; the old end-anchored regex
    captured no web text, so the verifier was blind on every web page."""
    from jevdual.native import _page_text

    md = (
        '- [1] AXWindow "Account - Apple Developer"\n'
        '    - [56] AXStaticText = "Team ID" [actions=[press,showmenu,scrolltovisible]]\n'
        '    - [57] AXStaticText = "2U5KQ6F79H"\n'
        "    - [66] AXStaticText [actions=[press]]\n"
        '    - [67] AXStaticText = "He said \\"yes\\"" [actions=[press]]\n'
    )
    text = _page_text(md, [], 6000)
    assert text.splitlines() == ["Team ID", "2U5KQ6F79H", 'He said "yes"']


def test_prune_drops_unnamed_and_duplicate_controls_and_caps():
    from jevdual.menu import Candidate, MenuBudget
    from jevdual.native import NATIVE_MENU_CAP, _prune

    def c(i, role, label, section=None):
        return Candidate(id=i, label=label, role=role, operations=("click",), section=section)

    cands = [c(1, "button", "button"), c(2, "button", "More actions"), c(3, "button", "More actions")]
    cands += [c(4, "button", "More actions", "Row 2"), c(5, "textbox", "textbox")]
    cands += [c(100 + i, "link", f"link {i}") for i in range(NATIVE_MENU_CAP + 5)]
    tokens = {x.id: f"t{x.id}" for x in cands}
    frames = {x.id: (0.0, 0.0, 1.0, 1.0) for x in cands}
    om: dict[str, int] = {}
    kept, tok, fr = _prune(cands, tokens, frames, om, MenuBudget())
    ids = [x.id for x in kept]
    assert 1 not in ids and om["unnamed"] == 1  # a button called 'button' offers nothing to choose on
    assert 2 in ids and 3 not in ids and 4 in ids and om["duplicate"] == 1  # same section repeats drop
    assert 5 in ids  # a text field keeps its role-name label (the value is the content)
    assert len(kept) == NATIVE_MENU_CAP and om["cap"] == 8  # 168 kept before the cap
    assert set(tok) == set(ids) and set(fr) == set(ids)
