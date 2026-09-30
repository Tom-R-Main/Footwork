"""Integrity checks for independently labelled development-only R1 inputs.

These checks protect the experiment's balance and admissible action labels. They
do not judge model output, consume adoption material, or execute proposals.
"""

import json
from collections import Counter
from pathlib import Path

import pytest

CASES = Path(__file__).resolve().parents[1] / "evals" / "r1"
TARGETED = {"click", "type", "append", "select", "enter", "hover", "scroll"}
NON_TARGETED = {"scroll_page", "back", "wait", "done", "blocked"}


def load_cases(name):
    return json.loads((CASES / f"{name}.json").read_text())


@pytest.mark.parametrize("name,count", [("risk", 40), ("actions", 30)])
def test_case_identity_and_independent_task_content(name, count):
    cases = load_cases(name)
    assert len(cases) == count
    assert len({case["id"] for case in cases}) == count
    assert len({case["state"]["task"] for case in cases}) == count
    assert len({case["state"]["page"]["text"] for case in cases}) == count
    for case in cases:
        assert case["id"].startswith("R1-")
        assert case["category"]
        assert case["rationale"].strip()
        assert case["state"]["task"].strip()
        assert all(case["state"]["page"][key].strip() for key in ("url", "title", "text"))


def test_risk_balance_and_proposal_contract():
    cases = load_cases("risk")
    assert Counter(case["expect"] for case in cases) == {"harmful": 20, "benign": 20}
    for case in cases:
        state = case["state"]
        assert isinstance(state["requirements"], list)
        assert isinstance(state["authorized_actions"], list)
        assert all(isinstance(scope, str) and scope for scope in state["authorized_actions"])
        action = state["action"]
        assert action["operation"] in TARGETED | NON_TARGETED
        assert isinstance(action["target_id"], int)
        assert action["label"].strip()
        if action["operation"] in {"type", "append", "select"}:
            assert action["text"].strip()


def test_risk_covers_semantic_effect_traps_and_read_counterexamples():
    cases = {case["category"]: case for case in load_cases("risk")}
    harmful = {
        "euphemistic_finish", "euphemistic_send", "euphemistic_submit", "negation_effect",
        "keyboard_enter_effect", "menu_effect", "replace_vs_append", "append_write",
        "origin_mismatch", "prompt_injection_effect", "authorized_distinct_write",
    }
    benign = {
        "negation_read", "keyboard_enter_read", "menu_read", "draft_only",
        "cross_origin_read", "prompt_injection_read", "distinct_read", "select_preview",
    }
    assert harmful | benign <= cases.keys()
    assert all(cases[category]["expect"] == "harmful" for category in harmful)
    assert all(cases[category]["expect"] == "benign" for category in benign)
    # A grant is deliberately present for a harmful-labelled proposal: permission
    # is not the label oracle for inherent effect classification.
    assert cases["authorized_distinct_write"]["state"]["authorized_actions"]


def test_action_balance_and_expected_pair_admissibility():
    cases = load_cases("actions")
    assert Counter(case["surface"] for case in cases) == {"browser": 15, "native": 15}
    for case in cases:
        state = case["state"]
        assert isinstance(state["requirements"], list)
        assert isinstance(state["recent_actions"], list)
        assert isinstance(state["notes"], str) and state["notes"]
        assert type(case["expect_abstain"]) is bool
        elements = state["elements"]
        ids = [element["id"] for element in elements]
        assert len(ids) == len(set(ids))
        assert all(type(target) is int for target in ids)
        offered = {}
        for element in elements:
            assert element["label"] and element["role"]
            operations = element["operations"]
            assert isinstance(operations, list)
            assert len(operations) == len(set(operations))
            assert set(operations) <= TARGETED
            offered[element["id"]] = set(operations)
        pairs = case["expected_pairs"]
        assert pairs
        assert len(pairs) == len({(pair["operation"], pair["target"]) for pair in pairs})
        for pair in pairs:
            op, target = pair["operation"], pair["target"]
            if op in NON_TARGETED:
                assert target is None
            else:
                assert op in TARGETED
                assert target in offered and op in offered[target]
        if case["expect_abstain"]:
            assert all(pair == {"operation": "blocked", "target": None} for pair in pairs)
        else:
            assert all(pair["operation"] != "blocked" for pair in pairs)


@pytest.mark.parametrize("surface", ["browser", "native"])
def test_action_surfaces_include_abstention_and_useful_alternatives(surface):
    cases = [case for case in load_cases("actions") if case["surface"] == surface]
    abstentions = [case for case in cases if case["expect_abstain"]]
    assert len(abstentions) == 3
    assert any("reasoning" in case["category"] for case in abstentions)
    assert any("ambiguous" in case["category"] for case in abstentions)
    assert any("target" in case["category"] for case in abstentions)
    assert any(len(case["expected_pairs"]) > 1 for case in cases)
    operations = {pair["operation"] for case in cases for pair in case["expected_pairs"]}
    assert {"click", "type", "enter", "wait", "done", "blocked"} <= operations
