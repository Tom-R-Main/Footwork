"""Offline contracts for the optional Decisions transport; no credentials/network."""

import copy
import json
from dataclasses import FrozenInstanceError

import httpx
import pytest
from jevdual.decisions import (
    ENDPOINT,
    MAX_BODY_BYTES,
    ChoiceAnswer,
    ChoiceQuestion,
    DecisionsClient,
    DecisionsError,
    PredicateAnswer,
    PredicateQuestion,
    ScoreAnswer,
    ScoreQuestion,
    request_body,
    serialize_questions,
)

QUESTIONS = [
    PredicateQuestion("complete", "Is visible evidence sufficient?"),
    ChoiceQuestion("operation", "Which operation is supported?", {"click": "Visible button", "stop": "Unclear"}),
    ScoreQuestion("severity", "Rate the effect.", {"low": "No lost work", "high": "Lost work"}),
]
RESPONSE = {
    "model": "gpt-6-luna-actual-version",
    "answers": [
        {"type": "predicate", "name": "complete", "probability": 0.8},
        {"type": "choice", "name": "operation", "choice": "click", "confidence": 0.63,
         "probabilities": [{"value": "click", "probability": 0.9}, {"value": "stop", "probability": 0.1}]},
        {"type": "score", "name": "severity", "score": 0.3, "confidence": 0.52,
         "probabilities": [{"value": 0, "label": "low", "probability": 0.7},
                           {"value": 1, "label": "high", "probability": 0.3}]},
    ],
    "usage": {"input_tokens": 123},
}


async def run_response(response, questions=QUESTIONS):
    return await DecisionsClient(
        "test-secret", transport=httpx.MockTransport(lambda request: httpx.Response(200, json=response))
    ).decide("Shared observations", questions)


async def test_native_outputs_match_names_and_preserve_independent_confidence():
    response = copy.deepcopy(RESPONSE)
    response["answers"].reverse()
    batch = await run_response(response)
    assert batch.model == "gpt-6-luna-actual-version"
    assert batch.input_tokens == 123
    assert batch.latency_s >= 0
    assert batch.raw == response
    assert batch.answers["complete"] == PredicateAnswer("complete", 0.8)
    assert batch.answers["operation"] == ChoiceAnswer("operation", "click", {"click": 0.9, "stop": 0.1}, 0.63)
    assert batch.answers["severity"] == ScoreAnswer("severity", 0.3, {0: 0.7, 1: 0.3}, 0.52)
    with pytest.raises(FrozenInstanceError):
        batch.model = "changed"


async def test_exact_endpoint_serialization_no_additional_prompt_and_no_retry():
    seen = []

    def handler(request):
        seen.append(request)
        assert str(request.url) == ENDPOINT
        assert request.method == "POST"
        assert request.headers["Authorization"] == "Bearer test-secret"
        assert request.content == request_body("évidence", QUESTIONS)
        assert json.loads(request.content) == {
            "model": "gpt-6-luna", "input": "évidence", "questions": serialize_questions(QUESTIONS)
        }
        return httpx.Response(200, json=RESPONSE)

    await DecisionsClient("test-secret", transport=httpx.MockTransport(handler)).decide("évidence", QUESTIONS)
    assert len(seen) == 1


@pytest.mark.parametrize("usage", [None, {}, {"output_tokens": 0}, {"input_tokens": None}])
async def test_missing_usage_is_unknown_not_zero(usage):
    response = copy.deepcopy(RESPONSE)
    response["usage"] = usage
    assert (await run_response(response)).input_tokens is None


@pytest.mark.parametrize("usage", [-1, True, 3.2, "100"])
async def test_malformed_usage_rejected(usage):
    response = copy.deepcopy(RESPONSE)
    response["usage"] = {"input_tokens": usage}
    with pytest.raises(DecisionsError, match="usage"):
        await run_response(response)


@pytest.mark.parametrize("probability", [True, "0.8", None, -0.1, 1.1, float("nan"), float("inf"), 10**1000])
async def test_predicate_probability_strict(probability):
    response = copy.deepcopy(RESPONSE)
    response["answers"][0]["probability"] = probability
    # httpx's JSON encoder correctly rejects NaN, so send the provider wire form directly.
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=json.dumps(response)))
    with pytest.raises(DecisionsError, match="probability"):
        await DecisionsClient("test-secret", transport=transport).decide("Evidence", QUESTIONS)


