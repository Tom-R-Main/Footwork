"""Offline tests of D2 evidence separation, image contract and accounting."""
import base64
import io
import json
from types import SimpleNamespace

import httpx
import pytest
from jevdual.decisions import DecisionsError
from PIL import Image

from evals import d2_visual as d2


def test_frozen_pairs_have_identical_text_questions_distinct_pixels_no_metadata():
    cases = d2.load_cases()
    assert len(cases) == 12
    for _, *rest in d2.DEFINITIONS:
        assert len(rest) == 4
    for category, *_ in d2.DEFINITIONS:
        pair = [c for c in cases if c["category"] == category]
        assert {c["expected"] for c in pair} == {True, False}
        assert pair[0]["text"] == pair[1]["text"]
        assert d2.instructions(pair[0]) == d2.instructions(pair[1])
        assert d2.wire_body(pair[0], "jev_text") == d2.wire_body(pair[1], "jev_text")
        assert d2.wire_body(pair[0], "decisions_text") == d2.wire_body(pair[1], "decisions_text")
        assert pair[0]["sha256"] != pair[1]["sha256"]
        for case in pair:
            raw = (d2.FIXTURES / case["file"]).read_bytes()
            # Authored PNG bytes are immutable; encoding/font libraries can vary by host.
            assert d2.sha(raw) == case["sha256"]
            with Image.open(io.BytesIO(raw)) as image:
                assert image.size == (480, 300)
                assert not image.info


def test_authored_cases_load_without_using_the_current_renderer(monkeypatch):
    def different_renderer():
        raise AssertionError("a frozen corpus must not be regenerated during readback")

    monkeypatch.setattr(d2, "generate_manifest", different_renderer)
    assert len(d2.load_cases()) == 12


@pytest.mark.parametrize("field,value", [("expected", False), ("text", "altered context"),
                                          ("sha256", "0" * 64)])
def test_altered_manifest_cannot_change_the_frozen_oracle(monkeypatch, tmp_path, field, value):
    manifest = json.loads((d2.FIXTURES / "manifest.json").read_text())
    manifest["cases"][0][field] = value
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(d2, "FIXTURES", tmp_path)
    with pytest.raises(ValueError, match="manifest integrity"):
        d2.load_cases()


def test_altered_png_is_rejected_against_the_authored_digest(monkeypatch, tmp_path):
    import shutil

    for path in d2.FIXTURES.iterdir():
        if path.is_file():
            shutil.copyfile(path, tmp_path / path.name)
    image = tmp_path / "f00.png"
    image.write_bytes(image.read_bytes() + b"altered")
    monkeypatch.setattr(d2, "FIXTURES", tmp_path)
    with pytest.raises(ValueError, match="PNG integrity"):
        d2.load_cases()


@pytest.mark.parametrize("category", [definition[0] for definition in d2.DEFINITIONS])
def test_current_renderer_keeps_the_pixel_input_format(category):
    for expected in (True, False):
        with Image.open(io.BytesIO(d2.render(category, expected))) as image:
            assert image.size == (480, 300)
            assert image.format == "PNG"
            assert not image.info


def test_wire_inputs_do_not_include_oracle_ids_or_image_paths():
    for case in d2.load_cases():
        for arm in d2.ARMS:
            raw = d2.wire_body(case, arm)
            assert len(raw) <= 24_000
            body = json.loads(raw)
            assert case["id"] not in raw.decode()
            assert "expected" not in raw.decode()
            assert case["file"] not in raw.decode()
            if "image" in arm or arm.endswith("combined"):
                assert set(body) == {"model", "input", "questions"}
                content = body["input"][0]["content"]
                assert body["input"][0]["role"] == "user"
                if arm == "decisions_image":
                    assert len(content) == 1
                else:
                    assert content[0] == {"type": "input_text", "text": case["text"]}
                image = content[-1]
                assert set(image) == {"type", "image_url"}
                assert image["type"] == "input_image"
                assert image["image_url"].startswith("data:image/png;base64,")
                data = base64.b64decode(image["image_url"].split(",", 1)[1], validate=True)
                assert d2.sha(data) == case["sha256"]
            if arm != "jev_text":
                assert body["questions"] == [{"name": "visible_state", "type": "predicate",
                                              "instructions": d2.instructions(case)}]


