"""D3 wire fairness, frozen captures, accounting, abstention and replay cadence (no paid calls)."""

from __future__ import annotations

import io
import json
from collections import Counter
from types import SimpleNamespace

import httpx
import pytest
from jevdual.decisions import DecisionBatch, DecisionsError, PredicateAnswer
from PIL import Image

from evals import d3_visual_tasks as d3


def freeze(tmp_path):
    root = tmp_path / "capture"
    root.mkdir()
    image = Image.new("RGB", (40, 30), "white")
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    data = stream.getvalue()
    (root / "neutral.png").write_bytes(data)
    cases = []
    for family_index in range(6):
        for variant, expected in (
            ("supported", True),
            ("near_miss", False),
            ("ambiguous", None),
            ("text_control", True),
        ):
            index = len(cases)
            cases.append(
                {
                    "id": f"c{index:02}",
                    "family": f"family{family_index}",
                    "variant": variant,
                    "surface": "browser_fixture" if family_index < 3 else "native_fixture",
                    "expected": expected,
                    "question": "Does the observation support the supplied bounded action?",
                    "text": f"Observed resource{index}, current revision2, supplied targetA. Previous revision1 unavailable.",
                    "images": ["neutral.png"],
                    "oracle": {"truth": expected, "secret_label": "ORACLE-NOT-WIRE"},
                    "proposal": {"target": "A", "revision": 2},
                    "recipe": {"index": index},
                    "conformance": {"passed": True},
                    "capture": {
                        "capture_ms": 11,
                        "images": [{"path": "neutral.png", "sha256": d3.sha(data), "dimensions": [40, 30]}],
                    },
                }
            )
    path = root / "manifest.json"
    path.write_text(json.dumps({"cases": cases}))
    return path, cases


def test_manifest_integrity_counts_hash_dimensions_and_wire_fairness(tmp_path):
    path, original = freeze(tmp_path)
    manifest, cases = d3.load_cases(path)
    assert cases == original and manifest["cases"] == cases
    assert d3.preflight(path)["scheduled_attempts"] == 216
    c = cases[0]
    combined = json.loads(d3.wire_body(c, "decisions_combined", path.parent))
    text = json.loads(d3.wire_body(c, "decisions_text", path.parent))
    jev = json.loads(d3.wire_body(c, "jev_text", path.parent))
    assert combined["input"][0]["content"][0]["text"] == text["input"] == jev["state"] == c["text"]
    assert combined["questions"][0]["instructions"] == jev["questions"][d3.NAME]["instructions"]
    assert combined["input"][0]["content"][1]["image_url"].startswith("data:image/png;base64,")
    assert "ORACLE-NOT-WIRE" not in str(combined)
    assert "variant" not in str(combined)
    assert "neutral.png" not in str(combined)
    (path.parent / "neutral.png").write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash"):
        d3.load_cases(path)


@pytest.mark.parametrize(
    "p,expected",
    [(0, "false"), (0.2, "false"), (0.20001, "unknown"), (0.7999, "unknown"), (0.8, "true"), (1, "true")],
)
def test_frozen_bands(p, expected):
    assert d3.band(p) == expected


@pytest.mark.parametrize("p", [True, None, float("nan"), float("inf"), -1, 1.01])
def test_malformed_finite_probabilities(p):
    with pytest.raises(ValueError, match="invalid"):
        d3.band(p)


def test_ambiguous_refusal_unknown_only_correct():
    assert d3.judged_correct({"expected": None}, "refusal")
    assert d3.judged_correct({"expected": None}, "unknown")
    assert not d3.judged_correct({"expected": None}, "error")
    assert not d3.judged_correct({"expected": None}, "true")
    assert not d3.judged_correct({"expected": False}, "refusal")


