"""Control state end to end (docs/notebook/2026-10-28-control-state.md CTL3): every producer keeps
checked/selected/expanded/pressed, "mixed" stays distinct from off, sessions round-trip them, and the
effect diff compares a state only when both observations report it."""

from __future__ import annotations

import json
from types import SimpleNamespace

from jevdual.arbiter import Arbiter
from jevdual.browser_driver import menu_from_semantic
from jevdual.effects import diff
from jevdual.menu import Candidate, Menu, candidate_from_node, control_state
from jevdual.receipts import receipt_from_effect, receipt_text

TEXT = "settings page " * 40


def cand(i, label, role="checkbox", **kw) -> Candidate:
    return Candidate(id=i, label=label, role=role, operations=("click",), **kw)


def menu(*cands: Candidate, text: str = TEXT) -> Menu:
    return Menu(url="http://x/s", title="Settings", page_text=text, candidates=tuple(cands), by_operation={})


# ---- producers ------------------------------------------------------------------------------


def test_control_state_keeps_mixed_apart_from_off():
    assert control_state("mixed") == "mixed" and control_state("MIXED") == "mixed"
    assert control_state("true") is True and control_state(False) is False and control_state(None) is None
    assert control_state("") is True  # a bare boolean attribute


class _Node(SimpleNamespace):
    def get_all_children_text(self) -> str:
        return self.text


def _node(tag: str, attrs: dict, props: dict | None = None, text: str = "") -> _Node:
    ax = SimpleNamespace(
        role=None,
        name=None,
        properties=[SimpleNamespace(name=k, value=v) for k, v in (props or {}).items()],
    )
    return _Node(
        node_name=tag,
        attributes=attrs,
        ax_node=ax,
        children=[],
        text=text,
        is_scrollable=False,
        parent_node=None,
        absolute_position=None,
        snapshot_node=None,
    )


def test_browser_use_nodes_keep_mixed_and_pressed():
    mixed = candidate_from_node(
        1, _node("INPUT", {"type": "checkbox", "aria-label": "All"}, {"checked": "mixed"})
    )
    assert mixed.checked == "mixed"
    aria = candidate_from_node(2, _node("DIV", {"role": "checkbox", "aria-checked": "mixed"}, text="Some"))
    assert aria.checked == "mixed"
    bold = candidate_from_node(3, _node("BUTTON", {"aria-pressed": "true"}, text="Bold"))
    assert bold.pressed is True and bold.to_state()["pressed"] is True
    ax_pressed = candidate_from_node(4, _node("BUTTON", {}, {"pressed": "mixed"}, text="Italic"))
    assert ax_pressed.pressed == "mixed"


def test_cua_browser_menu_keeps_every_reported_state():
    s = {
        "page": {"url": "http://x/", "title": "T"},
        "snapshot": {"id": "snap1", "complete": True},
        "refs": [
            {"ref": "e:1", "role": "checkbox", "name": "All", "states": {"checked": "mixed"}},
            {"ref": "e:2", "role": "tab", "name": "Billing", "states": {"selected": True}},
            {"ref": "e:3", "role": "button", "name": "Details", "states": {"expanded": False}},
            {"ref": "e:4", "role": "button", "name": "Bold", "states": {"pressed": "true"}},
            {"ref": "e:5", "role": "button", "name": "Plain", "states": {}},
        ],
    }
    by = {c.label: c for c in menu_from_semantic(s).menu.candidates}
    assert by["All"].checked == "mixed"
    assert by["Billing"].selected is True
    assert by["Details"].expanded is False
    assert by["Bold"].pressed is True
    plain = by["Plain"]
    assert (plain.checked, plain.selected, plain.expanded, plain.pressed) == (None, None, None, None)


def test_native_mixed_checkbox_and_repeated_toggles_survive_pruning():
    from jevdual.menu import MenuBudget
    from jevdual.native import _checked, _prune

    assert _checked("2") == "mixed" and _checked(1) is True and _checked("0") is False
    cands = [
        cand(1, "Enabled", checked=True),
        cand(2, "Enabled", checked=False),  # a second setting with the same label
        cand(3, "More", role="button"),
        cand(4, "More", role="button"),  # a stateless repeat still drops
    ]
    om: dict[str, int] = {}
    kept, _, _ = _prune(cands, {c.id: str(c.id) for c in cands}, {}, om, MenuBudget())
    assert [c.id for c in kept] == [1, 2, 3] and om["duplicate"] == 1


# ---- the effect diff ------------------------------------------------------------------------