@pytest.mark.parametrize("p,expected", [(0, "false"), (.2, "false"), (.20001, "unknown"),
                                          (.79999, "unknown"), (.8, "true"), (1, "true")])
def test_frozen_native_predicate_bands(p, expected):
    assert d2.band(p) == expected


@pytest.mark.parametrize("p", [-.1, 1.1, float("nan"), float("inf"), True, "0.9"])
def test_invalid_native_predicates_never_establish_confidence(p):
    with pytest.raises(ValueError):
        d2.band(p)


def full_rows():
    return [{"id": c["id"], "expected": c["expected"], "arm": arm, "repeat": repeat,
             "band": "true" if c["expected"] else "false", "correct": True, "latency_ms": 20 + repeat}
            for c, repeat, arm in d2.schedule(d2.load_cases())]


def test_primary_requires_all_three_errors_unknowns_and_safety_reported():
    cases, rows = d2.load_cases(), full_rows()
    for row in rows:
        if row["arm"].endswith("text"):
            row.update(band="unknown", correct=False)
    summary = d2.summarize(rows, cases)
    assert summary["visual_rule_met"]
    assert summary["combined_gain_cases"] == 12
    assert summary["arms"]["decisions_text"]["unknown"] == 36
    target = next(r for r in rows if r["arm"] == "decisions_combined" and not r["expected"])
    target.update(band="true", correct=False)
    assert not d2.summarize(rows, cases)["visual_rule_met"]
    target.pop("band")
    target["error"] = {"type": "refusal"}
    result = d2.summarize(rows, cases)
    assert result["arms"]["decisions_combined"]["errors"] == 1
    assert result["arms"]["decisions_combined"]["all_three_correct_confident"] == 11
    assert not result["visual_rule_met"]
    assert not d2.summarize(rows[:-1], cases)["visual_rule_met"]


def test_schedule_reproducible_paired_and_all_attempts_once():
    cases = d2.load_cases()
    scheduled = d2.schedule(cases)
    assert scheduled == d2.schedule(cases)
    assert len(scheduled) == 144
    assert len({(c["id"], repeat, arm) for c, repeat, arm in scheduled}) == 144
    for offset in range(0, len(scheduled), 8):
        chunk = scheduled[offset:offset + 8]
        assert len({c["category"] for c, _, _ in chunk}) == 1
        assert {c["expected"] for c, _, _ in chunk} == {True, False}
        assert len({repeat for _, repeat, _ in chunk}) == 1


async def test_image_native_contract_pool_closure_and_secret_safe_http_error():
    seen = []
    def transport(request):
        seen.append(request)
        assert request.url == "https://api.openai.com/v1/decisions"
        assert request.headers["authorization"] == "Bearer opaque-test-key"
        assert json.loads(request.content)["input"][0]["content"][-1]["type"] == "input_image"
        return httpx.Response(200, json={"model": "gpt-6-luna", "usage": {"input_tokens": 40},
            "answers": [{"name": "visible_state", "type": "predicate", "probability": .9}]})
    client = d2.ImageDecisionsClient("opaque-test-key", transport=httpx.MockTransport(transport))
    body = d2.image_body(d2.load_cases()[0], True)
    a = await client.decide(body)
    b = await client.decide(body)
    assert a.answers["visible_state"].probability == b.answers["visible_state"].probability == .9
    assert a.input_tokens == 40 and len(seen) == 2
    await client.aclose()
    assert client._client.is_closed

    bad = d2.ImageDecisionsClient("opaque-test-key", transport=httpx.MockTransport(lambda req:
        httpx.Response(400, json={"error": {"message": "opaque-test-key failed", "code": "invalid"}})))
    with pytest.raises(DecisionsError) as caught:
        await bad.decide(body)
    assert caught.value.code == "http_400"
    assert caught.value.provider_error["message"] == "[REDACTED] failed"
    assert "opaque-test-key" not in str(caught.value)
    assert caught.value.raw is None
    await bad.aclose()


