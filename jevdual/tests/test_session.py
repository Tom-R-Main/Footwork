"""The footwork session's receipts (python/jevdual/session.py), without a Driver."""

from __future__ import annotations

import dataclasses
import json
from types import SimpleNamespace

import pytest
from jevdual.menu import Candidate, Menu
from jevdual.session import SessionState, receipt_for


def test_projection_repair_retains_valid_records_after_damaged_middle_and_quarantines_bytes(tmp_path):
    import json

    from jevdual.session import _repair_projection_log

    state = SessionState(
        dir=str(tmp_path),
        app="fixture",
        pid=77,
        window_id=3,
        task="observe",
        authority=str(tmp_path / "authority.sqlite"),
    )
    original = b'{"kind":"first"}\n{"interrupted":\n{"kind":"receipt","effect":"unverifiable"}\n'
    log = tmp_path / "session.jsonl"
    log.write_bytes(original)
    _repair_projection_log(state)
    records = [json.loads(line) for line in log.read_bytes().splitlines()]
    assert records[:2] == [{"kind": "first"}, {"kind": "receipt", "effect": "unverifiable"}]
    repair = records[2]
    assert repair["kind"] == "projection_repair" and repair["damaged_lines"] == [2]
    assert (tmp_path / repair["quarantine"]).read_bytes() == original
    _repair_projection_log(state)
    assert len(list(tmp_path.glob("session.interrupted-*.jsonl"))) == 1


def test_projection_repair_separates_complete_record_when_terminal_newline_was_lost(tmp_path):
    import json

    from jevdual.session import _repair_projection_log

    state = SessionState(dir=str(tmp_path), app="fixture", pid=77, window_id=3, task="observe")
    log = tmp_path / "session.jsonl"
    original = b'{"kind":"do","operation_id":"finished"}'
    log.write_bytes(original)
    _repair_projection_log(state)
    state.log({"kind": "receipt", "effect": "confirmed"})
    first, repair, last = [json.loads(line) for line in log.read_bytes().splitlines()]
    assert first == {"kind": "do", "operation_id": "finished"}
    assert repair["missing_terminal_newline"] is True and repair["damaged_lines"] == []
    assert (tmp_path / repair["quarantine"]).read_bytes() == original
    assert last["kind"] == "receipt" and last["effect"] == "confirmed"


@pytest.mark.parametrize("value", [None, "", "x", "xy"])
def test_durable_bind_refuses_unavailable_prior_secret_before_driver_creation(tmp_path, monkeypatch, value):
    import asyncio

    import cua_driver
    from jevdual.native import NativeBridgeError
    from jevdual.session import bind

    state = SessionState(
        dir=str(tmp_path),
        app="X",
        pid=1,
        window_id=2,
        task="t",
        authority=str(tmp_path / "authority.sqlite"),
        secret_names=["FIXTURE"],
    )
    if value is None:
        monkeypatch.delenv("FOOTWORK_SECRET_FIXTURE", raising=False)
    else:
        monkeypatch.setenv("FOOTWORK_SECRET_FIXTURE", value)

    def unexpected_driver(**kwargs):
        raise AssertionError("unavailable-secret gate must run before driver creation")

    monkeypatch.setattr(cua_driver.CuaDriver, "create", staticmethod(unexpected_driver))
    with pytest.raises(NativeBridgeError) as stopped:
        asyncio.run(bind(state))
    assert stopped.value.reason == "secret_unavailable"


@pytest.mark.parametrize(("authority", "value"), [("authority.sqlite", "fixture-long-value"), ("", None)])
def test_bind_allows_restored_durable_secret_and_preserves_legacy_mode(
    tmp_path, monkeypatch, authority, value
):
    import asyncio

    import cua_driver
    from jevdual import session

    state = SessionState(
        dir=str(tmp_path),
        app="X",
        pid=1,
        window_id=2,
        task="t",
        authority=authority,
        secret_names=["FIXTURE"],
    )
    if value is None:
        monkeypatch.delenv("FOOTWORK_SECRET_FIXTURE", raising=False)
    else:
        monkeypatch.setenv("FOOTWORK_SECRET_FIXTURE", value)
    driver, bridge = object(), object()
    monkeypatch.setattr(cua_driver.CuaDriver, "create", staticmethod(lambda **kwargs: driver))
    monkeypatch.setattr(session, "_native_bridge", lambda *args: bridge)
    assert asyncio.run(session.bind(state)) == (driver, bridge)


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


