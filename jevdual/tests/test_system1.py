"""Offline provider contract and factory tests; no credentials or network required."""

import copy
import hashlib
import json
from dataclasses import FrozenInstanceError

import httpx
import httpx2
import pytest
import typesafe_sdk
from jevdual.system1 import (
    JEV_MODEL,
    SNAP_MODEL,
    S1Config,
    create_s1_client,
    prepare_request,
    resolve_s1_config,
    validate_response,
)
from typesafe_sdk import Choice, Noul, RetryPolicy, TypeSafeAPIError, TypeSafeError


@pytest.fixture(autouse=True)
def clean_config(monkeypatch):
    monkeypatch.delenv("JEVDUAL_S1_PROVIDER", raising=False)
    monkeypatch.delenv("JEVDUAL_S1_MODEL", raising=False)


def questions():
    return {
        "complete": Noul(instructions={"ask": ["Is it done?", {"use": "receipts"}]},
                         criteria={"true": {"receipt": True}, "false": ["missing", "partial"]}),
        "operation": Choice(instructions=["Choose", {"scope": "local"}],
                            criteria={"done": {"meaning": "Complete"}, "wait": None}),
    }


def raw(model=SNAP_MODEL):
    return {
        "model": model,
        "usage": {"input_tokens": 12, "output_tokens": 0},
        "answers": {
            "complete": {"type": "noul", "noul": 0.93},
            "operation": {"type": "choice", "choice": "done", "confidence": 0.63,
                          "probabilities": {"done": 0.81, "wait": 0.19}},
        },
    }


def test_default_is_frozen_and_pinned(monkeypatch):
    monkeypatch.setenv("TYPESAFE_DEFAULT_MODEL", "jev-latest")
    config = resolve_s1_config()
    assert (config.provider, config.model, config.key_env, config.price_per_million) == (
        "jev", "jev-1.13.0", "TYPESAFE_API_KEY", 0.042,
    )
    with pytest.raises(FrozenInstanceError):
        config.model = "jev-latest"
    monkeypatch.setenv("JEVDUAL_S1_PROVIDER", "subq")
    assert resolve_s1_config().model == SNAP_MODEL
    assert resolve_s1_config().price_per_million == 0.05
    assert resolve_s1_config("jev").model == JEV_MODEL


@pytest.mark.parametrize("provider,model", [("other", None), ("jev", SNAP_MODEL), ("subq", JEV_MODEL),
                                           ("jev", "jev-latest"), ("subq", "subq-preview")])
def test_unsupported_configuration_fails_closed(provider, model):
    with pytest.raises(TypeSafeError):
        resolve_s1_config(provider, model)
    with pytest.raises(TypeSafeError):
        S1Config("subq", SNAP_MODEL, "TYPESAFE_API_KEY", 0.042, "https://api.subq.ai")


def test_jev_constructor_is_dynamically_resolved(monkeypatch):
    captured = {}
    sentinel = object()

    def factory(**kwargs):
        captured.update(kwargs)
        return sentinel

    monkeypatch.setattr(typesafe_sdk, "AsyncTypeSafeClient", factory)
    assert create_s1_client(resolve_s1_config(), timeout=7) is sentinel
    assert captured == {"api_key": None, "model": JEV_MODEL, "base_url": "https://api.typesafe.ai", "timeout": 7}


async def test_jev_preparation_matches_exact_sdk_body():
    captured = []

    def handle(request):
        captured.append(request)
        return httpx2.Response(200, json=raw(JEV_MODEL))

    config = resolve_s1_config()
    async with create_s1_client(config, api_key="synthetic", transport=httpx2.MockTransport(handle),
                                retry=RetryPolicy(max_retries=0)) as client:
        await client.system_one({"task": "α"}, questions())
    assert prepare_request(config, {"task": "α"}, questions()).body == captured[0].content