def test_d3_48k_budget_independent_of_d1_and_unknown_usage_kept():
    budget = d3.VisualBudget(5, 0.192055158)
    index = budget.reserve("decisions", b"x" * 48000)
    assert budget.settle(index, None)["charged_upper_usd"] == pytest.approx(0.0064)
    with pytest.raises(d3.BudgetExceeded, match="limit"):
        budget.reserve("decisions", b"x" * 48001)
    with pytest.raises(d3.BudgetExceeded, match="question"):
        budget.reserve("decisions", b"{}", 2)
    with pytest.raises(d3.BudgetExceeded, match="reservation"):
        budget.settle(index, 64001)
    assert budget.entries[index]["input_tokens"] == 64001
    tiny = d3.VisualBudget(0.007)
    tiny.reserve("decisions", b"{}")
    with pytest.raises(d3.BudgetExceeded, match="exhausted"):
        tiny.reserve("decisions", b"{}")


@pytest.mark.asyncio
async def test_pooled_http_actual_multimodal_48k_and_refusal_receipt():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "model": "gpt-6-luna",
                "usage": {"input_tokens": 31},
                "answers": [{"type": "refusal", "name": d3.NAME}],
            },
        )

    client = d3.VisualDecisions("opaque-test-key", transport=httpx.MockTransport(handler))
    body = json.dumps(
        {
            "model": "gpt-6-luna",
            "input": "x" * 26000,
            "questions": [{"type": "predicate", "name": d3.NAME, "instructions": "Predicate"}],
        }
    ).encode()
    try:
        with pytest.raises(DecisionsError) as failure:
            await client.call(body)
        assert failure.value.code == "refusal"
        assert failure.value.input_tokens == 31
        assert failure.value.raw["answers"][0]["type"] == "refusal"
        assert len(requests) == 1
    finally:
        await client.aclose()
    assert client._client.is_closed


def test_coverage_gap_is_not_model_wrongness_and_temporal_metadata_preserved(tmp_path):
    _, cases = freeze(tmp_path)
    cases[0]["conformance"] = {"passed": False, "reason": "driver failed"}
    coverage = d3.coverage(cases)
    assert not coverage["all_conformance_verified"]
    assert coverage["conformance_gaps"][0]["id"] == cases[0]["id"]
    recipe = d3.execution_recipe(cases[0])
    assert all(k not in recipe for k in ("expected", "oracle", "conformance"))
    assert recipe["proposal"]["revision"] == 2
    assert "Previous revision1" in recipe["text"]


@pytest.mark.asyncio
async def test_mock_full_accounting_fair_wire_replay_cadence_and_cleanup(monkeypatch, tmp_path):
    import typesafe_sdk

    path, cases = freeze(tmp_path)
    out = tmp_path / "run"
    closed, replayed, attempts = [], [], []
    probability = {c["text"]: 0.9 if c["expected"] else 0.5 if c["expected"] is None else 0.1 for c in cases}

    class Candidate:
        def __init__(self, *args):
            pass

        async def call(self, body):
            ledger = json.loads((out / "budget.json").read_text())
            assert len(ledger["attempts"]) == len(attempts) + 1
            spec = json.loads(body)
            text = spec["input"] if isinstance(spec["input"], str) else spec["input"][0]["content"][0]["text"]
            attempts.append(text)
            return DecisionBatch(
                "gpt-6-luna", {d3.NAME: PredicateAnswer(d3.NAME, probability[text])}, 100, {}, 0.001
            )

        async def aclose(self):
            closed.append("candidate")

    class Baseline:
        def __init__(self, *args, **kwargs):
            pass

        async def system_one(self, text, questions, **kwargs):
            assert len(json.loads((out / "budget.json").read_text())["attempts"]) == len(attempts) + 1
            attempts.append(text)
            return SimpleNamespace(
                model="jev-1.13.0",
                usage=SimpleNamespace(input_tokens=100),
                nouls={d3.NAME: SimpleNamespace(noul=probability[text])},
                model_dump=lambda **kwargs: {},
            )

        async def aclose(self):
            closed.append("baseline")

    async def replay(case, accepted, target):
        replayed.append((case["id"], accepted))
        return {"dispatched": accepted, "goal_met": accepted, "wrong_effect": False}

    monkeypatch.setattr(d3, "checkout_dirty", lambda: False)
    monkeypatch.setattr(d3, "committed_file", lambda _: True)
    monkeypatch.setattr(d3, "key", lambda _: "opaque-test-key")
    monkeypatch.setattr(d3, "VisualDecisions", Candidate)
    monkeypatch.setattr(typesafe_sdk, "AsyncTypeSafeClient", Baseline)
    monkeypatch.setattr(d3, "replay", replay)
    await d3.run(path, out, 0.192055158)
    rows = json.loads((out / "results.json").read_text())
    assert len(rows) == len(attempts) == 216
    assert len(replayed) == 72
    assert Counter(i for i, _ in replayed) == {c["id"]: 3 for c in cases}
    assert closed == ["candidate", "baseline"]
    assert all(r["capture_to_judgment_estimate_ms"] >= 11 for r in rows)
    summary = json.loads((out / "summary.json").read_text())
    assert summary["complete"]
    assert all(len(summary["arms"][arm]["all_three_correct"]) == 24 for arm in d3.ARMS)
    budget = json.loads((out / "budget.json").read_text())
    assert budget["reserved_or_usage_upper_usd"] < 5
    assert all(e["usage_known"] for e in budget["attempts"])
    with pytest.raises(ValueError, match="fresh"):
        await d3.run(path, out, 0.2)


