"""Offline image transport and durable-budget contracts; no remote requests."""
import asyncio
import json
import time
from dataclasses import replace
from io import BytesIO

import httpx
import pytest
from jevdual.decisions import ENDPOINT, MODEL
from jevdual.visual_checks import (
    QUESTIONS,
    ResourceImage,
    VisualCheckBudget,
    VisualCheckEvidence,
    VisualCheckRequest,
)
from jevdual.visual_decisions import VisualCallLedger, VisualDecisionsClient, VisualLedgerError
from jevdual.visual_evidence import Bounds, Surface, bind_visual
from PIL import Image


def request():
    buffer = BytesIO()
    Image.new("RGB", (80, 60), "white").save(buffer, format="PNG")
    png = buffer.getvalue()
    capture = bind_visual(
        png=png, surface=Surface("native", pid=1, window_id=2), observation_id="o1",
        captured_at="2026-10-08T12:00:00+00:00", viewport=Bounds(0, 0, 80, 60),
        target_id="17", target_token="opaque-token", target_bounds=Bounds(1, 1, 10, 10),
        operation="inspect", postcondition="appearance assessment",
    )
    now = time.monotonic()
    evidence = VisualCheckEvidence(capture, "generation1", now - 1, now,
                                   ("reference",), reference=ResourceImage(png, "reference", "v1"))
    return VisualCheckRequest("r1", "document_reference_match", "Reference match", "v1",
                              "generation1", now + 30, evidence, disclosure_allowed=True)


def response(**overrides):
    return {"model": MODEL, "answers": [{"name": "required", "type": "predicate", "probability": 0.87}],
            "usage": {"input_tokens": 500}, **overrides}


async def call(tmp_path, *, req=None, handler=None, ledger=None, current=lambda: True):
    seen = []

    async def dispatch(message):
        seen.append(message)
        return await handler(message) if handler else httpx.Response(200, json=response())

    async with httpx.AsyncClient(transport=httpx.MockTransport(dispatch)) as http:
        client = VisualDecisionsClient("test-key", client=http)
        result = await client.check(req or request(), ledger or VisualCallLedger(tmp_path / "ledger.json"),
                                    is_current=current)
    return result, seen


async def test_official_wire_single_predicate_identity_and_no_authority(tmp_path):
    req = request()
    result, seen = await call(tmp_path, req=req)
    assert len(seen) == 1 and str(seen[0].url) == ENDPOINT
    body = json.loads(seen[0].content)
    assert body["model"] == MODEL
    assert body["questions"] == [{"type": "predicate", "name": "required",
                                   "instructions": QUESTIONS[req.role]}]
    content = body["input"][0]["content"]
    assert content[0] == {"type": "input_text", "text": req.provider_input()}
    assert len(content) == 3
    assert all(item["image_url"].startswith("data:image/png;base64,") for item in content[1:])
    assert "opaque-token" not in seen[0].content.decode()
    assert result.status == "valid" and result.p == 0.87
    assert result.request_digest == req.digest and result.evidence_digest == req.evidence.digest
    assert result.requested_model == result.returned_model == MODEL
    assert len(result.prompt_sha256) == 64 and result.phases_ms
    assert result.to_dict()["execution_authority"] is False
    assert "test-key" not in json.dumps(result.to_dict())


@pytest.mark.parametrize("change,reason", [
    ({"role": "text_only"}, "text_route"), ({"role": "icon_approval"}, "unsupported_role"),
    ({"disclosure_allowed": False}, "pixels_withheld"),
    ({"budget": VisualCheckBudget(max_bytes=1)}, "request_too_large"),
    ({"budget": VisualCheckBudget(max_bytes=4_000_001)}, "unsupported_budget"),
    ({"budget": VisualCheckBudget(max_input_tokens=64_001)}, "unsupported_budget"),
])
async def test_no_dispatch_for_unsupported_or_undisclosed_request(tmp_path, change, reason):
    result, seen = await call(tmp_path, req=replace(request(), **change))
    assert result.status == "unavailable" and result.reason == reason
    assert seen == [] and not (tmp_path / "ledger.json").exists()


@pytest.mark.parametrize("current", [lambda: False, lambda: None])
async def test_generation_refusal_before_dispatch(tmp_path, current):
    result, seen = await call(tmp_path, current=current)
    assert result.status == "invalidated" and seen == []


