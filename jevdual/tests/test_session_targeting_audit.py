"""Public CLI targeting refusals retain evidence without claiming dispatch."""

import json

import pytest

from tests import test_session_scenarios as scenarios
from tests.fixtures.native_world import ToggleControl

fw = scenarios.fw
world = scenarios.world


def _state(fw):
    return json.loads((fw.session / "session.json").read_text())


def _records(fw):
    return [json.loads(line) for line in (fw.session / "session.jsonl").read_text().splitlines()]


@pytest.mark.parametrize("failure", ["missing_label", "missing_id", "ambiguous_label", "prior_ambiguity", "changed_label", "changed_role", "changed_section", "drag_missing"])
def test_targeting_failure_is_logged_without_dispatch(world, fw, failure):
    world.backed_toggles = {200: ToggleControl("A", label="Setting A")}
    if failure in ("ambiguous_label", "prior_ambiguity"):
        world.backed_toggles[201] = ToggleControl("B", label="Setting A")
    assert fw("start", "Inspect fixture controls", "--app", "Calculator")[0] == 0
    previous = _state(fw)["last_snapshot"]
    selector = "200"
    command = ["click", selector]
    if failure == "missing_label":
        selector = "Missing setting"
        command = ["click", selector]
    elif failure == "missing_id":
        selector = "9999"
        command = ["click", selector]
    elif failure == "ambiguous_label":
        selector = "Setting A"
        command = ["click", selector]
    elif failure == "changed_label":
        world.backed_toggles[200].label = "Another setting"
    elif failure == "changed_role":
        world.backed_toggles[200].role = "AXButton"
    elif failure == "changed_section":
        # The previous candidate's scope changed, even though its ID and label did not.
        state = _state(fw)
        next(c for c in state["last_candidates"] if c["id"] == 200)["section"] = "Original row"
        (fw.session / "session.json").write_text(json.dumps(state))
    elif failure == "drag_missing":
        command = ["drag", "200", "missing destination"]
    code, out, err = fw("do", *command, "--no-judge")
    assert code == 4 and world.toggle_writes == [] and world.presses == [], (out, err)
    attempts = [r for r in _records(fw) if r["kind"] == "attempted_action"]
    assert len(attempts) == 1
    record = attempts[0]
    assert record["dispatched"] is False and record["requested_selector"] == selector
    assert record["previous_observation"] == previous
    assert record["observation"] == _state(fw)["last_snapshot"] != previous
    assert record["reason"] and record["code"] and "coverage" in record
    assert _state(fw)["step"] == 0 and _state(fw)["pending"] is None
    assert not [r for r in _records(fw) if r["kind"] in ("do", "receipt")]


def test_targeting_audit_excludes_typed_text_and_redacts_selector_secrets(world, fw, monkeypatch):
    monkeypatch.setenv("FOOTWORK_SECRET_AUDIT", "private-fixture-secret")
    assert fw("start", "Inspect fixture controls", "--app", "Calculator")[0] == 0
    code, out, err = fw("do", "type", "private-fixture-secret", "{AUDIT}", "--no-judge")
    assert code == 4, (out, err)
    attempt = next(r for r in _records(fw) if r["kind"] == "attempted_action")
    assert attempt["requested_selector"] == "{secret}"
    assert "private-fixture-secret" not in json.dumps(attempt)
    assert not {"text", "intended", "page_text", "target_label"} & attempt.keys()


def test_missing_selector_with_capped_observation_is_not_claimed_absent(world, fw):
    assert fw("start", "Inspect fixture controls", "--app", "Calculator", "--native-menu-cap", "3")[0] == 0
    code, out, err = fw("do", "click", "Not in this budget", "--no-judge")
    assert code == 4 and "budget" in err, (out, err)
    attempt = next(r for r in _records(fw) if r["kind"] == "attempted_action")
    assert attempt["code"] == "selector_not_observed"
    assert attempt["coverage"]["omitted"]["cap"] > 0


@pytest.mark.parametrize("explicit_pid", [False, True])
def test_native_budget_persists_through_observation_and_action(world, fw, explicit_pid):
    world.base["pid"] = 77
    args = ["--pid", "77"] if explicit_pid else []
    code, out, err = fw(
        "start", "Inspect fixture controls", "--app", "Calculator", "--native-menu-cap", "3", *args
    )
    assert code == 0, (out, err)
    assert _state(fw)["native_menu_cap"] == 3
    assert len(_state(fw)["last_candidates"]) == 3
    assert fw("look")[0] == 0
    assert len(_state(fw)["last_candidates"]) == 3
    target = next(c for c in _state(fw)["last_candidates"] if c["label"] != "Delete")
    code, out, err = fw("do", "click", str(target["id"]), "--no-judge")
    assert code == 0, (out, err)
    assert len(_state(fw)["last_candidates"]) == 3


def test_browser_start_refuses_a_native_budget_before_resetting_history(world, fw):
    assert fw("start", "Inspect fixture controls", "--app", "Calculator")[0] == 0
    before = (fw.session / "session.json").read_bytes()
    code, out, err = fw("start", "Inspect fixture", "--browser", "--native-menu-cap", "240")
    assert code == 2 and "requires a native session" in err, (out, err)
    assert (fw.session / "session.json").read_bytes() == before