@pytest.mark.asyncio
async def test_halt_contract_rejection_durable_unknown_reservation(monkeypatch, tmp_path):
    import typesafe_sdk

    path, _ = freeze(tmp_path)
    out = tmp_path / "failed-run"

    class Candidate:
        def __init__(self, *args):
            pass

        async def call(self, body):
            raise DecisionsError("http_422", provider_error={"code": "unsupported_contract"})

        async def aclose(self):
            pass

    class Baseline:
        def __init__(self, *args, **kwargs):
            pass

        async def system_one(self, *args, **kwargs):
            raise RuntimeError("opaque-test-key must not appear")

        async def aclose(self):
            pass

    monkeypatch.setattr(d3, "checkout_dirty", lambda: False)
    monkeypatch.setattr(d3, "committed_file", lambda _: True)
    monkeypatch.setattr(d3, "key", lambda _: "opaque-test-key")
    monkeypatch.setattr(d3, "VisualDecisions", Candidate)
    monkeypatch.setattr(typesafe_sdk, "AsyncTypeSafeClient", Baseline)

    async def replay(case, accepted, out):
        return {"dispatched": False}

    monkeypatch.setattr(d3, "replay", replay)
    await d3.run(path, out, 0.192055158)
    closed = json.loads((out / "closed.json").read_text())
    assert closed["halted"] == "provider contract/account access failure"
    assert closed["attempts"] <= 2
    assert not closed["complete"]
    budget = json.loads((out / "budget.json").read_text())
    assert all(not entry["usage_known"] for entry in budget["attempts"])
    assert "opaque-test-key" not in "".join(p.read_text() for p in out.iterdir())


def test_ambiguous_operational_false_is_safe_rejection_not_primary_epistemic_correct(tmp_path):
    _, cases = freeze(tmp_path)
    case = next(case for case in cases if case["expected"] is None)
    rows = [
        {
            "id": case["id"],
            "family": case["family"],
            "surface": case["surface"],
            "arm": "decisions_combined",
            "repeat": repeat,
            "band": "false",
            "correct": d3.judged_correct(case, "false"),
            "request_ms": 2,
        }
        for repeat in range(3)
    ]
    summary = d3.summarize(rows, cases)["arms"]["decisions_combined"]
    assert case["id"] not in summary["all_three_correct"]
    assert case["id"] in summary["ambiguous_all_three_safe_nonacceptance"]
    assert summary["ambiguous_safe_nonacceptance_replays"] == {"false": 3, "unknown": 0, "refusal": 0}