async def test_generation_callback_failure_fails_closed(tmp_path):
    def current():
        raise RuntimeError("sensitive driver detail")
    result, seen = await call(tmp_path, current=current)
    assert result.status == "invalidated" and seen == []


async def test_large_original_png_uses_explicit_budget_without_pixel_modification(tmp_path):
    req = request()
    buffer = BytesIO()
    Image.effect_noise((512, 512), 80).save(buffer, format="PNG")
    png = buffer.getvalue()
    capture = bind_visual(
        png=png, surface=Surface("native", pid=1, window_id=2), observation_id="large",
        captured_at="2026-10-08T12:00:00+00:00", viewport=Bounds(0, 0, 512, 512),
        target_id="17", target_token="opaque", target_bounds=Bounds(1, 1, 10, 10),
        operation="inspect", postcondition="appearance assessment",
    )
    req = replace(req, evidence=replace(req.evidence, capture=capture),
                  budget=replace(req.budget, max_bytes=4_000_000))
    result, seen = await call(tmp_path, req=req)
    assert result.status == "valid" and len(seen[0].content) > 48_000
    import base64
    wire_png = json.loads(seen[0].content)["input"][0]["content"][1]["image_url"].split(",", 1)[1]
    assert base64.b64decode(wire_png) == png


@pytest.mark.parametrize("raw,reason", [
    ({"model": "other-model"}, "response_model"),
    ({"model": "test-key"}, "response_model"),
    ({"model": {"unexpected": True}}, "response_model"),
    ({"answers": []}, "answer_set"),
    ({"answers": [{"name": "wrong", "type": "predicate", "probability": .9}]}, "answer_set"),
    ({"answers": [{"name": "required", "type": "predicate", "probability": True}]}, "probability"),
    ({"usage": {"input_tokens": True}}, "usage"),
    ({"usage": {"input_tokens": 64_001}}, "usage_exceeds_reservation"),
])
async def test_strict_response_does_not_admit_malformed_answers(tmp_path, raw, reason):
    async def handler(message):
        return httpx.Response(200, json=response(**raw))
    result, seen = await call(tmp_path, handler=handler)
    assert result.status == "invalid_response" and result.reason == reason and result.p is None
    assert len(seen) == 1 and "test-key" not in json.dumps(result.to_dict())


async def test_required_head_refusal_retains_native_status(tmp_path):
    async def handler(message):
        return httpx.Response(200, json=response(answers=[{"name": "required", "type": "refusal"}]))
    result, seen = await call(tmp_path, handler=handler)
    assert result.status == "refusal" and result.p is None and len(seen) == 1


@pytest.mark.parametrize("code", [302, 401, 429, 500])
async def test_http_errors_never_redirect_retry_or_echo_provider(tmp_path, code):
    async def handler(message):
        return httpx.Response(code, content=b"test-key secret pixels", headers={"Location": "https://example.com"})
    result, seen = await call(tmp_path, handler=handler)
    assert result.status == "error" and result.reason == f"http_{code}" and len(seen) == 1
    assert result.input_tokens is None
    assert json.loads((tmp_path / "ledger.json").read_text())["entries"][0]["tokens"] == 64_000


@pytest.mark.parametrize("data", [b"not-json", b'{"model":"gpt-6-luna","model":"gpt-6-luna"}', b"x" * 65_537])
async def test_invalid_or_oversized_body_is_bounded(tmp_path, data):
    async def handler(message):
        return httpx.Response(200, content=data)
    result, seen = await call(tmp_path, handler=handler)
    assert result.status == "invalid_response" and result.p is None and len(seen) == 1


async def test_network_error_is_safe_and_reserved(tmp_path):
    async def handler(message):
        raise httpx.ConnectError("test-key private endpoint", request=message)
    result, seen = await call(tmp_path, handler=handler)
    assert result.status == "error" and result.reason == "network" and len(seen) == 1


async def test_timeout_retains_unknown_cost_and_no_retry(tmp_path, monkeypatch):
    from types import SimpleNamespace

    req = request()
    now = time.monotonic()
    # The contract under test is an in-flight timeout. Filesystem scheduling
    # before dispatch must not turn it into the separate pre-dispatch expiry case.
    # Freeze only the producer's clock; asyncio's real timeout still runs.
    monkeypatch.setattr("jevdual.visual_decisions.time", SimpleNamespace(monotonic=lambda: now))
    req = replace(req, deadline_monotonic=now + .015)
    async def handler(message):
        await asyncio.sleep(.05)
        return httpx.Response(200, json=response())
    result, seen = await call(tmp_path, req=req, handler=handler)
    assert result.status == "timeout" and result.p is None and len(seen) == 1
    entry = json.loads((tmp_path / "ledger.json").read_text())["entries"][0]
    assert not entry["settled"] and entry["cost"] == pytest.approx(.0064)


