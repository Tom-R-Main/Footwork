"""Portable proposals fail closed without inventing native probability distributions."""

from copy import deepcopy

import pytest
from jevdual.judgments import (
    JudgmentError,
    NativeScore,
    check_schema,
    completion_admissible,
    completion_schema,
    proposal_schema,
    risk_schema,
    validate_completion,
    validate_proposal,
    validate_schema,
)


def completed():
    return {
        "complete": "supported",
        "answer_required": True,
        "source_ids": ["s1"],
        "requirements": [
            {"id": "r1", "verdict": "supported", "source_ids": ["s1"]},
            {"id": "r2", "verdict": "supported", "source_ids": ["s2"]},
        ],
    }


def test_completion_categories_and_unknown_abstain():
    value = completed()
    assert completion_admissible(value, ["r1", "r2"], ["s1", "s2"])
    for category in ["contradicted", "insufficient", "unknown"]:
        value["requirements"][0]["verdict"] = category
        assert not completion_admissible(value, ["r1", "r2"], ["s1", "s2"])
    value = completed()
    value["answer_required"] = None
    assert not completion_admissible(value, ["r1", "r2"], ["s1", "s2"])


@pytest.mark.parametrize(
    "mutation",
    [
        lambda v: v["requirements"].pop(),
        lambda v: v["requirements"][1].update(id="r1"),
        lambda v: v["requirements"][1].update(id="invented"),
        lambda v: v["requirements"][0].update(source_ids=["invented"]),
        lambda v: v["requirements"][0].update(source_ids=["s1", "s1"]),
        lambda v: v["requirements"][0].update(source_ids=[]),
        lambda v: v.update(source_ids=[]),
        lambda v: v.update(source_ids=["s1", "s1"]),
        lambda v: v.update(confidence=0.99),
        lambda v: v.update(answer_required=1),
    ],
)
def test_completion_rejects_invalid_bindings_and_invented_scores(mutation):
    value = completed()
    mutation(value)
    with pytest.raises(JudgmentError):
        validate_completion(value, ["r1", "r2"], ["s1", "s2"])


def test_no_sources_can_report_unknown():
    value = {
        "complete": "unknown",
        "answer_required": None,
        "source_ids": [],
        "requirements": [{"id": "r", "verdict": "unknown", "source_ids": []}],
    }
    validate_completion(value, ["r"], [])
    value["source_ids"] = ["invented"]
    with pytest.raises(JudgmentError):
        validate_completion(value, ["r"], [])


def test_pair_and_revision_are_both_required():
    pairs = [("click", "button"), ("type", "field"), ("wait", None)]
    value = {"decision": "propose", "revision": "rev1", "operation": "click", "target_id": "button"}
    validate_proposal(value, pairs, "rev1")
    value["target_id"] = "field"
    with pytest.raises(JudgmentError, match="pair"):
        validate_proposal(value, pairs, "rev1")
    value.update(operation="wait", target_id=None)
    validate_proposal(value, pairs, "rev1")
    with pytest.raises(JudgmentError):
        validate_proposal(value, pairs, "rev2")


@pytest.mark.parametrize("decision", ["abstain", "unknown"])
def test_nonproposal_requires_null_pair(decision):
    value = {"decision": decision, "revision": "r", "operation": None, "target_id": None}
    validate_proposal(value, [("click", "1")], "r")
    value.update(operation="click", target_id="1")
    with pytest.raises(JudgmentError):
        validate_proposal(value, [("click", "1")], "r")


def test_risk_preserves_unknown_permission_separately():
    validate_schema({"effect": "unknown", "permission_required": None, "source_ids": []}, risk_schema([]))
    validate_schema(
        {"effect": "benign", "permission_required": True, "source_ids": ["task"]}, risk_schema(["task"])
    )


def test_native_score_requires_provenance_and_finite_value():
    assert NativeScore("typesafe", "jev", "complete", 0.81, "case/r1").value == 0.81
    with pytest.raises(JudgmentError):
        NativeScore("typesafe", "jev", "complete", float("nan"), "case/r1")
    with pytest.raises(JudgmentError):
        NativeScore("typesafe", "jev", "complete", 0.81, "")


def test_schema_rejects_unenforced_constraints_even_unused_branch():
    schema = deepcopy(completion_schema(["r"], ["s"]))
    schema["properties"]["source_ids"]["items"]["pattern"] = "^s$"
    with pytest.raises(JudgmentError, match="unsupported"):
        check_schema(schema)
    schema = proposal_schema([], "r")
    schema["required"].remove("operation")
    with pytest.raises(JudgmentError, match="fully required"):
        check_schema(schema)