@pytest.mark.parametrize("mutation,code", [
    (lambda r: r["answers"].pop(), "answer_set"),
    (lambda r: r["answers"].append(r["answers"][0]), "answer_set"),
    (lambda r: r["answers"][1].update(name="complete"), "answer_set"),
    (lambda r: r["answers"][0].update(name="unknown"), "answer_set"),
    (lambda r: r["answers"][0].update(type="choice"), "answer_type"),
    (lambda r: r["answers"][0].update(type="refusal", refusal="private reason"), "refusal"),
    (lambda r: r["answers"][1].update(choice="invented"), "choice"),
    (lambda r: r["answers"][1].update(choice="stop"), "choice_argmax"),
    (lambda r: r["answers"][1].pop("confidence"), "confidence"),
    (lambda r: r["answers"][1].update(confidence=True), "confidence"),
    (lambda r: r["answers"][1]["probabilities"].pop(), "distribution_options"),
    (lambda r: r["answers"][1]["probabilities"][1].update(value="click"), "distribution_options"),
    (lambda r: r["answers"][1]["probabilities"][1].update(value="invented"), "distribution_options"),
    (lambda r: r["answers"][1]["probabilities"][1].update(probability=0.4), "distribution_sum"),
    (lambda r: r["answers"][2]["probabilities"][0].update(value=True), "distribution_options"),
    (lambda r: r["answers"][2]["probabilities"][0].update(label="wrong"), "score_label"),
    (lambda r: r["answers"][2].update(score=0.8), "score_expectation"),
    (lambda r: r["answers"][2].update(score=2), "score"),
    (lambda r: r.pop("model"), "response_model"),
])
async def test_malformed_and_refused_batches_fail_atomically_with_receipt(mutation, code):
    response = copy.deepcopy(RESPONSE)
    mutation(response)
    with pytest.raises(DecisionsError) as caught:
        await run_response(response)
    assert caught.value.code == code
    assert caught.value.input_tokens == 123
    assert caught.value.raw == response
    assert "private reason" not in str(caught.value)
    assert "test-secret" not in repr(caught.value)


async def test_distribution_rounding_tolerance_does_not_normalize_scores():
    response = copy.deepcopy(RESPONSE)
    response["answers"][1]["probabilities"][1]["probability"] = 0.08
    batch = await run_response(response)
    assert batch.answers["operation"].probabilities == {"click": 0.9, "stop": 0.08}


@pytest.mark.parametrize("questions,code", [
    ([], "questions"),
    ([QUESTIONS[0], QUESTIONS[0]], "duplicate_question_name"),
    ([PredicateQuestion("", "Instructions")], "question_text"),
    ([ChoiceQuestion("q", "Instructions", {})], "question_options"),
    ([{"type": "predicate", "name": "q", "instructions": "x", "extra": "x"}], "question_fields"),
    ([{"type": "choice", "name": "q", "instructions": "x", "choices": [
        {"value": "x", "description": "x"}, {"value": "x", "description": "y"}]}], "duplicate_option"),
    ([{"type": "choice", "name": "q", "instructions": "x", "choices": [
        {"value": 4, "description": "x"}]}], "option_text"),
    ([{"type": "unknown", "name": "q", "instructions": "x"}], "question_type"),
])
async def test_invalid_questions_never_dispatch(questions, code):
    def forbidden(request):
        pytest.fail("Invalid request dispatched")

    with pytest.raises(DecisionsError) as caught:
        await DecisionsClient("test-secret", transport=httpx.MockTransport(forbidden)).decide("Evidence", questions)
    assert caught.value.code == code