def _exact_pending(tmp_path, value):
    binding = {"boot": "test", "pid": 77, "start": "start", "window_id": 3}
    state = SessionState(
        dir=str(tmp_path),
        app="Native fixture",
        pid=77,
        window_id=3,
        task="append",
        authority=str(tmp_path / "authority.sqlite"),
        session_id="session_one",
        native_binding=binding,
    )
    pending = {
        "operation_id": "op_one",
        "binding": binding,
        "observation": "decision",
        "execution_interval": {"start": 1.0, "end": 2.0},
        "target_id": 3,
        "target_label": "Body",
        "op": "append",
        "secret": False,
        "dispatched": True,
        "field_readback": {
            "schema_version": 1,
            "producer": {"name": "footwork.native", "version": 1},
            "predicate": "field_equals",
            "observed_value": value,
            "expected_value": value,
            "before_value": "Before",
            "matches": True,
            "complete": True,
            "target_id": 8,
            "label": "Body",
            "role": "AXTextArea",
            "frame": [10, 20, 400, 300],
            "snapshot_id": "revalidated",
            "decision_snapshot_id": "decision",
            "decision_target_id": 3,
        },
    }
    fresh = _nm([_field(8, "Body", value=value[:120])])
    fresh.ax_roles = {8: "AXTextArea"}
    fresh.frames = {8: (10, 20, 400, 300)}
    fresh.values = {8: value[:120]}
    return state, pending, fresh


def test_exact_readback_links_revalidated_target_without_using_projection_as_full_value(tmp_path):
    from jevdual.completion import effects
    from jevdual.session import _structured_receipt

    value = "Complete long value " * 30
    state, pending, fresh = _exact_pending(tmp_path, value)
    payload = _structured_receipt(state, pending, fresh)
    (item,) = effects([{"kind": "receipt", "action": pending, "structured_evidence": payload}])
    assert item.usable and item.values == (value,)
    assert payload["facts"][0]["parameters"]["source_observation"] == "revalidated"


def test_fresh_contradictory_projection_limits_earlier_exact_readback(tmp_path):
    from jevdual.completion import effects
    from jevdual.session import _structured_receipt

    state, pending, fresh = _exact_pending(tmp_path, "Expected exact field")
    fresh.values = {8: "Externally changed"}
    payload = _structured_receipt(state, pending, fresh)
    (item,) = effects([{"kind": "receipt", "action": pending, "structured_evidence": payload}])
    assert not item.usable and "contradicts" in item.limits[0]


def test_prior_secret_redaction_is_not_exact_literal_placeholder_evidence(tmp_path, monkeypatch):
    from jevdual.completion import effects
    from jevdual.session import _safe_field_readback, _structured_receipt

    value = "Previously secret phrase"
    monkeypatch.setenv("FOOTWORK_SECRET_OLD", value)
    state, pending, fresh = _exact_pending(tmp_path, value + "\nNew public text")
    state.secret_names = ["OLD"]
    pending["field_readback"] = _safe_field_readback(state, pending["field_readback"], None)
    readback = pending["field_readback"]
    assert readback["redacted"] and not readback["complete"] and readback["observed_value"] is None
    payload = _structured_receipt(state, pending, fresh)
    assert value not in json.dumps(payload) and value not in json.dumps(readback)
    assert effects([{"kind": "receipt", "action": pending, "structured_evidence": payload}]) == []


def test_durable_observation_records_projection_limits_and_generation(tmp_path):
    from jevdual.session import finish_observation

    state, _, fresh = _exact_pending(tmp_path, "Read value")
    fresh.elements_complete = False
    fresh.text_truncated = True
    finish_observation(state, fresh, observed_interval=(1.0, 2.0))
    record = json.loads((tmp_path / "session.jsonl").read_text().splitlines()[-1])
    assert record["kind"] == "observation" and record["generation"] == state.visual_generation
    assert record["coverage"]["text_truncated"] and not record["coverage"]["values_exact"]
    assert record["binding"] == state.native_binding and record["interval"] == {"start": 1.0, "end": 2.0}


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


def test_screenshots_stay_off_after_a_secret_even_when_its_value_is_gone(tmp_path, monkeypatch):
    """The first fix keyed on the value being scrubbable: a short secret, or one no longer exported,
    re-enabled capture while the session still remembered handling it."""
    import asyncio

    from jevdual.session import observe

    asked: list[object] = []

    class Bridge:
        async def observe(self, *, screenshot_path=None):
            asked.append(screenshot_path)
            return _nm([_field(1, "PIN", value="42")])

    st = SessionState(dir=str(tmp_path), app="X", pid=1, window_id=2, task="t")
    st.secret_names.append("PIN")
    monkeypatch.delenv("FOOTWORK_SECRET_PIN", raising=False)
    asyncio.run(observe(st, Bridge()))
    monkeypatch.setenv("FOOTWORK_SECRET_PIN", "42")  # shorter than the scrub minimum
    asyncio.run(observe(st, Bridge()))
    assert asked == [None, None]


def test_a_menu_items_effect_is_not_confirmed_by_the_windows_change(tmp_path):
    """Q13a task 4: File > Open in Finder read "confirmed (1 elements removed)" and opened nothing."""
    before = [_field(1, "a", value="x"), _field(2, "b", value="y")]
    pend = {"line": "menu(File > Open)", "driver_effect": "unverifiable", "op": "menu"}
    r = receipt_for(_state(tmp_path, before, pend), _nm(before[:1]))
    assert r is not None and r["effect"] == "unverifiable" and "another window or app" in r["evidence"], r


