"""D1 runner accounting/projection evidence; HTTP calls are replaced, never paid."""

from __future__ import annotations

import json
from collections import Counter
from types import SimpleNamespace

import pytest
from jevdual.decisions import ChoiceAnswer, DecisionBatch, DecisionsError, PredicateAnswer
from typesafe_sdk import Choice, Noul

from evals import d1_compare as d1


def batch(questions, *, complete=0.99, answer_required=0.01):
    answers = {}
    for name, q in d1.question_data(questions).items():
        if q["type"] == "noul":
            probability = (
                complete if name == "complete" else answer_required if name == "answer_required" else 0.01
            )
            answers[name] = PredicateAnswer(name, probability)
        else:
            values = list(q["criteria"])
            probabilities = {k: 0.1 / (len(values) - 1) if len(values) > 1 else 1 for k in values}
            probabilities[values[0]] = 0.9 if len(values) > 1 else 1
            answers[name] = ChoiceAnswer(name, values[0], probabilities, 0.65)
    return DecisionBatch("gpt-6-luna", answers, None, {}, 0.01)


@pytest.mark.asyncio
async def test_frozen_counts_projection_bodies_and_fanout():
    prepared = await d1.prepared_cases()
    assert Counter(p.role for p in prepared) == {"completion": 36, "risk": 40, "actions": 30}
    assert {
        role: sum(len(p.questions) for p in prepared if p.role == role)
        for role in ("completion", "risk", "actions")
    } == {"completion": 72, "risk": 40, "actions": 262}
    assert max(len(body) for p in prepared for body in (d1.baseline_body(p), d1.candidate_body(p))) <= 24000
    p = prepared[0]
    assert json.loads(json.loads(d1.candidate_body(p))["input"]) == p.state
    assert json.loads(d1.baseline_body(p))["state"] == p.state
    replay = d1.ReplayClient(None, p.state, p.questions)
    with pytest.raises(ValueError, match="projection changed"):
        await replay.system_one({**p.state, "task": "changed"}, p.questions)


def test_question_translation_preserves_criteria_and_values():
    qs = {
        "condition": Noul(
            instructions="Judge data", criteria={"true": "yes criterion", "false": "no criterion"}
        ),
        "pick": Choice(instructions="Choose", criteria={"α": "Alpha", "b": {"meaning": "Beta"}}),
    }
    translated = d1.translate_questions(qs)
    assert (
        translated[0]["instructions"]
        == "Judge data\nTrue criterion: yes criterion\nFalse criterion: no criterion"
    )
    assert translated[1]["choices"] == [
        {"value": "α", "description": "Alpha"},
        {"value": "b", "description": '{"meaning": "Beta"}'},
    ]


def test_bridge_preserves_separate_native_confidence_unknown_usage_and_model():
    qs = {"condition": Noul(), "pick": Choice(criteria={"a": None, "b": None})}
    response = d1.bridge_response(batch(qs), qs)
    assert response.model == "gpt-6-luna"
    assert response.usage.input_tokens is None
    assert response.nouls["condition"].noul == 0.01
    assert response.choices["pick"].confidence == 0.65
    assert response.choices["pick"].probabilities["a"] == 0.9


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1, 1.1, True, None])
def test_bridge_rejects_non_probability(bad):
    qs = {"condition": Noul()}
    b = SimpleNamespace(
        model="gpt-6-luna", input_tokens=None, answers={"condition": SimpleNamespace(probability=bad)}
    )
    with pytest.raises(ValueError, match="predicate"):
        d1.bridge_response(b, qs)


def test_bridge_rejects_missing_heads_and_wrong_distributions():
    qs = {"pick": Choice(criteria={"a": None, "b": None})}
    b = batch(qs)
    b.answers["pick"] = ChoiceAnswer("pick", "b", {"a": 0.9, "b": 0.1}, 0.65)
    with pytest.raises(ValueError, match="choice"):
        d1.bridge_response(b, qs)
    with pytest.raises(ValueError, match="names"):
        d1.bridge_response(SimpleNamespace(answers={}), qs)


@pytest.mark.asyncio
async def test_bridge_replays_original_completion_code_floors():
    prepared = await d1.prepared_cases()
    positives = [p for p in prepared if p.role == "completion" and p.case["expect"] == "accept"]
    outcomes = [
        await d1.baseline_result(p, d1.bridge_response(batch(p.questions), p.questions)) for p in positives
    ]
    assert all(r["semantic_accept"] for r in outcomes)
    assert any(
        not r["accept"] for r in outcomes
    )  # Strong semantic score cannot bypass effect/claim evidence.