@pytest.mark.parametrize("raw,code", [
    ({"model": "gpt-6-luna", "answers": [{"name": "visible_state", "type": "refusal"}]}, "refusal"),
    ({"model": "gpt-6-luna", "answers": [{"name": "visible_state", "type": "predicate", "probability": 2}]},
     "probability"),
    ({"model": "gpt-6-luna", "answers": []}, "answer_set"),
])
async def test_image_rejects_native_refusal_and_malformed(raw, code):
    client = d2.ImageDecisionsClient("opaque", transport=httpx.MockTransport(lambda req:
        httpx.Response(200, json=raw)))
    try:
        with pytest.raises(DecisionsError) as caught:
            await client.decide(d2.image_body(d2.load_cases()[0], False))
        assert caught.value.code == code
    finally:
        await client.aclose()


def test_budget_reserves_per_predicate_and_rejects_over_cap():
    budget = d2.Budget(5, prior_cost=4.995)
    with pytest.raises(d2.BudgetExceeded):
        budget.reserve("decisions", d2.image_body(d2.load_cases()[0], True))
    assert not budget.entries
    budget = d2.Budget(5, prior_cost=2)
    index = budget.reserve("decisions", d2.image_body(d2.load_cases()[0], True))
    assert budget.entries[index]["reserved_usd"] == .0064
    budget.settle(index, None)
    assert budget.committed == 2.0064
    budget.settle(index, 100)
    assert budget.committed == 2.00001


async def test_run_flushes_rejection_retains_unknown_budget_and_closes_clients(tmp_path, monkeypatch):
    import typesafe_sdk
    closed = []
    class Baseline:
        def __init__(self, **kwargs):
            pass
        async def system_one(self, *args, **kwargs):
            return SimpleNamespace(model="jev-1.13.0", usage=SimpleNamespace(input_tokens=10),
                nouls={"visible_state": SimpleNamespace(noul=.5)}, model_dump=lambda **kw: {"model": "jev-1.13.0"})
        async def aclose(self):
            closed.append("jev")
    class Candidate:
        def __init__(self, *args, **kwargs):
            pass
        async def decide(self, *args):
            raise DecisionsError("http_400", provider_error={"code": "invalid"})
        async def aclose(self):
            closed.append("candidate")
    class Images(Candidate):
        async def aclose(self):
            closed.append("images")
    monkeypatch.setattr(typesafe_sdk, "AsyncTypeSafeClient", Baseline)
    monkeypatch.setattr(d2, "DecisionsClient", Candidate)
    monkeypatch.setattr(d2, "ImageDecisionsClient", Images)
    monkeypatch.setattr(d2, "checkout_dirty", lambda: False)
    monkeypatch.setattr(d2, "key", lambda name: "opaque")
    out = tmp_path / "run"
    await d2.measure(out, 5, .2)
    rows = json.loads((out / "results.json").read_text())
    assert rows[-1]["error"]["code"] == "http_400"
    assert not rows[-1]["correct"]
    assert rows[-1]["budget"]["usage_known"] is False
    budget = json.loads((out / "budget.json").read_text())
    assert budget["prior_cost_upper_usd"] == .2
    assert budget["attempts"][-1]["charged_upper_usd"] == .0064
    assert len(closed) == 3
    summary = json.loads((out / "summary.json").read_text())
    assert summary["halted"] == "HTTP contract or account request rejected"
    assert not summary["complete"] and not summary["visual_rule_met"]
    with pytest.raises(ValueError):
        await d2.measure(out, 5, .2)


def test_latency_median_even_sample_includes_error_time():
    case = d2.load_cases()[0]
    rows = [{"id": case["id"], "expected": True, "arm": "decisions_combined",
             "correct": index == 0, "latency_ms": latency,
             **({"error": {"type": "refusal"}} if index else {})}
            for index, latency in enumerate((10, 90))]
    report = d2.summarize(rows, d2.load_cases())["arms"]["decisions_combined"]
    assert report["median_ms"] == 50
    assert report["p95_ms"] == 90
    assert report["errors"] == 1