def test_a_navigation_that_became_a_download_is_not_called_not_applied(tmp_path):
    """Q13a task 4: navigating to a .txt read "refused (not applied ...)" while the file was downloaded."""
    cands = [_field(1, "a", value="x")]
    pend = {
        "line": "navigate(http://x/report.txt)",
        "driver_effect": "refused",
        "op": "navigate",
        "error": "driver refused:  navigation failed: net::ERR_ABORTED",
    }
    r = receipt_for(_state(tmp_path, cands, pend), _nm(cands))
    assert r is not None and r["effect"] == "unverifiable" and "download" in r["evidence"], r


def test_cross_context_labels_receipts_and_carries_with_their_surface(tmp_path):
    import json as _json

    from jevdual.session import cross_context

    st = SessionState(
        dir=str(tmp_path), app="Google Chrome (footwork)", pid=1, window_id=2, task="t", mode="browser"
    )
    st.last_url = "https://books.toscrape.com/"
    st.save()
    (tmp_path / "session.jsonl").write_text(
        _json.dumps(
            {
                "kind": "receipt",
                "action": {"line": "click(Books)"},
                "effect": "confirmed",
                "evidence": "navigated to /",
            }
        )
        + "\n"
    )
    (tmp_path / "carries.json").write_text(
        _json.dumps(
            {
                "price": {
                    "text": "£51.77",
                    "location": "https://books.toscrape.com/",
                    "title": "",
                    "element_role": "text",
                    "element_label": "£51.77",
                }
            }
        )
    )
    ctx = cross_context(tmp_path)
    assert ctx[0]["surface"] == "Google Chrome (footwork) https://books.toscrape.com/"
    assert ctx[0]["actions"] == ["click(Books) -> confirmed: navigated to /"]
    assert "read @price = '£51.77' at https://books.toscrape.com/" in ctx[1]["actions"][0]


def test_carried_checks_say_whether_the_field_holds_the_carried_value():
    from jevdual.session import carried_checks

    carry = {"name": "price", "text": "£51.77", "location": "https://books.toscrape.com/", "title": ""}
    rec = {"kind": "do", "op": "append", "target_label": "text area", "carry": carry}
    ok = carried_checks([rec], _nm([_field(1, "text area", value="Price:\n£51.77")]).menu)
    assert ok[0]["actions"][0].startswith("harness check: 'text area' holds @price = '£51.77'")
    bad = carried_checks([rec], _nm([_field(1, "text area", value="Price:\n£52.00")]).menu)
    assert "does NOT hold" in bad[0]["actions"][0] and "'£52.00'" in bad[0]["actions"][0]
    typed = {"kind": "do", "op": "type", "target_label": "Message", "carry": {**carry, "text": "624"}}
    assert (
        "holds @price = '624'"
        in carried_checks([typed], _nm([_field(2, "Message", value="624")]).menu)[0]["actions"][0]
    )


def test_writing_a_finder_name_field_is_not_a_confirmed_rename(tmp_path):
    """E3: typing into Finder's list-view name cell read "confirmed" while the file on disk kept its name."""
    before = [_field(61, "textbox", value="draft.txt")]
    pend = {
        "line": "type(textbox)",
        "driver_effect": "confirmed",
        "op": "type",
        "target_id": 61,
        "target_label": "textbox",
        "intended": "KB-20260921.txt",
        "secret": False,
        "app": "Finder",
    }
    r = receipt_for(_state(tmp_path, before, pend), _nm([_field(61, "textbox", value="KB-20260921.txt")]))
    assert r is not None and r["effect"] == "unverifiable" and "not a committed rename" in r["evidence"], r


def test_a_secret_typed_into_a_masked_field_is_unverifiable_not_partial(tmp_path, monkeypatch):
    """Q19 R3: a correct password read "partial (holds {secret}, not the text typed)" because the browser
    reads the field back as bullets and does not mark it as a password."""
    monkeypatch.setenv("FOOTWORK_SECRET_PTA", "Password123")
    before = [_field(34, "Password")]
    pend = {
        "line": "type(Password)",
        "driver_effect": "confirmed",
        "op": "type",
        "target_id": 34,
        "target_label": "Password",
        "intended": None,
        "secret": True,
    }
    st = _state(tmp_path, before, pend)
    st.secret_names.append("PTA")
    r = receipt_for(st, _nm([_field(34, "Password", value="•" * 11)]), secret_value="Password123")
    assert (
        r is not None
        and r["effect"] == "unverifiable"
        and "11 characters, the length of the {secret}" in r["evidence"]
    ), r


def test_a_numeric_label_is_addressable_and_an_incomplete_view_says_so():
    """Q19 R4: digit buttons could not be addressed by label (D08); a partial page read as whole (D02)."""
    from jevdual.session import render_observation, resolve_label

    nm = _nm(
        [
            Candidate(id=14, label="2", role="button", operations=("click",)),
            Candidate(id=2, label="All Clear", role="button", operations=("click",)),
        ]
    )
    assert resolve_label(nm, "label:2") == (14, "")
    nm.menu = Menu(
        url="u",
        title="t",
        page_text="",
        candidates=nm.menu.candidates,
        by_operation={},
        omitted={"elements_incomplete": 1},
    )
    assert "this observation is incomplete" in render_observation(nm, receipt=None)