def test_mixed_to_unchecked_is_a_named_change():
    e = diff(menu(cand(1, "All", checked="mixed")), menu(cand(1, "All", checked=False)))
    assert e.status == "changed" and e.changed == 1
    assert e.transitions == ("'All' checked mixed -> False",) and "checked mixed -> False" in e.summary


def test_a_toggle_button_with_unchanged_text_is_a_change():
    e = diff(
        menu(cand(1, "Bold", role="button", pressed=False)),
        menu(cand(1, "Bold", role="button", pressed=True)),
    )
    assert e.status == "changed" and not e.no_effect


def test_an_expanded_disclosure_with_unchanged_text_is_a_change():
    e = diff(
        menu(cand(1, "Details", role="button", expanded=False)),
        menu(cand(1, "Details", role="button", expanded=True)),
    )
    assert e.status == "changed" and "'Details' expanded False -> True" in e.summary


def test_the_second_of_two_same_key_controls_is_compared():
    before = menu(cand(1, "Enabled", checked=True), cand(2, "Enabled", checked=False))
    after = menu(cand(1, "Enabled", checked=True), cand(2, "Enabled", checked=True))
    e = diff(before, after)
    assert e.status == "changed" and e.changed == 1


def test_a_repeated_control_appearing_is_counted():
    before = menu(cand(1, "Remove", role="button"))
    after = menu(cand(1, "Remove", role="button"), cand(2, "Remove", role="button"))
    e = diff(before, after)
    assert (e.added, e.removed) == (1, 0) and e.status == "changed"


def test_a_state_seen_on_one_side_only_is_inconclusive_not_progress():
    e = diff(menu(cand(1, "Details", role="button")), menu(cand(1, "Details", role="button", expanded=True)))
    assert e.status == "inconclusive" and e.inconclusive and not e.no_effect and not e.visible_change
    assert e.unknown == 1 and "not observed both before and after" in e.summary


def test_identical_stateful_menus_are_unchanged():
    m = menu(cand(1, "All", checked="mixed"), cand(2, "Bold", role="button", pressed=True))
    assert diff(m, m).status == "unchanged" and diff(m, m).no_effect


# ---- consumers ------------------------------------------------------------------------------


def test_an_inconclusive_step_is_an_unverifiable_receipt():
    e = diff(menu(cand(1, "Details", role="button")), menu(cand(1, "Details", role="button", expanded=True)))
    r = receipt_from_effect(3, ("click(Details)",), e, url_after="http://x/s")
    assert r.effect == "unverifiable" and not r.no_effect
    assert "1 control states were not observed" in receipt_text(r)
    refused = receipt_from_effect(3, ("click(Details)",), e, url_after="http://x/s", error="not clickable")
    assert refused.effect == "refused"


def test_a_confirmed_receipt_names_the_transition():
    e = diff(
        menu(cand(1, "Bold", role="button", pressed=False)),
        menu(cand(1, "Bold", role="button", pressed=True)),
    )
    r = receipt_from_effect(3, ("click(Bold)",), e, url_after="http://x/s")
    assert r.effect == "confirmed" and "'Bold' pressed False -> True" in r.evidence


def test_an_inconclusive_step_neither_extends_nor_breaks_a_no_effect_run():
    a = Arbiter()
    same = menu(cand(1, "Details", role="button"))
    seen = menu(cand(1, "Details", role="button", expanded=True))
    a._observe(same)
    a._observe(same)
    assert a._no_effect_run == 1
    a._observe(seen)  # one-sided state: inconclusive
    assert a._no_effect_run == 1
    a._observe(seen)
    assert a._no_effect_run == 2
    a._observe(menu(cand(1, "Details", role="button", expanded=False)))  # a real change
    assert a._no_effect_run == 0


# ---- persistence and public projections -----------------------------------------------------


def _state(tmp_path):
    from jevdual.session import SessionState

    return SessionState(dir=str(tmp_path), app="Chrome", pid=1, window_id=2, task="t")


def test_a_saved_baseline_round_trips_every_state_and_identity_field(tmp_path):
    from jevdual.session import SessionState

    m = menu(
        cand(1, "All", checked="mixed"),
        cand(2, "Billing", role="tab", selected=True),
        cand(3, "Details", role="button", expanded=True),
        cand(4, "Bold", role="button", pressed=False),
        cand(5, "Docs", role="link", href="/docs"),
    )
    st = _state(tmp_path)
    st.remember(SimpleNamespace(menu=m, snapshot_id="snap1"))
    st.save()
    back = SessionState.load(tmp_path).last_menu()
    assert back is not None
    assert [(c.checked, c.selected, c.expanded, c.pressed, c.href) for c in back.candidates] == [
        (c.checked, c.selected, c.expanded, c.pressed, c.href) for c in m.candidates
    ]
    assert diff(back, m).status == "unchanged"


