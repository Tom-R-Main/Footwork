"""Responses transport conformance: offline MockTransport only, no keys or paid calls."""

import json

import httpx
import pytest
from jevdual.judgments import risk_schema
from jevdual.responses import ResponsesChat, ResponsesError


def payload(content=None, **overrides):
    value = {"effect": "unknown", "permission_required": None, "source_ids": []}
    data = {
        "id": "resp_test",
        "model": "test-model-returned",
        "status": "completed",
        "output": [
            {"type": "reasoning", "summary": []},
            {
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": [{"type": "output_text", "text": content or json.dumps(value)}],
            },
        ],
        "usage": {
            "input_tokens": 120,
            "output_tokens": 50,
            "input_tokens_details": {"cached_tokens": 20},
            "output_tokens_details": {"reasoning_tokens": 30},
        },
    }
    data.update(overrides)
    return data


async def invoke(data, *, status=200, schema=None):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(status, json=data, headers={"x-request-id": "req_test"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        chat = ResponsesChat(
            "https://example.test/v1",
            "opaque-test-key",
            "test-model",
            client=client,
            max_output_tokens=321,
            schema=schema,
        )
        try:
            result = await chat.judge({"evidence": []}, risk_schema([]), "Judge offered evidence", "risk")
        except ResponsesError as error:
            result = error
        return chat, result, requests


async def test_judge_builds_strict_request_and_counts_reasoning_once():
    chat, result, requests = await invoke(payload())
    body = json.loads(requests[0].content)
    assert str(requests[0].url) == "https://example.test/v1/responses"
    assert body["store"] is False and body["reasoning"] == {"effort": "low"}
    assert body["max_output_tokens"] == 321 and body["model"] == "test-model"
    assert body["text"]["format"]["strict"] is True
    assert body["instructions"] == "Judge offered evidence"
    assert result.value["effect"] == "unknown"
    assert result.metadata is chat.last_call
    assert result.metadata.input_tokens == 120
    assert result.metadata.output_tokens == 50  # includes 30 reasoning; do not add it again
    assert result.metadata.reasoning_tokens == 30 and result.metadata.cached_tokens == 20
    assert result.metadata.requested_model == "test-model"
    assert result.metadata.model == "test-model-returned" and result.metadata.request_id == "req_test"
    assert result.metadata.usage_known and result.metadata.latency_ms >= 0


async def test_chat_callable_preserves_messages_and_accepts_injected_schema():
    captured = []

    def respond(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json=payload())

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        chat = ResponsesChat("https://example.test/v1", "opaque", "m", client=client, schema=risk_schema([]))
        messages = [{"role": "system", "content": "Policy"}, {"role": "user", "content": "Observation"}]
        reply = await chat(messages)
        assert captured[0]["input"] == messages
        assert reply.input_tokens == 120 and reply.output_tokens == 50
        assert json.loads(reply.content)["effect"] == "unknown"


@pytest.mark.parametrize("status", ["incomplete", "failed", "cancelled", "in_progress", "queued"])
async def test_noncompleted_outputs_preserve_usage_for_budget(status):
    chat, error, requests = await invoke(
        payload(status=status, incomplete_details={"reason": "max_output_tokens"})
    )
    assert isinstance(error, ResponsesError) and error.code == status
    assert chat.last_call.output_tokens == 50 and chat.last_call.usage_known
    assert chat.last_call.status == status and len(requests) == 1


async def test_refusal_is_not_empty_answer_and_keeps_usage():
    data = payload()
    data["output"][1]["content"] = [{"type": "refusal", "refusal": "opaque-test-key provider echo"}]
    chat, error, _ = await invoke(data)
    assert error.code == "refusal" and chat.last_call.output_tokens == 50
    assert "opaque-test-key" not in str(error) and "provider echo" not in str(error)


@pytest.mark.parametrize(
    "content",
    [
        "not JSON opaque-test-key",
        "[]",
        '{"effect":"unknown"}',
        '{"effect":"unknown","permission_required":null,"source_ids":[],"extra":1}',
        '{"effect":"unknown","effect":"benign","permission_required":null,"source_ids":[]}',
        '{"effect":"benign","permission_required":NaN,"source_ids":[]}',
        '{"effect":"benign","permission_required":true,"source_ids":["invented"]}',
    ],
)
async def test_completed_malformed_or_out_of_schema_output_fails_closed(content):
    chat, error, _ = await invoke(payload(content))
    assert isinstance(error, ResponsesError) and error.code == "invalid_response"
    assert "opaque-test-key" not in str(error)
    assert chat.last_call.usage_known


@pytest.mark.parametrize(
    "output",
    [
        [],
        [{"type": "function_call", "arguments": "opaque-test-key"}],
        [{"type": "message", "role": "assistant", "status": "incomplete", "content": []}],
        [{"type": "message", "role": "user", "status": "completed", "content": []}],
        [{"type": "message", "role": "assistant", "status": "completed", "content": [{"type": "image"}]}],
    ],
)
async def test_typed_output_items_are_checked(output):
    _, error, _ = await invoke(payload(output=output))
    assert isinstance(error, ResponsesError)
    assert "opaque-test-key" not in str(error)


async def test_http_error_does_not_expose_body_or_retry():
    chat, error, requests = await invoke({"error": "opaque-test-key request echo"}, status=429)
    assert error.code == "http_error"
    assert "opaque-test-key" not in str(error) and len(requests) == 1
    assert chat.last_call.http_status == 429 and not chat.last_call.usage_known


async def test_network_exception_does_not_expose_sensitive_exception_text():
    def respond(request):
        raise httpx.ConnectError("opaque-test-key request echo", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        chat = ResponsesChat("https://example.test/v1", "opaque-test-key", "m", client=client)
        with pytest.raises(ResponsesError) as caught:
            await chat([])
        assert "opaque-test-key" not in str(caught.value)
        assert caught.value.__suppress_context__
        assert chat.last_call.status == "transport_error"


async def test_invalid_usage_is_not_silently_undercharged():
    chat, error, _ = await invoke(
        payload(
            usage={"input_tokens": 10, "output_tokens": 5, "output_tokens_details": {"reasoning_tokens": 9}}
        )
    )
    assert error.code == "invalid_response" and not chat.last_call.usage_known


async def test_missing_usage_is_explicit_even_on_completed_answer():
    chat, result, _ = await invoke(payload(usage=None))
    assert result.value["effect"] == "unknown"
    assert not chat.last_call.usage_known