async def test_snap_endpoint_json_preservation_pooling_receipt_and_close():
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(200, json=raw())

    config = resolve_s1_config("subq")
    transport = httpx.MockTransport(handle)
    async with create_s1_client(config, api_key="synthetic-secret", transport=transport) as client:
        pooled = client._http_client
        for _ in range(2):
            response = await client.system_one({"task": "α"}, questions(), model=SNAP_MODEL,
                                                retry=RetryPolicy(max_retries=0))
        assert client._http_client is pooled
        assert response.nouls["complete"].noul == 0.93
        assert response.choices["operation"].confidence == 0.63
        assert response.choices["operation"].probabilities["done"] == 0.81
        receipt = client.last_receipt
        assert receipt.requested_model == receipt.returned_model == SNAP_MODEL
        assert receipt.input_tokens == 12
        assert receipt.transport_latency_ms >= 0
        assert receipt.request_sha256 == hashlib.sha256(requests[-1].content).hexdigest()
        assert receipt.answer_sources == {"complete": "provider", "operation": "provider"}
        assert receipt.raw_response == raw()
    assert pooled.is_closed
    assert len(requests) == 2
    assert str(requests[0].url) == "https://api.subq.ai/v1/systemone"
    assert json.loads(requests[0].content)["questions"] == {
        name: q.model_dump(mode="json") for name, q in questions().items()
    }


async def test_singleton_binding_has_explicit_provenance_and_no_model_claim():
    config = resolve_s1_config("subq")
    qs = {**questions(), "target": Choice(criteria={"7": {"visible": "Save"}})}
    prepared = prepare_request(config, "state", qs)
    assert "target" not in prepared.wire_questions
    assert prepared.answer_sources["target"] == "forced_single_option"
    async with create_s1_client(config, api_key="synthetic", transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json=raw())
    )) as client:
        result = await client.system_one("state", qs)
        assert result.choices["target"].probabilities == {"7": 1.0}
        assert result.choices["target"].choice == "7"
        assert result.choices["target"].confidence == 1.0
        assert "target" not in client.last_receipt.raw_response["answers"]
        assert client.last_receipt.answer_sources["target"] == "forced_single_option"
    assert "target" in prepare_request(resolve_s1_config(), "state", qs).wire_questions


async def test_all_singletons_are_local_without_transport_or_provider_identity():
    def handle(request):
        pytest.fail("A deterministic-only batch must not dispatch")

    async with create_s1_client(resolve_s1_config("subq"), api_key="synthetic",
                                transport=httpx.MockTransport(handle)) as client:
        result = await client.system_one("state", {"target": Choice(criteria={"7": None})})
        assert result.choices["target"].choice == "7"
        assert client.last_receipt.input_tokens == 0
        assert client.last_receipt.returned_model is None


@pytest.mark.parametrize("bad_questions", [
    {str(i): Noul() for i in range(17)},
    {"choice": Choice(criteria={str(i): None for i in range(256)})},
    {"score": {"type": "score", "criteria": ["no", "yes"]}},
    {"x" * 101: Noul()},
    {},
])
def test_snap_limits_reject_without_truncation(bad_questions):
    with pytest.raises(TypeSafeError):
        prepare_request(resolve_s1_config("subq"), "state", bad_questions)


@pytest.mark.parametrize("mutation", [
    lambda r: r.update(model=JEV_MODEL),
    lambda r: r["answers"].pop("complete"),
    lambda r: r["answers"].update(extra={"type": "noul", "noul": 0.2}),
    lambda r: r["answers"]["complete"].update(type="unknown"),
    lambda r: r["answers"]["complete"].update(noul="0.9"),
    lambda r: r["answers"]["complete"].update(noul=True),
    lambda r: r["answers"]["complete"].update(noul=float("nan")),
    lambda r: r["answers"]["complete"].update(noul=10**1000),
    lambda r: r["answers"]["operation"].update(confidence=False),
    lambda r: r["answers"]["operation"].update(choice="wait"),
    lambda r: r["answers"]["operation"].update(probabilities={"done": 0.8}),
    lambda r: r["answers"]["operation"].update(probabilities={"done": 0.7, "wait": 0.2}),
    lambda r: r["usage"].update(input_tokens=True),
    lambda r: r["usage"].update(input_tokens=-1),
    lambda r: r["usage"].update(output_tokens="0"),
    lambda r: r["usage"].update(output_tokens=1),
])
def test_native_contract_refuses_malformed_values_before_sdk(mutation):
    response = copy.deepcopy(raw())
    mutation(response)
    with pytest.raises(TypeSafeAPIError):
        validate_response(resolve_s1_config("subq"), response, questions())


