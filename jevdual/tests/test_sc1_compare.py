"""SC1 accounting and matched fixture evidence. All transports are offline fakes."""

from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace

import pytest
from jevdual.system1 import prepare_request
from typesafe_sdk import Noul

from evals import d1_compare as d1
from evals import sc1_compare as sc1


def test_durable_reservation_settlement_and_explicit_prior_accounting(tmp_path):
    ledger, out = tmp_path / "sc1-budget.json", tmp_path / "sc1-first"
    budget = sc1.PackageBudget(ledger, out, 1)
    out.mkdir()
    index = budget.reserve("subq", b"{}", 12)
    assert json.loads(ledger.read_text())["attempts"][0]["charged_upper_usd"] == pytest.approx(0.0384)
    assert budget.settle(index, None)["charged_upper_usd"] == pytest.approx(0.0384)
    with pytest.raises(ValueError, match="settled"):
        budget.settle(index, 0)
    sc1.atomic_json(out / "budget.json", budget.snapshot())
    budget.close()
    with pytest.raises(ValueError, match="prior-run"):
        sc1.PackageBudget(ledger, tmp_path / "sc1-next", 1)
    next_budget = sc1.PackageBudget(ledger, tmp_path / "sc1-next", 1, [out])
    assert next_budget.committed == pytest.approx(0.0384)
    assert next_budget.settle(next_budget.reserve("jev", b"{}", 12), 1000)[
        "charged_upper_usd"
    ] == pytest.approx(0.000042)
    next_budget.close()


def test_interrupted_attempt_keeps_durable_reservation_and_refuses_stale_lock(tmp_path):
    ledger = tmp_path / "sc1-budget.json"
    budget = sc1.PackageBudget(ledger, tmp_path / "sc1-first", 1)
    budget.reserve("subq", b"request", 2)
    with pytest.raises(ValueError, match="unresolved"):
        budget.close()
    stored = json.loads(ledger.read_text())
    assert stored["attempts"][0]["state"] == "reserved"
    assert stored["attempts"][0]["charged_upper_usd"] == pytest.approx(0.0064)
    with pytest.raises(FileExistsError):
        sc1.PackageBudget(ledger, tmp_path / "sc1-other", 1)
    # Even losing only the lock cannot erase the ledger's active run/reservation.
    budget.release()
    with pytest.raises(ValueError, match="unresolved"):
        sc1.PackageBudget(ledger, tmp_path / "sc1-other", 1)


def test_no_ledger_reset_or_prior_receipt_tampering(tmp_path):
    out, ledger = tmp_path / "sc1-first", tmp_path / "sc1-budget.json"
    out.mkdir()
    with pytest.raises(ValueError, match="original package ledger"):
        sc1.PackageBudget(ledger, tmp_path / "sc1-other", 1)
    out.rmdir()
    budget = sc1.PackageBudget(ledger, out, 1)
    out.mkdir()
    budget.settle(budget.reserve("jev", b"{}", 1), 100)
    sc1.atomic_json(out / "budget.json", {"attempts": []})
    budget.close()
    with pytest.raises(ValueError, match="disagree"):
        sc1.PackageBudget(ledger, tmp_path / "sc1-other", 1, [out])


def test_cap_applies_before_dispatch_and_overshoot_is_preserved(tmp_path):
    ledger = tmp_path / "sc1-budget.json"
    budget = sc1.PackageBudget(ledger, tmp_path / "sc1-first", 0.004)
    first = budget.reserve("jev", b"{}", 1)
    with pytest.raises(sc1.BudgetExceeded, match="aggregate"):
        budget.reserve("subq", b"{}", 1)
    assert len(json.loads(ledger.read_text())["attempts"]) == 1
    with pytest.raises(sc1.BudgetExceeded, match="exceeded reservation"):
        budget.settle(first, 64001)
    assert json.loads(ledger.read_text())["attempts"][0]["input_tokens"] == 64001
    budget.close()
    with pytest.raises(ValueError, match="at most"):
        sc1.PackageBudget(ledger, tmp_path / "sc1-next", 1.00001)


