"""The footwork session's receipts (python/jevdual/session.py), without a Driver."""

from __future__ import annotations

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
    assert r["effect"] == "confirmed" and "hunter" not in r["text"] and "a value" in r["evidence"]
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