async def test_error_receipt_retains_usage_and_native_response_but_redacts_echoed_key():
    response = raw()
    response["model"] = "wrong-synthetic-secret"
    async with create_s1_client(resolve_s1_config("subq"), api_key="synthetic-secret",
                                transport=httpx.MockTransport(lambda r: httpx.Response(200, json=response))) as client:
        with pytest.raises(TypeSafeAPIError) as error:
            await client.system_one("state", questions())
        assert client.last_receipt.input_tokens == 12
        assert client.last_receipt.raw_response["model"] == "wrong-[REDACTED]"
        assert "synthetic-secret" not in repr(client.last_receipt)
        assert "synthetic-secret" not in repr(error.value)


@pytest.mark.parametrize("content", [b'{"model":"x","model":"y"}', b'{"x":NaN}', b'not json'])
async def test_strict_json_refuses_duplicates_nonfinite_and_invalid_json(content):
    async with create_s1_client(resolve_s1_config("subq"), api_key="synthetic", transport=httpx.MockTransport(
        lambda r: httpx.Response(200, content=content)
    )) as client:
        with pytest.raises(TypeSafeAPIError):
            await client.system_one("state", questions())
        assert client.last_receipt.transport_latency_ms >= 0


async def test_access_error_is_not_retried_and_never_echoes_response_body():
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(402, text="synthetic-secret")

    async with create_s1_client(resolve_s1_config("subq"), api_key="synthetic-secret",
                                transport=httpx.MockTransport(handle), retry=RetryPolicy(max_retries=0)) as client:
        with pytest.raises(TypeSafeAPIError) as error:
            await client.system_one("state", questions())
        assert error.value.status == 402
        assert "synthetic-secret" not in repr(error.value)
        assert client.last_receipt.raw_response == {"unparsed_response": "[REDACTED]"}
        assert client.last_receipt.input_tokens is None
        assert len(calls) == 1


async def test_error_json_is_bounded_and_redacted_in_receipt():
    async with create_s1_client(resolve_s1_config("subq"), api_key="synthetic-secret", transport=httpx.MockTransport(
        lambda r: httpx.Response(422, json={"detail": {"message": "synthetic-secret: bad instructions"}})
    )) as client:
        with pytest.raises(TypeSafeAPIError):
            await client.system_one("state", questions())
        assert client.last_receipt.raw_response == {"detail": {"message": "[REDACTED]: bad instructions"}}
    async with create_s1_client(resolve_s1_config("subq"), api_key="synthetic-secret", transport=httpx.MockTransport(
        lambda r: httpx.Response(422, content=b"x" * 16_001)
    )) as client:
        with pytest.raises(TypeSafeAPIError):
            await client.system_one("state", questions())
        assert client.last_receipt.raw_response == {"error": "response_body_exceeds_local_bound", "body_bytes": 16_001}


async def test_transport_failure_maps_to_sdk_and_retains_attempt_receipt():
    def handle(request):
        raise httpx.ConnectError("synthetic-secret", request=request)

    async with create_s1_client(resolve_s1_config("subq"), api_key="synthetic-secret",
                                transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(typesafe_sdk.TypeSafeAPIConnectionError) as error:
            await client.system_one("state", questions())
        assert "synthetic-secret" not in repr(error.value)
        assert client.last_receipt.request_sha256
        assert client.last_receipt.raw_response is None


async def test_call_model_mismatch_and_missing_key_refuse_before_dispatch(monkeypatch):
    monkeypatch.delenv("SUBQ_API_KEY", raising=False)
    with pytest.raises(TypeSafeError):
        create_s1_client(resolve_s1_config("subq"))
    async with create_s1_client(resolve_s1_config("subq"), api_key="synthetic") as client:
        with pytest.raises(TypeSafeError):
            await client.system_one("state", questions(), model=JEV_MODEL)
        assert client.last_receipt is None