@pytest.mark.parametrize("usage", [None, True, -1, 2.5, "100"])
def test_invalid_usage_keeps_unknown_reservation(tmp_path, usage):
    budget = sc1.PackageBudget(tmp_path / "sc1-budget.json", tmp_path / "sc1-first", 1)
    index = budget.reserve("jev", b"{}", 1)
    result = budget.settle(index, usage)
    assert not result["usage_known"]
    assert result["charged_upper_usd"] == pytest.approx(0.002688)
    budget.close()


@pytest.mark.asyncio
async def test_actual_wire_preserves_fixture_projection_and_schedule():
    prepared = await d1.prepared_cases()
    frozen = sc1.freeze(prepared, sc1.configs())
    assert len(frozen) == 106
    assert max(len(p.questions) for p in prepared) == 12
    structured_instructions = structured_criteria = singleton = 0
    for p, record in zip(prepared, frozen, strict=True):
        request = prepare_request(sc1.configs()["subq"], p.state, p.questions)
        assert record["wire"]["subq"]["sha256"] == hashlib.sha256(request.body).hexdigest()
        assert json.loads(request.body)["state"] == p.state
        for name, question in d1.question_data(p.questions).items():
            structured_instructions += isinstance(question.get("instructions"), dict)
            structured_criteria += sum(isinstance(v, dict) for v in (question.get("criteria") or {}).values())
            if name in request.forced_answers:
                singleton += 1
                assert len(question["criteria"]) == 1
                assert request.answer_sources[name] == "forced_single_option"
            else:
                assert request.wire_questions[name] == question
    assert (structured_instructions, structured_criteria) == (82, 100)
    assert singleton > 0
    plan = sc1.schedule(prepared)
    assert len(plan) == 636
    assert plan == sc1.schedule(prepared)
    assert [p.role for p, _, _ in plan] == sorted([p.role for p, _, _ in plan], key=sc1.ROLES.index)
    for i in range(0, len(plan), 2):
        p, repeat, backend = plan[i]
        p2, repeat2, backend2 = plan[i + 1]
        assert p is p2 and repeat == repeat2 and {backend, backend2} == {"jev", "subq"}


def fixture(identifier="negative", expectation="refuse"):
    return SimpleNamespace(
        role="completion", case={"id": identifier, "expect": expectation, "category": "case"}
    )


def row(
    identifier="negative",
    backend="subq",
    repeat=0,
    error=False,
    accept=False,
    semantic=False,
    latency=1,
    cold=False,
):
    return {
        "id": identifier,
        "role": "completion",
        "backend": backend,
        "repeat": repeat,
        "category": "case",
        "error": {"type": "Failure"} if error else None,
        "correct": not accept,
        "budget": {"charged_upper_usd": 0.001, "usage_known": True},
        "result": {"accept": accept, "semantic_accept": semantic},
        "request_latency_ms": latency,
        "total_latency_ms": latency + 1,
        "cold": cold,
    }


def test_missing_or_error_negative_cannot_establish_safety_and_semantic_failures_visible():
    prepared = [fixture(), fixture("missing")]
    rows = [row(repeat=i) for i in range(3)]
    summary = sc1.summarize(rows, prepared)["roles"]["completion"]["subq"]
    assert not summary["negative_safety_established"]
    assert summary["negative_cases_unmeasured"] == ["missing"]
    summary = sc1.summarize([row(repeat=i, error=i == 2) for i in range(3)], [fixture()])
    assert not summary["roles"]["completion"]["subq"]["negative_safety_established"]
    summary = sc1.summarize([row(repeat=i, semantic=i == 2) for i in range(3)], [fixture()])
    snap = summary["roles"]["completion"]["subq"]
    assert snap["negative_cases_accept_any"] == []
    assert snap["negative_cases_semantic_accept_any"] == ["negative"]
    assert not snap["negative_safety_established"]


