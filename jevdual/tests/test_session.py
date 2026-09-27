"""The footwork session's receipts (python/jevdual/session.py), without a Driver."""

from __future__ import annotations

import dataclasses
import json
from types import SimpleNamespace

from jevdual.menu import Candidate, Menu
from jevdual.session import SessionState, receipt_for


def _nm(cands, title="page", page_text=""):
    menu = Menu(url="app://X", title=title, page_text=page_text, candidates=tuple(cands), by_operation={})
    return SimpleNamespace(menu=menu, snapshot_id="s2", app_name="X")


def _state(tmp_path, cands, pending):
    st = SessionState(dir=str(tmp_path), app="X", pid=1, window_id=2, task="t")
    st.remember(_nm(cands))
    st.pending = pending
    return st


def _field(id, label, value=None, **kw):
    return Candidate(id=id, label=label, role="textbox", operations=("type",), value=value, **kw)


def test_type_receipt_follows_the_field_not_the_element_count(tmp_path):
    before = [_field(4, "Search Wikipedia")]
    pend = {
        "line": "type(Search Wikipedia)",
        "driver_effect": "unverifiable",
        "op": "type",
        "target_id": 4,
        "target_label": "Search Wikipedia",
        "intended": "Dune novel",
        "secret": False,
    }
    st = _state(tmp_path, before, pend)
    # 49 suggestion links appeared, but the field is still empty: that is a no-op, whatever the diff says
    after = [_field(4, "Search Wikipedia", value=None)] + [
        Candidate(id=100 + i, label=f"suggestion {i}", role="link", operations=("click",)) for i in range(49)
    ]
    r = receipt_for(st, _nm(after))
    assert r["effect"] == "suspected_noop" and "holds ''" in r["evidence"] and "Dune novel" in r["evidence"]
    # the field holds the text (the id renumbered, the label did not): confirmed, naming the value
    after = [_field(5, "Search Wikipedia", value="Dune novel")]
    r = receipt_for(st, _nm(after))
    assert r["effect"] == "confirmed" and r["evidence"] == "'Search Wikipedia' now holds 'Dune novel'"


def test_secret_and_password_receipts_never_show_the_value(tmp_path):
    before = [_field(1, "Password", input_type="password")]
    pend = {
        "line": "type(Password)",
        "driver_effect": "unverifiable",
        "op": "type",
        "target_id": 1,
        "target_label": "Password",
        "intended": None,
        "secret": True,
    }
    st = _state(tmp_path, before, pend)
    r = receipt_for(st, _nm([_field(1, "Password", input_type="password", has_value=True)]))
    # a password field says only that it holds something: unverifiable, not confirmed (package A2)
    assert r["effect"] == "unverifiable" and "hunter" not in r["text"] and "a value" in r["evidence"]
    r = receipt_for(st, _nm([_field(1, "Password", input_type="password", has_value=False)]))
    assert r["effect"] == "suspected_noop" and "{secret}" in r["evidence"]


def test_click_receipts_are_untouched_and_missing_fields_are_unverifiable(tmp_path):
    before = [Candidate(id=7, label="Go", role="button", operations=("click",))]
    pend = {
        "line": "click(Go)",
        "driver_effect": "unverifiable",
        "op": "click",
        "target_id": 7,
        "target_label": "Go",
    }
    st = _state(tmp_path, before, pend)
    r = receipt_for(st, _nm([Candidate(id=7, label="Go", role="button", operations=("click",))]))
    assert r["effect"] == "suspected_noop"
    pend = {
        "line": "type(Name)",
        "driver_effect": "unverifiable",
        "op": "type",
        "target_id": 3,
        "target_label": "Name",
        "intended": "Ada",
        "secret": False,
    }
    st = _state(tmp_path, [_field(3, "Name")], pend)
    r = receipt_for(st, _nm([Candidate(id=9, label="Done", role="button", operations=("click",))]))
    assert r["effect"] == "unverifiable" and "not on the fresh observation" in r["evidence"]


def test_browser_replace_typing_asks_the_posture_and_never_keystrokes():
    """footwork-9c's tab probe (2026-09-25): browser_type selects the bound tab for ~100 ms in every
    mode but insert_text with replace=false. Inserting into an empty field or appending stays
    background; replacing held text is a foreground step and a background_only bridge refuses it."""
    import asyncio
    import json

    from jevdual.browser_driver import BrowserBridge, WebMenu
    from jevdual.posture import ExecutionPolicy

    calls = []

    class Driver:
        async def call_tool(self, name, args):
            calls.append((name, json.loads(args)))
            return SimpleNamespace(structured_json='{"status":"ok"}', text="typed", is_error=False)

    def menu(value):
        c = Candidate(id=1, label="Name", role="textbox", operations=("type",), value=value)
        return WebMenu(
            menu=Menu(url="u", title="t", page_text="", candidates=(c,), by_operation={}),
            snapshot_id="p1",
            refs={1: "p1:1"},
        )

    b = BrowserBridge(Driver(), 1, 2, policy=ExecutionPolicy("background_only"))
    b.target_id, b.tab_id = "bt", "tab"
    nm = menu(None)
    b.last = nm
    eff = asyncio.run(b.act(nm, "type", 1, "Ada"))
    assert (
        eff.effect != "refused" and calls[-1][1]["mode"] == "insert_text" and calls[-1][1]["replace"] is False
    )
    nm = menu("Old")
    b.last = nm
    eff = asyncio.run(b.act(nm, "append", 1, " more"))
    assert calls[-1][1]["replace"] is False
    b.last = nm
    eff = asyncio.run(b.act(nm, "type", 1, "New"))
    assert eff.effect == "refused" and eff.error_code == "requires_foreground" and eff.dispatched is False
    assert "100 ms" in eff.summary and len(calls) == 2  # nothing reached the browser
    b2 = BrowserBridge(Driver(), 1, 2, policy=ExecutionPolicy("exclusive_desktop"))
    b2.target_id, b2.tab_id = "bt", "tab"
    b2.last = nm
    eff = asyncio.run(b2.act(nm, "type", 1, "New"))
    assert (
        eff.effect != "refused" and calls[-1][1]["replace"] is True and calls[-1][1]["mode"] == "insert_text"
    )