def test_a_baseline_saved_before_the_new_fields_loads_and_compares_conservatively(tmp_path):
    from jevdual.session import SessionState

    st = _state(tmp_path)
    st.last_url, st.last_title, st.last_page_text = "http://x/s", "Settings", TEXT
    st.last_candidates = [
        {
            "id": 1,
            "label": "Details",
            "role": "button",
            "operations": ["click"],
            "value": None,
            "input_type": None,
            "checked": None,
            "selected": None,
            "section": None,
        }
    ]
    st.save()
    raw = json.loads((tmp_path / "session.json").read_text())
    assert "expanded" not in raw["last_candidates"][0]
    back = SessionState.load(tmp_path).last_menu()
    assert back is not None and back.candidates[0].expanded is None
    assert diff(back, menu(cand(1, "Details", role="button", expanded=True))).status == "inconclusive"


def test_the_capability_observation_reports_known_state_only():
    from jevdual.capability.observations import Observations

    snap = SimpleNamespace(
        menu=menu(cand(1, "All", checked="mixed"), cand(2, "Plain", role="button")),
        values={},
        frames={},
        elements_complete=True,
        truncated=False,
        degraded=False,
    )
    rows = Observations().project("r", snap, writable=False)["elements"]
    assert rows[0]["state"] == {"checked": "mixed"} and "state" not in rows[1]


_NM = {
    "pid": 1,
    "window_id": 2,
    "app_name": "Demo",
    "elements_complete": True,
    "truncated": False,
    "degraded": False,
}


def _bridge_observing(fresh_cands):
    import asyncio as _a

    from jevdual.native import NativeBridge, NativeMenu

    b = NativeBridge.__new__(NativeBridge)

    async def observe(**kw):
        return NativeMenu(
            **_NM, menu=menu(*fresh_cands), snapshot_id="s2", tokens={c.id: str(c.id) for c in fresh_cands}
        )

    b.observe = observe  # type: ignore[method-assign]
    return b, _a, NativeMenu


def test_live_resolution_keeps_the_position_among_same_label_toggles():
    import pytest
    from jevdual.native import NativeBridgeError

    decided = (cand(200, "Enabled", checked=False), cand(201, "Enabled", checked=False))
    shifted = (
        cand(200, "Wi-Fi", checked=True),
        cand(201, "Enabled", checked=False),
        cand(202, "Enabled", checked=False),
    )
    b, aio, NativeMenu = _bridge_observing(shifted)
    nm = NativeMenu(**_NM, menu=menu(*decided), snapshot_id="s1", tokens={200: "a", 201: "b"})
    _, hit = aio.run(b._live(nm, 201, "click"))
    assert hit == 202  # the second "Enabled", not id 201 which is now the first
    b, aio, _ = _bridge_observing((cand(201, "Enabled", checked=False),))
    with pytest.raises(NativeBridgeError) as exc:
        aio.run(b._live(nm, 201, "click"))
    assert exc.value.reason == "target_changed"


def test_repeated_toggles_are_offered_only_as_whole_groups():
    from jevdual.menu import MenuBudget
    from jevdual.native import NATIVE_MENU_CAP, TOGGLE_REPEATS_KEPT, _prune

    def prune(cands):
        om: dict[str, int] = {}
        kept, _, _ = _prune(cands, {c.id: str(c.id) for c in cands}, {}, om, MenuBudget())
        return [c.id for c in kept], om

    small = [cand(i, "Enabled", checked=False) for i in range(TOGGLE_REPEATS_KEPT)]
    assert prune(small)[0] == list(range(TOGGLE_REPEATS_KEPT))
    # a larger group cannot be told apart by position among what is offered: its first member only
    table = [cand(i, "0", checked=False) for i in range(40)] + [cand(99, "OK", role="button")]
    ids, om = prune(table)
    assert ids == [0, 99] and om["duplicate"] == 39
    # a group the cap would cut is offered by its first member, not partially
    filler = [cand(1000 + i, f"link {i}", role="link") for i in range(NATIVE_MENU_CAP - 2)]
    ids, om = prune(filler + [cand(i, "Enabled", checked=False) for i in range(3)])
    assert [i for i in ids if i < 1000] == [0] and "cap" not in om