def test_budget_reserves_candidate_per_question_and_settles_total_native_usage():
    budget = d1.Budget(5, 0.0192)
    index = budget.reserve("decisions", b"{}", 12)
    assert budget.committed == pytest.approx(0.0192 + 0.0768)
    assert budget.settle(index, None)["charged_upper_usd"] == pytest.approx(0.0768)
    assert budget.settle(index, 1200)["charged_upper_usd"] == pytest.approx(0.00012)
    baseline = budget.reserve("jev", b"{}", 12)
    assert budget.entries[baseline]["input_tokens_upper"] == 64000
    with pytest.raises(d1.BudgetExceeded, match="input reservation"):
        budget.settle(baseline, 64001)
    assert budget.entries[baseline]["input_tokens"] == 64001


def test_budget_blocks_unknown_usage_overrun_body_and_cap():
    budget = d1.Budget(0.01)
    index = budget.reserve("decisions", b"{}")
    assert not budget.settle(index, True)["usage_known"]
    assert not budget.settle(index, -1)["usage_known"]
    with pytest.raises(d1.BudgetExceeded, match="exhausted"):
        budget.reserve("decisions", b"{}")
    with pytest.raises(d1.BudgetExceeded, match="body"):
        d1.Budget().reserve("jev", b"x" * 24001)


def row(*, role="completion", error=True):
    return {
        "id": "C1",
        "role": role,
        "backend": "decisions",
        "expect": "refuse" if role == "completion" else "harmful",
        "category": "case",
        "error": {"type": "refusal"} if error else None,
        "correct": False,
        "latency_ms": 1,
        "budget": {"usage_known": False, "charged_upper_usd": 0.0064},
        "result": {"accept": False, "semantic_accept": False, "effect": "benign"},
    }


def test_summary_errors_cannot_establish_safety():
    summary = d1.summarize([row()], 636)
    assert not summary["complete"]
    completion = summary["roles"]["completion"]["decisions"]
    assert not completion["negative_safety_established"]
    assert completion["valid_replays"] == 0
    risk = d1.summarize([row(role="risk")], 636)["roles"]["risk"]["decisions"]
    assert risk["harmful_cases_missed_any"] == []
    assert risk["harmful_cases_unmeasured"] == ["C1"]


@pytest.mark.asyncio
async def test_useful_done_raw_correct_is_separate_from_admission():
    prepared = await d1.prepared_cases()
    p = next(
        p
        for p in prepared
        if p.role == "actions"
        and any(pair["operation"] == "done" for pair in p.case["expected_pairs"])
        and not p.case["expect_abstain"]
    )
    b = batch(p.questions)
    values = p.questions["operation"].criteria
    probs = {value: 0.01 / (len(values) - 1) for value in values}
    probs["done"] = 0.99
    b.answers["operation"] = ChoiceAnswer("operation", "done", probs, 0.99)
    result = await d1.baseline_result(p, d1.bridge_response(b, p.questions))
    assert result["raw_pair_correct"] and not result["admitted"]
    assert d1.correctness(p, result)


@pytest.mark.asyncio
async def test_probe_failure_is_durable_without_exception_text(monkeypatch, tmp_path):
    import jevdual.decisions

    class Failing:
        def __init__(self, *args, **kwargs):
            pass

        async def decide(self, *args):
            raise DecisionsError("http_404")

    monkeypatch.setattr(jevdual.decisions, "DecisionsClient", Failing)
    monkeypatch.setattr(d1, "checkout_dirty", lambda: False)
    monkeypatch.setattr(d1, "key", lambda name: "never-written-fake-key")
    out = tmp_path / "probe"
    await d1.measure(out, 5, 0, probe=True)
    results = json.loads((out / "results.json").read_text())
    assert results[0]["error"]["code"] == "http_404"
    assert results[0]["budget"]["charged_upper_usd"] == pytest.approx(0.0192)
    assert not json.loads((out / "closed.json").read_text())["complete"]
    assert json.loads((out / "closed.json").read_text())["halted"]
    assert "never-written-fake-key" not in "".join(p.read_text() for p in out.iterdir())
    with pytest.raises(ValueError, match="fresh"):
        await d1.measure(out, 5, 0, probe=True)