def _append_pending(**kw):
    return {
        "line": "append(text area)",
        "driver_effect": "confirmed",
        "op": "append",
        "target_id": 1,
        "target_label": "text area",
        "intended": "£51.77",
        "secret": False,
    } | kw


def test_native_append_after_a_stripped_trailing_newline_is_confirmed(tmp_path):
    """G1 pilot: the file ended with a newline the Driver strips, the bridge appended no separator, and
    the receipt said partial on a correct append."""
    st = _state(tmp_path, [_field(1, "text area", value="Price:")], _append_pending())
    r = receipt_for(st, _nm([_field(1, "text area", value="Price:\n£51.77")]))
    assert r is not None and r["effect"] == "confirmed", r


def test_browser_append_keeps_the_exact_rule(tmp_path):
    st = _state(tmp_path, [_field(1, "text area", value="Price:")], _append_pending(mode="browser"))
    r = receipt_for(st, _nm([_field(1, "text area", value="Price:\n£51.77")]))
    assert r is not None and r["effect"] == "partial", r


def test_a_save_is_confirmed_only_by_the_file_on_disk(tmp_path):
    cands = [_field(1, "text area", value="x")]
    for rb, effect in (
        (
            {"ok": True, "path": "/f", "detail": "/f holds the window's text exactly (5 characters)"},
            "confirmed",
        ),
        (
            {"ok": False, "path": "/f", "detail": "/f differs from the window's text at character 3"},
            "partial",
        ),
        ({"ok": None, "detail": "the window names no file (unsaved document)"}, "unverifiable"),
    ):
        pend = {"line": "hotkey(cmd+s)", "driver_effect": "unverifiable", "op": "hotkey", "save_readback": rb}
        r = receipt_for(_state(tmp_path, cands, pend), _nm(cands))
        assert r is not None and r["effect"] == effect and rb["detail"] in r["evidence"], r


def test_save_readback_compares_the_disk_with_the_window(tmp_path):
    from types import SimpleNamespace

    from jevdual.native import NativeEffect, is_save, save_readback, with_save_readback

    f = tmp_path / "t.txt"
    f.write_text("a\nb")
    ax = SimpleNamespace(document_path=lambda pid, wid: str(f), text_area_values=lambda pid, wid: ["a\nb"])
    rb = save_readback(ax, 1, 2)
    assert rb["ok"] is True
    eff = with_save_readback(NativeEffect("hotkey", -1, "cmd+s", "unverifiable"), rb)
    assert eff.effect == "confirmed" and "saved: " in eff.summary and eff.readback == rb
    ax.text_area_values = lambda pid, wid: ["a\nc"]
    rb = save_readback(ax, 1, 2)
    assert rb["ok"] is False and "character 2" in rb["detail"]
    assert with_save_readback(NativeEffect("menu", -1, "File > Save", "unverifiable"), rb).effect == "partial"
    ax.document_path = lambda pid, wid: None
    rb = save_readback(ax, 1, 2)
    assert (
        rb["ok"] is None
        and with_save_readback(NativeEffect("m", -1, "x", "confirmed"), rb).effect == "unverifiable"
    )
    assert is_save(keys=["cmd", "s"]) and is_save(path=["File", "Save"])
    assert not is_save(keys=["cmd", "shift", "s"]) and not is_save(path=["File", "Save As…"])


def test_no_screenshot_is_written_while_the_session_holds_a_secret(tmp_path, monkeypatch):
    """Secondary audit 2026-09-27: the screenshot was written before the observation was scrubbed, so a
    named secret shown in an ordinary field could persist in the image. Pixels cannot be scrubbed, so
    no screenshot is captured once the session holds a secret."""
    import asyncio

    from jevdual.session import observe

    asked: list[object] = []

    class Bridge:
        async def observe(self, *, screenshot_path=None):
            asked.append(screenshot_path)
            return _nm([_field(1, "API key", value="s3cr3t-value")])

    st = SessionState(dir=str(tmp_path), app="X", pid=1, window_id=2, task="t")
    asyncio.run(observe(st, Bridge()))
    assert asked[-1] is not None  # no secret yet: the audit screenshot is kept
    monkeypatch.setenv("FOOTWORK_SECRET_KEY", "s3cr3t-value")
    st.secret_names.append("KEY")
    nm, _ = asyncio.run(observe(st, Bridge()))
    assert asked[-1] is None
    assert "s3cr3t-value" not in json.dumps(dataclasses.asdict(nm.menu), default=str)
    assert "screenshot withheld" in (tmp_path / "session.jsonl").read_text()