async def test_changed_generation_after_response_never_returns_probability(tmp_path):
    current = True
    async def handler(message):
        nonlocal current
        current = False
        return httpx.Response(200, json=response())
    result, _ = await call(tmp_path, handler=handler, current=lambda: current)
    assert result.status == "invalidated" and result.p is None and result.input_tokens == 500


async def test_unknown_usage_is_not_zero_and_changed_id_wording_cannot_retry(tmp_path):
    req = request()
    ledger = VisualCallLedger(tmp_path / "ledger.json", max_calls=2, max_input_tokens=128_000, max_cost_usd=.0128)
    async def handler(message):
        return httpx.Response(200, json=response(usage=None))
    first, _ = await call(tmp_path, req=req, ledger=ledger, handler=handler)
    second, seen = await call(tmp_path, req=replace(req, request_id="r2", criterion="Ask again"), ledger=ledger)
    assert first.status == "valid" and first.input_tokens is None
    assert second.status == "budget_exhausted" and second.reason == "duplicate_evidence" and seen == []
    assert json.loads(ledger.path.read_text())["entries"][0]["cost"] == pytest.approx(.0064)


async def test_durable_reservation_is_present_before_network(tmp_path):
    async def handler(message):
        state = json.loads((tmp_path / "ledger.json").read_text())
        assert len(state["entries"]) == 1 and not state["entries"][0]["settled"]
        return httpx.Response(200, json=response())
    await call(tmp_path, handler=handler)
    assert json.loads((tmp_path / "ledger.json").read_text())["entries"][0]["cost"] == pytest.approx(.00005)


async def test_existing_empty_ledger_never_resets_a_charged_workflow(tmp_path):
    ledger = VisualCallLedger(tmp_path / "ledger.json")
    ledger.reserve(request())
    ledger.path.write_bytes(b"")  # an interrupted/truncated persisted budget
    result, seen = await call(tmp_path, ledger=ledger)
    assert seen == []
    assert result.status == "budget_exhausted" and result.reason == "ledger_invalid"
    assert ledger.path.read_bytes() == b""


def test_new_receipt_generation_and_criterion_version_do_not_reset_same_pixel_budget(tmp_path):
    req = request()
    ledger = VisualCallLedger(tmp_path / "ledger.json", max_calls=2, max_input_tokens=128_000,
                              max_cost_usd=.0128)
    ledger.reserve(req)
    capture = replace(req.evidence.capture, observation_id="fresh", captured_at="2026-10-08T13:00:00+00:00")
    evidence = replace(req.evidence, capture=capture, generation="freshgeneration",
                       capture_started=req.evidence.capture_started + .01,
                       capture_finished=req.evidence.capture_finished + .01)
    other = replace(req, evidence=evidence, generation="freshgeneration", criterion_version="v2")
    with pytest.raises(VisualLedgerError, match="duplicate_evidence"):
        ledger.reserve(other)


def test_metadata_only_resource_revision_alias_and_ownership_changes_cannot_retry(tmp_path):
    req = request()
    req = replace(req, budget=replace(req.budget, max_calls=2))
    ledger = VisualCallLedger(tmp_path / "ledger.json", max_calls=2, max_input_tokens=128_000,
                              max_cost_usd=.0128)
    ledger.reserve(req)
    image = replace(req.evidence.reference, resource_id="renamed", revision="v2", render_recipe="new_alias")
    capture = replace(req.evidence.capture, surface=Surface("native", pid=3, window_id=4),
                      target=replace(req.evidence.capture.target, id="renamed-target", token="new-token"))
    evidence = replace(req.evidence, capture=capture, reference=image, source_scope=("renamed",),
                       declared_resource_ownership="renamed", coverage_warning="new wording")
    other = replace(req, evidence=evidence)
    with pytest.raises(VisualLedgerError, match="duplicate_evidence"):
        ledger.reserve(other)


