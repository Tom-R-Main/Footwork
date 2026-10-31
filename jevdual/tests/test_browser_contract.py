"""The browser bridge's wire requests and effects, pinned across the L1b adapter change (LBC1).

The replies follow the vendored CUA constructors at d5373879: every structured browser reply is
``{"status": "ok" | "refused", ...}``; a refusal is ``{"status": "refused", "refusal": {code, message,
detail?}}`` (cua-driver-core/src/browser/refusal.rs); an acknowledged trusted click whose focus
emulation could not be restored refuses with ``detail = {"delivery": "unknown", "retryable": false}``
(browser/tools.rs); the recovery-hint layer adds top-level ``hint`` and ``next_call``
(recovery_hint.rs).
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest
from jevdual import browser_driver, cli
from jevdual.browser_driver import BrowserBridge
from jevdual.posture import ExecutionPolicy

URL = "https://example.invalid/form"

BOUND = {
    "status": "ok",
    "target_id": "target-1",
    "tabs": [{"tab_id": "tab-1", "active": True, "url": URL}],
}
SNAPSHOT = {
    "status": "ok",
    "page": {"url": URL, "title": "Form"},
    "snapshot": {"id": "snap-1", "complete": True},
    "refs": [
        {"ref": "snap-1:1", "role": "button", "name": "Continue", "actions": ["click"]},
        {"ref": "snap-1:2", "role": "textbox", "name": "Name", "actions": ["type"], "value": "Ada"},
        {"ref": "snap-1:3", "role": "textbox", "name": "Note", "actions": ["type"]},
    ],
    "content_refs": [{"role": "paragraph", "name": "Fill the form"}],
}
UNKNOWN_DELIVERY = {
    "status": "refused",
    "refusal": {
        "code": "browser_input_trust_unavailable",
        "message": "trusted click was acknowledged but CDP focus emulation could not be restored (closed); "
        "delivery is unknown and must not be retried automatically",
        "detail": {"delivery": "unknown", "retryable": False},
    },
    "hint": "Observe the page before deciding whether the click happened.",
    "next_call": {"tool": "get_browser_state", "arguments": {"target_id": "target-1"}},
}


class Wire:
    """The CUA browser tools as the bridge reaches them: ``call_tool(name, json) -> ToolResult``."""

    def __init__(self, replies: dict[str, dict] | None = None, *, text: str = "done") -> None:
        self.calls: list[tuple[str, dict]] = []
        self.replies = replies or {}
        self.text = text

    async def call_tool(self, name, args_json):
        args = json.loads(args_json)
        self.calls.append((name, args))
        if name in self.replies:
            reply = self.replies[name]
        elif name == "browser_prepare":
            reply = {"status": "ok"}
        elif name == "get_browser_state":
            reply = SNAPSHOT if "tab_id" in args else BOUND
        else:
            reply = {"status": "ok", "target_id": args.get("target_id"), "tab_id": args.get("tab_id")}
        error = reply.get("status") == "refused"
        text = f"refused ({reply['refusal']['code']}): {reply['refusal']['message']}" if error else self.text
        return SimpleNamespace(structured_json=json.dumps(reply), text=text, is_error=False)

    async def list_windows(self, _):
        window = SimpleNamespace(pid=42, window_id=7, bounds=SimpleNamespace(width=100, height=100))
        return SimpleNamespace(windows=[window])

    async def shutdown(self):
        pass


def _effect(e) -> tuple:
    return (e.operation, e.target, e.label, e.effect, e.route, e.evidence, e.summary, e.error_code, e.dispatched)


def _bridge(wire, posture="exclusive_desktop") -> BrowserBridge:
    return BrowserBridge(wire, 42, 7, policy=ExecutionPolicy(posture))


def test_every_operation_sends_the_same_wire_request():
    wire = Wire()

    async def run():
        b = _bridge(wire)
        await b.attach()
        effects = []
        nm = await b.observe()
        effects.append(await b.act(nm, "click", 1))
        nm = await b.observe()
        effects.append(await b.act(nm, "click", 1, route="trusted"))
        nm = await b.observe()
        effects.append(await b.act(nm, "type", 3, "Grace"))
        nm = await b.observe()
        effects.append(await b.act(nm, "append", 2, " Lovelace"))
        nm = await b.observe()
        effects.append(await b.act(nm, "type", 2, "Grace"))  # replaces held text
        effects.append(await b.navigate("https://example.invalid/next"))
        return effects

    effects = asyncio.run(run())
    s = {"session": "footwork"}
    tab = {"target_id": "target-1", "tab_id": "tab-1"}
    state = ("get_browser_state", {**s, **tab, "snapshot_format": "semantic_v2"})
    assert wire.calls == [
        ("browser_prepare", {**s, "pid": 42, "window_id": 7, "strategy": {"kind": "existing_profile"}}),
        ("get_browser_state", {**s, "pid": 42, "window_id": 7}),
        state,
        ("browser_click", {**s, **tab, "ref": "snap-1:1", "input_route": "dom_event"}),
        state,
        ("browser_click", {**s, **tab, "ref": "snap-1:1", "input_route": "trusted"}),
        state,
        ("browser_type", {**s, **tab, "ref": "snap-1:3", "text": "Grace", "mode": "insert_text", "replace": False}),
        state,
        ("browser_type", {**s, **tab, "ref": "snap-1:2", "text": " Lovelace", "mode": "insert_text",
                          "replace": False}),
        state,
        ("browser_type", {**s, **tab, "ref": "snap-1:2", "text": "Grace", "mode": "insert_text", "replace": True}),
        ("browser_navigate", {**s, **tab, "url": "https://example.invalid/next"}),
    ]
    assert [_effect(e) for e in effects] == [
        ("click", 1, "Continue", "unverifiable", "dom_event", (), "done", None, True),
        ("click", 1, "Continue", "unverifiable", "trusted", (), "done", None, True),
        ("type", 3, "Note", "unverifiable", "cdp", (), "done", None, True),
        ("append", 2, "Name", "unverifiable", "cdp", (), "done", None, True),
        ("type", 2, "Name", "unverifiable", "cdp", (), "done", None, True),
        ("navigate", -1, "https://example.invalid/next", "unverifiable", "cdp", (), "done", None, True),
    ]


def test_observation_projects_the_semantic_reply_unchanged():
    async def run():
        b = _bridge(Wire())
        await b.attach()
        return b, await b.observe()

    b, nm = asyncio.run(run())
    assert (b.target_id, b.tab_id) == ("target-1", "tab-1")
    assert nm.snapshot_id == "snap-1" and nm.refs == {1: "snap-1:1", 2: "snap-1:2", 3: "snap-1:3"}
    assert (nm.page_url, nm.page_title, nm.values, nm.elements_complete) == (URL, "Form", {2: "Ada"}, True)
    assert [(c.id, c.label, c.role, c.operations) for c in nm.menu.candidates] == [
        (1, "Continue", "button", ("click",)),
        (2, "Name", "textbox", ("type",)),
        (3, "Note", "textbox", ("type",)),
    ]
    assert nm.menu.page_text == "Fill the form\nAda"


def test_a_refusal_keeps_its_code_and_message_and_stays_dispatched():
    refused = {
        "status": "refused",
        "refusal": {"code": "browser_action_unavailable", "message": "the ref is stale"},
    }

    async def run():
        b = _bridge(Wire({"browser_click": refused}))
        await b.attach()
        nm = await b.observe()
        return await b.act(nm, "click", 1)

    eff = asyncio.run(run())
    assert _effect(eff) == (
        "click", 1, "Continue", "refused", "dom_event", (), "the ref is stale", "browser_action_unavailable", True
    )


def test_an_acknowledged_click_with_unknown_delivery_is_never_reported_as_not_sent():
    async def run():
        b = _bridge(Wire({"browser_click": UNKNOWN_DELIVERY}))
        await b.attach()
        nm = await b.observe()
        return await b.act(nm, "click", 1, route="trusted")

    eff = asyncio.run(run())
    assert eff.effect == "refused" and eff.dispatched is True
    assert eff.error_code == "browser_input_trust_unavailable"
    assert eff.summary == UNKNOWN_DELIVERY["refusal"]["message"][:200]


def test_a_posture_refusal_sends_nothing():
    wire = Wire()

    async def run():
        b = _bridge(wire, "background_only")
        await b.attach()
        nm = await b.observe()
        return await b.act(nm, "type", 2, "Grace")

    eff = asyncio.run(run())
    assert eff.effect == "refused" and eff.dispatched is False and eff.error_code == "requires_foreground"
    assert [name for name, _ in wire.calls] == ["browser_prepare", "get_browser_state", "get_browser_state"]


@pytest.mark.parametrize(
    ("name", "reply", "message"),
    [
        ("browser_prepare", {"status": "refused", "refusal": {"code": "browser_requires_setup", "message": "no"}},
         "browser_prepare refused: no"),
        ("get_browser_state", {"status": "refused", "refusal": {"code": "browser_binding_ambiguous",
                                                                "message": "two"}}, "bind refused: two"),
    ],
)
def test_attach_refusals_raise_before_any_input(name, reply, message):
    wire = Wire({name: reply})
    with pytest.raises(RuntimeError) as exc:
        asyncio.run(_bridge(wire).attach())
    assert str(exc.value) == message
    assert all(n in ("browser_prepare", "get_browser_state") for n, _ in wire.calls)


def test_an_unparseable_reply_reads_as_an_unverifiable_effect():
    class Garbled(Wire):
        async def call_tool(self, name, args_json):
            result = await super().call_tool(name, args_json)
            if name == "browser_click":
                return SimpleNamespace(structured_json="not json", text="clicked", is_error=False)
            return result

    async def run():
        b = _bridge(Garbled())
        await b.attach()
        nm = await b.observe()
        return await b.act(nm, "click", 1)

    assert asyncio.run(run()).effect == "unverifiable"


def test_the_session_reports_an_unknown_delivery_refusal_as_unverifiable(tmp_path, capsys, monkeypatch):
    """The command layer, not the bridge, decides what a dispatched refusal means for the person."""
    import jevdual.keys

    wire = Wire({"browser_click": UNKNOWN_DELIVERY})
    monkeypatch.setattr(browser_driver, "_begin_chrome", lambda *_: (42, None))
    monkeypatch.setattr(browser_driver, "chrome_pid", lambda: 42)
    monkeypatch.setattr(browser_driver, "_incarnation", lambda pid: 1.0)
    monkeypatch.setattr(browser_driver, "configured_driver", lambda pid: wire)
    monkeypatch.setattr(jevdual.keys, "load_keys", lambda *a, **k: {})
    session = str(tmp_path / "session")

    def fw(*argv):
        extra = ["--settle", "0"] if argv[0] == "do" else []
        code = cli.main([*argv, "--session", session, *extra])
        out = capsys.readouterr()
        return code, out.out, out.err

    code, out, err = fw("start", "Continue the form", "--browser")
    assert code == 0, err
    before = len(wire.calls)
    code, out, err = fw("do", "click", "1", "--no-judge", "--route", "trusted")
    clicks = [a for n, a in wire.calls[before:] if n == "browser_click"]
    assert len(clicks) == 1, (out, err)
    assert "driver says unverifiable" in out and "input outcome unknown" in out
    assert "not sent" not in out