async def test_utf8_byte_bound_and_text_only_fail_before_dispatch():
    def forbidden(request):
        pytest.fail("Oversize/image request dispatched")

    client = DecisionsClient("test-secret", transport=httpx.MockTransport(forbidden))
    with pytest.raises(DecisionsError, match="request_too_large"):
        await client.decide("é" * (MAX_BODY_BYTES // 2), QUESTIONS)
    with pytest.raises(DecisionsError, match="text_input_required"):
        await client.decide([{"role": "user", "content": []}], QUESTIONS)
    prefix = len(request_body("", QUESTIONS))
    assert len(request_body("a" * (MAX_BODY_BYTES - prefix), QUESTIONS)) == MAX_BODY_BYTES


@pytest.mark.parametrize("status", [302, 403, 429, 500])
async def test_http_error_sanitized_and_single_attempt(status):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(status, text="test-secret private body", headers={"Location": "https://other.test"})

    with pytest.raises(DecisionsError) as caught:
        await DecisionsClient("test-secret", transport=httpx.MockTransport(handler)).decide("Evidence", QUESTIONS)
    assert caught.value.code == f"http_{status}"
    assert caught.value.raw is None
    assert caught.value.provider_error is None
    assert "test-secret" not in str(caught.value)
    assert len(seen) == 1


async def test_network_error_sanitized_and_single_attempt():
    seen = []

    def handler(request):
        seen.append(request)
        raise httpx.ReadTimeout("test-secret private request", request=request)

    with pytest.raises(DecisionsError) as caught:
        await DecisionsClient("test-secret", transport=httpx.MockTransport(handler)).decide("Evidence", QUESTIONS)
    assert caught.value.code == "network"
    assert caught.value.__cause__ is None
    assert "test-secret" not in str(caught.value)
    assert len(seen) == 1


@pytest.mark.parametrize("wire,code", [
    ("not json test-secret", "invalid_json"),
    ('{"model":"x","model":"y"}', "duplicate_json_key"),
    ("[]", "response_object"),
])
async def test_invalid_json_and_duplicate_keys_rejected(wire, code):
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=wire))
    with pytest.raises(DecisionsError) as caught:
        await DecisionsClient("test-secret", transport=transport).decide("Evidence", QUESTIONS)
    assert caught.value.code == code
    assert "test-secret" not in str(caught.value)


async def test_http_diagnostic_whitelist_redacts_reflected_key_everywhere():
    response = {
        "error": {
            "type": "invalid_test-secret", "code": "test-secret_code", "param": "questions[test-secret]",
            "message": "Rejected test-secret in request", "input": "private evidence",
            "headers": {"Authorization": "Bearer test-secret"}, "request": "private request",
        },
        "input": "private evidence", "request": "private request",
    }
    transport = httpx.MockTransport(lambda request: httpx.Response(400, json=response))
    with pytest.raises(DecisionsError) as caught:
        await DecisionsClient("test-secret", transport=transport).decide("Evidence", QUESTIONS)
    error = caught.value
    assert error.provider_error == {
        "type": "invalid_[REDACTED]", "code": "[REDACTED]_code", "param": "questions[[REDACTED]]",
        "message": "Rejected [REDACTED] in request",
    }
    assert error.raw is None
    assert str(error) == "Decisions request failed: http_400"
    exported = json.dumps(vars(error))
    assert "test-secret" not in exported
    assert "private evidence" not in exported
    assert "private request" not in exported


async def test_http_diagnostic_bounds_and_redacts_before_truncating():
    response = {"error": {
        "type": "t" * 100, "code": "c" * 200, "param": "p" * 300,
        "message": "m" * 2045 + "test-secret" + "x" * 100,
    }}
    transport = httpx.MockTransport(lambda request: httpx.Response(400, json=response))
    with pytest.raises(DecisionsError) as caught:
        await DecisionsClient("test-secret", transport=transport).decide("Evidence", QUESTIONS)
    metadata = caught.value.provider_error
    assert {key: len(value) for key, value in metadata.items()} == {
        "type": 64, "code": 128, "param": 256, "message": 2048,
    }
    assert metadata["message"].endswith("[RE")
    assert "test" not in metadata["message"]


@pytest.mark.parametrize("wire", [
    "not JSON test-secret", "[]", '{}', '{"error":[]}', '{"error":{"message":[]}}',
    '{"error":{"message":"x","message":"test-secret"}}',
    '{"error":{"message":null}}', '{"error":{"input":"test-secret"}}',
    '{"error":{"message":"' + 'x' * 65_536 + '"}}',
])
async def test_malformed_http_diagnostics_are_code_only(wire):
    transport = httpx.MockTransport(lambda request: httpx.Response(400, content=wire))
    with pytest.raises(DecisionsError) as caught:
        await DecisionsClient("test-secret", transport=transport).decide("Evidence", QUESTIONS)
    assert caught.value.provider_error is None
    assert caught.value.raw is None
    assert str(caught.value) == "Decisions request failed: http_400"