def test_changed_pixel_evidence_allows_only_one_bounded_recovery(tmp_path):
    req = request()
    ledger = VisualCallLedger(tmp_path / "ledger.json", max_calls=2, max_input_tokens=128_000,
                              max_cost_usd=.0128)
    req = replace(req, budget=replace(req.budget, max_calls=2))
    ledger.reserve(req)
    buffer = BytesIO()
    Image.new("RGB", (80, 60), "red").save(buffer, format="PNG")
    capture = replace(req.evidence.capture, png=buffer.getvalue())
    other = replace(req, evidence=replace(req.evidence, capture=capture))
    ledger.reserve(other)
    third = replace(other, evidence=replace(other.evidence, accessible_text="new visible label"))
    with pytest.raises(VisualLedgerError, match="budget_exhausted"):
        ledger.reserve(third)


def test_changed_target_geometry_allows_second_appearance_check(tmp_path):
    req = replace(request(), budget=VisualCheckBudget(max_calls=2))
    ledger = VisualCallLedger(tmp_path / "ledger.json", max_calls=2, max_input_tokens=128_000,
                              max_cost_usd=.0128)
    ledger.reserve(req)
    target = replace(req.evidence.capture.target, bounds=Bounds(2, 1, 10, 10),
                     pixel_bounds=(2, 1, 12, 11))
    capture = replace(req.evidence.capture, target=target)
    other = replace(req, evidence=replace(req.evidence, capture=capture))
    ledger.reserve(other)
    assert len(json.loads(ledger.path.read_text())["entries"]) == 2


@pytest.mark.parametrize("limits", [{"max_input_tokens": 63_999}, {"max_cost_usd": .0063}])
async def test_pessimistic_token_and_cost_caps_hold_before_request(tmp_path, limits):
    ledger = VisualCallLedger(tmp_path / "ledger.json", **limits)
    result, seen = await call(tmp_path, ledger=ledger)
    assert result.status == "budget_exhausted" and seen == []


async def test_expired_request_does_not_reserve_or_dispatch(tmp_path):
    req = request()
    evidence = replace(req.evidence, capture_started=time.monotonic() - 2,
                       capture_finished=time.monotonic() - 1)
    req = replace(req, evidence=evidence, deadline_monotonic=evidence.capture_finished)
    result, seen = await call(tmp_path, req=req)
    assert result.status == "unavailable" and result.reason == "deadline_expired" and seen == []


async def test_concurrent_duplicate_reservations_have_one_winner(tmp_path):
    req = request()
    ledger = VisualCallLedger(tmp_path / "ledger.json")
    outcomes = await asyncio.gather(*(asyncio.to_thread(ledger.reserve, req) for _ in range(4)),
                                    return_exceptions=True)
    assert sum(isinstance(item, str) for item in outcomes) == 1
    assert all(isinstance(item, VisualLedgerError) for item in outcomes if not isinstance(item, str))


@pytest.mark.parametrize("kind", ["symlink", "parent_symlink", "broad_mode", "malformed", "other_limits"])
async def test_unsafe_or_malformed_ledger_is_fail_closed(tmp_path, kind):
    path = tmp_path / "ledger.json"
    if kind == "symlink":
        target = tmp_path / "private.json"
        target.write_text("{}")
        path.symlink_to(target)
    elif kind == "parent_symlink":
        directory = tmp_path / "other"
        directory.mkdir()
        (tmp_path / "link").symlink_to(directory)
        path = tmp_path / "link" / "ledger.json"
    elif kind == "broad_mode":
        path.write_text("{}")
        path.chmod(0o644)
    elif kind == "malformed":
        path.write_text('{"version":1,"entries":')
        path.chmod(0o600)
    else:
        VisualCallLedger(path).reserve(request())
    ledger = VisualCallLedger(path, max_calls=2) if kind == "other_limits" else VisualCallLedger(path)
    result, seen = await call(tmp_path, ledger=ledger)
    assert result.status == "budget_exhausted" and seen == []


@pytest.mark.parametrize("limits", [
    {"max_calls": 0}, {"max_calls": 3}, {"max_calls": True},
    {"max_input_tokens": True}, {"max_cost_usd": float("nan")},
])
def test_ledger_limits_validated(tmp_path, limits):
    with pytest.raises(VisualLedgerError):
        VisualCallLedger(tmp_path / "ledger.json", **limits)


async def test_explicit_cancellation_keeps_pessimistic_reservation(tmp_path):
    entered = asyncio.Event()
    async def handler(message):
        entered.set()
        await asyncio.Future()
    task = asyncio.create_task(call(tmp_path, handler=handler))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    entry = json.loads((tmp_path / "ledger.json").read_text())["entries"][0]
    assert not entry["settled"] and entry["tokens"] == 64_000