def test_section_selector_resolves_only_the_named_ancestor(world, fw):
    # Each semantic row is an actual ancestor in the driver snapshot.
    world.base["elements"].extend([
        {"element_index": 500, "role": "AXGroup", "label": "alpha.test", "parent_index": 0},
        {"element_index": 501, "role": "AXGroup", "label": "beta.test", "parent_index": 0},
        {"element_index": 502, "role": "AXButton", "label": "MANAGE", "parent_index": 500, "actions": ["AXPress"], "enabled": True},
        {"element_index": 503, "role": "AXButton", "label": "MANAGE", "parent_index": 501, "actions": ["AXPress"], "enabled": True},
    ])
    assert fw("start", "Inspect fixture controls", "--app", "Calculator")[0] == 0
    code, out, err = fw("do", "click", "section:beta.test::button:MANAGE", "--no-judge")
    assert code == 0 and world.presses == ["MANAGE"], (out, err)
    action = next(r for r in _records(fw) if r["kind"] == "do")
    assert action["target_id"] == 503
    assert action["target_identity"] == {
        "role": "button", "label": "MANAGE", "section": "beta.test", "placeholder": None,
    }
    assert not [r for r in _records(fw) if r["kind"] == "attempted_action"]


@pytest.mark.parametrize("changed", ["reorder", "disappear", "duplicate"])
def test_qualified_field_receipt_never_uses_another_rows_value(changed):
    from jevdual.menu import Candidate, Menu
    from jevdual.session import _bound_field

    identity = {"role": "textbox", "label": "Nameserver", "section": "row A", "placeholder": "Primary"}
    selected = Candidate(id=201, operations=("type",), value="selected value", **identity)
    other = Candidate(
        id=200, operations=("type",), value="unrelated value",
        **{**identity, "section": "row B"},
    )
    candidates = [other, selected] if changed == "reorder" else [other]
    if changed == "duplicate":
        candidates = [selected, Candidate(id=200, operations=("type",), value="duplicate", **identity)]
    menu = Menu(url="u", title="fixture", page_text="", candidates=tuple(candidates), by_operation={})
    pending = {"target_id": 200, "target_label": "Nameserver", "target_identity": identity}
    result = _bound_field(menu, pending)
    assert result == selected if changed == "reorder" else result is None


def test_exact_grant_stays_with_qualified_row_after_reordering(world, fw):
    world.base["elements"].extend([
        {"element_index": 500, "role": "AXGroup", "label": "alpha.test", "parent_index": 0},
        {"element_index": 501, "role": "AXGroup", "label": "beta.test", "parent_index": 0},
        {"element_index": 502, "role": "AXButton", "label": "Delete", "parent_index": 500, "actions": ["AXPress"], "enabled": True},
        {"element_index": 503, "role": "AXButton", "label": "Delete", "parent_index": 501, "actions": ["AXPress"], "enabled": True},
    ])
    assert fw("start", "Inspect fixture controls", "--app", "Calculator")[0] == 0
    assert fw("grant", "click", "section:alpha.test::button:Delete")[0] == 0
    world.base["elements"][-2:] = world.base["elements"][-2:][::-1]
    code, out, err = fw("do", "click", "section:beta.test::button:Delete", "--no-judge")
    assert code == 3 and world.presses == [], (out, err)
    assert fw("do", "click", "section:alpha.test::button:Delete", "--no-judge")[0] == 0
    assert world.presses == ["Delete"]


def test_scrub_removes_secret_context_from_candidates_and_operation_index(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from jevdual.menu import Candidate, Menu
    from jevdual.session import SessionState, scrub

    monkeypatch.setenv("FOOTWORK_SECRET_AUDIT", "private-fixture-secret")
    candidate = Candidate(
        id=1, label="Field", role="textbox", operations=("type",),
        section="private-fixture-secret", placeholder="private-fixture-secret",
    )
    menu = Menu(url="u", title="fixture", page_text="", candidates=(candidate,), by_operation={"type": (candidate,)})
    state = SessionState(dir=str(tmp_path), app="fixture", pid=1, window_id=1, task="t", secret_names=["AUDIT"])
    result = scrub(state, SimpleNamespace(menu=menu))
    assert result.menu.candidates[0].section == result.menu.candidates[0].placeholder == "{secret}"
    assert result.menu.by_operation["type"][0] is result.menu.candidates[0]


def test_drag_cannot_reuse_previously_ambiguous_destination(world, fw):
    world.backed_toggles = {
        200: ToggleControl("source", label="Source"),
        201: ToggleControl("first destination", label="Destination"),
        202: ToggleControl("other destination", label="Destination"),
    }
    assert fw("start", "Inspect fixture controls", "--app", "Calculator")[0] == 0
    del world.backed_toggles[202]
    code, out, err = fw("do", "drag", "200", "201", "--no-judge")
    assert code == 4, (out, err)
    attempt = next(r for r in _records(fw) if r["kind"] == "attempted_action")
    assert attempt["code"] == "target_ambiguous" and attempt["requested_destination"] == "201"
    assert not [r for r in _records(fw) if r["kind"] == "do"]