def test_ordinary_median_p95_paired_common_success_cold_warm_and_positive_coverage():
    prepared = [fixture(), fixture("positive", "accept")]
    rows = [
        row(repeat=i, backend=backend, latency=(i + 1) * (2 if backend == "subq" else 1), cold=i == 0)
        for i in range(3)
        for backend in ("jev", "subq")
    ]
    rows += [row("positive", repeat=i, accept=i != 2, semantic=True) for i in range(3)]
    # One provider failed on this pair: it must not bias common-success timings.
    rows += [row("positive", backend="jev", error=True, latency=200)]
    summary = sc1.summarize(rows, prepared)["roles"]["completion"]
    assert sc1.percentile([1, 2, 3, 4]) == {"n": 4, "median_ms": 2.5, "p95_ms": 4, "sum_ms": 10}
    pair = summary["paired_latency"]
    assert summary["jev"]["latency"]["success"]["request_latency_ms"]["sum_ms"] == 6
    assert summary["jev"]["latency"]["success"]["total_latency_ms"]["sum_ms"] == 9
    assert summary["jev"]["latency"]["error"]["request_latency_ms"]["sum_ms"] == 200
    assert pair["all"]["common_success_pairs"] == 3
    assert pair["all"]["request_latency_ms"]["median_subq_over_jev"] == 2
    assert pair["warm_only"]["common_success_pairs"] == 2
    assert summary["subq"]["positive_cases_accept_any"] == ["positive"]
    assert summary["subq"]["positive_cases_accept_all_three"] == []
    assert summary["subq"]["positive_cases_semantic_accept_all_three"] == ["positive"]


def test_artifact_redacts_nested_keys_values_and_invalid_numbers(tmp_path):
    secret = 'sk-secret-"quoted'
    path = tmp_path / "receipt.json"
    sc1.atomic_json(path, {secret: {"error": secret, "number": float("nan")}}, (secret,))
    encoded = path.read_text()
    assert secret not in encoded
    assert json.loads(encoded) == {"[REDACTED]": {"error": "[REDACTED]", "number": "[NONFINITE]"}}


@pytest.mark.asyncio
@pytest.mark.parametrize("source_changed", [False, True])
async def test_access_failure_or_source_change_stops_without_retry(tmp_path, monkeypatch, source_changed):
    root = tmp_path
    results = root / "results"
    results.mkdir()
    monkeypatch.setattr(sc1, "ROOT", root)
    monkeypatch.setattr(sc1, "LEDGER", results / "sc1-budget.json")
    monkeypatch.setattr(d1, "checkout_dirty", lambda: False)
    monkeypatch.setattr(sc1, "head", lambda: "frozen")
    monkeypatch.setattr(sc1, "tracked_source_changed", lambda: source_changed)
    monkeypatch.setattr(sc1, "provenance", lambda _: {"commit": "frozen"})
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-jev-secret")
    monkeypatch.setenv("SUBQ_API_KEY", "test-snap-secret")
    p = SimpleNamespace(
        role="completion",
        case={"id": "negative", "category": "test", "expect": "refuse"},
        state={"test": "state"},
        questions={"complete": Noul()},
    )

    async def prepared():
        return [p]

    monkeypatch.setattr(d1, "prepared_cases", prepared)
    monkeypatch.setattr(sc1, "schedule", lambda _: [(p, 0, "subq"), (p, 0, "jev")])

    class AccessError(Exception):
        status_code = 402

    class Client:
        calls = 0

        def __init__(self):
            self.last_receipt = {}

        async def system_one(self, *args, **kwargs):
            self.calls += 1
            budget = json.loads(sc1.LEDGER.read_text())
            assert budget["attempts"][-1]["state"] == "reserved"
            raise AccessError("test-snap-secret must not reach artifacts")

        async def aclose(self):
            pass

    clients = []

    def create(*args, **kwargs):
        client = Client()
        clients.append(client)
        return client

    monkeypatch.setattr(sc1, "create_s1_client", create)
    out = results / "sc1-test"
    result = await sc1.measure(out, 1)
    assert sum(c.calls for c in clients) == (0 if source_changed else 1)
    assert not result["complete"]
    saved = json.loads((out / "results.json").read_text())
    if source_changed:
        assert saved == []
        assert json.loads(sc1.LEDGER.read_text())["attempts"] == []
        return
    assert saved[0]["error"] == {"type": "AccessError", "http_status": 402}
    assert not saved[0]["budget"]["usage_known"]
    assert saved[0]["budget"]["charged_upper_usd"] == pytest.approx(0.0032)
    assert not sc1.LEDGER.with_suffix(".lock").exists()
    assert "test-snap-secret" not in "".join(p.read_text() for p in out.rglob("*.json"))
