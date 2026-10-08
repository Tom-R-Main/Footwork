"""D3 browser fixture contracts and oracle-independent execution admission."""

import json
from copy import deepcopy

import pytest

from evals.d3_browser import (
    FAMILIES,
    OBSERVATION_JS,
    VARIANTS,
    expected_label,
    fixture,
    guard,
    point_in_polygon,
    proposal_for,
)


@pytest.mark.parametrize("family", FAMILIES)
def test_variant_oracle_does_not_enter_prompt(family):
    cases = [fixture(family, variant) for variant in VARIANTS]
    assert [c["oracle"]["expected"] for c in cases] == [True, False, None, True]
    for case in cases:
        assert "expected" not in case["question"]
        assert "fixtureState" not in case["question"]
        assert "correct answer" not in case["html"]
        assert "receipt" in case["html"]


def test_actual_observation_excludes_hidden_oracle():
    assert "innerText" in OBSERVATION_JS
    assert "aria-label" in OBSERVATION_JS
    assert "getBoundingClientRect" in OBSERVATION_JS
    assert "fixtureState" not in OBSERVATION_JS
    assert "innerHTML" not in OBSERVATION_JS


def test_map_oracle_distinguishes_containment():
    spec = fixture("map_containment", "supported")
    oracle = spec["oracle"]
    assert point_in_polygon(tuple(oracle["points_canvas"]["marker-a"]), oracle["polygon"])
    assert not point_in_polygon(tuple(oracle["points_canvas"]["marker-b"]), oracle["polygon"])
    assert fixture("map_containment", "ambiguous")["oracle"]["polygon"] == []


def observation(revision="r1", target="browser-1", x=10):
    return {"revision": revision, "target_id": target,
            "dom": {"elements": [{"target_id": "approve", "bounds": {
                "x": x, "y": 20, "width": 100, "height": 40}}]}}


def test_proposals_keep_old_binding_only_for_stale_near_miss():
    spec = {"target": "approve"}
    old, current = observation(), observation("r2", x=300)
    stale = proposal_for(spec, [old, current], "near_miss")
    fresh = proposal_for(spec, [old, current], "text_control")
    assert stale["x"] == 60 and stale["observation_revision"] == "r1"
    assert fresh["x"] == 350 and fresh["observation_revision"] == "r2"


@pytest.mark.parametrize("expected", [True, False, None])
def test_semantic_oracle_cannot_prevent_safe_fixture_dispatch(expected):
    current = observation()
    case = {"expected": expected, "proposal": proposal_for({"target": "approve"}, [current], "supported")}
    assert guard(case, current) == (True, "scope_and_binding_pass")
    changed = deepcopy(case)
    changed["oracle"] = {"expected": not bool(expected)}
    changed["variant"] = "near_miss"
    assert guard(changed, current) == (True, "scope_and_binding_pass")


def test_guard_refuses_stale_or_wrong_browser_target():
    current = observation("r2")
    stale = proposal_for({"target": "approve"}, [observation()], "supported")
    assert guard({"proposal": stale}, current) == (False, "stale_observation")
    stale["browser_target_id"] = "other-browser"
    assert guard({"proposal": stale}, current) == (False, "wrong_browser_target")


def test_guard_checks_current_geometry_and_disabled_state():
    current = observation()
    proposal = proposal_for({"target": "approve"}, [current], "supported")
    changed = deepcopy(current)
    changed["dom"]["elements"][0]["bounds"]["x"] = 30
    assert guard({"proposal": proposal}, changed) == (False, "target_geometry_changed")
    current["dom"]["elements"][0]["disabled"] = True
    assert guard({"proposal": proposal}, current) == (False, "target_unavailable")


def test_fixture_parameters_reject_unknowns():
    with pytest.raises(ValueError):
        fixture("unknown", "supported")
    with pytest.raises(ValueError):
        fixture("toolbar_glyph", "unknown")
    assert json.dumps(expected_label("ambiguous")) == "null"
