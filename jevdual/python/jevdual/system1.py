"""Explicit experimental System One backends; the default remains pinned Jev.

Snap uses the existing SDK answer types after validating its native JSON contract.
Its receipt separates model judgments from deterministic singleton bindings. No
credentials are read from files and no provider response text enters exceptions.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any, Self

import httpx
import httpx2
from pydantic import ValidationError
from typesafe_sdk import (
    RetryPolicy,
    SystemOneResponse,
    TypeSafeAPIConnectionError,
    TypeSafeAPIError,
    TypeSafeAPIResponseValidationError,
    TypeSafeAPITimeoutError,
    TypeSafeError,
    TypeSafeRateLimitError,
)

JEV_MODEL = "jev-1.13.0"
SNAP_MODEL = "subq-snap-preview"
DISTRIBUTION_TOLERANCE = 0.02
_BACKENDS = {
    "jev": (JEV_MODEL, "TYPESAFE_API_KEY", 0.042, "https://api.typesafe.ai"),
    "subq": (SNAP_MODEL, "SUBQ_API_KEY", 0.05, "https://api.subq.ai"),
}


@dataclass(frozen=True)
class S1Config:
    provider: str
    model: str
    key_env: str
    price_per_million: float
    base_url: str

    def __post_init__(self) -> None:
        expected = _BACKENDS.get(self.provider)
        if expected is None or (
            self.model, self.key_env, self.price_per_million, self.base_url
        ) != expected:
            raise TypeSafeError("Unsupported System One provider/model configuration")


def resolve_s1_config(provider: str | None = None, model: str | None = None) -> S1Config:
    provider = provider if provider is not None else os.environ.get("JEVDUAL_S1_PROVIDER", "").strip() or "jev"
    if provider not in _BACKENDS:
        raise TypeSafeError("Unsupported System One provider")
    default, key_env, rate, base_url = _BACKENDS[provider]
    model = model if model is not None else os.environ.get("JEVDUAL_S1_MODEL", "").strip() or default
    return S1Config(provider, model, key_env, rate, base_url)


@dataclass(frozen=True)
class PreparedRequest:
    body: bytes
    wire_questions: dict[str, dict[str, Any]]
    forced_answers: dict[str, dict[str, Any]]
    answer_sources: dict[str, str]


def _question_data(questions: Mapping) -> dict[str, dict[str, Any]]:
    if not isinstance(questions, Mapping) or not questions:
        raise TypeSafeError("System One questions must be a nonempty mapping")
    data = {}
    for name, question in questions.items():
        if not isinstance(name, str) or not name:
            raise TypeSafeError("System One question names must be nonempty strings")
        if hasattr(question, "model_dump"):
            question = question.model_dump(mode="json")
        if not isinstance(question, Mapping):
            raise TypeSafeError("Unsupported System One question")
        item = dict(question)
        if set(item) - {"type", "instructions", "criteria"} or item.get("type") not in {"noul", "choice"}:
            raise TypeSafeError("Only Noul and Choice questions are supported by this adapter")
        if item["type"] == "choice":
            options = item.get("criteria")
            if not isinstance(options, Mapping) or not options or any(
                not isinstance(label, str) or not label for label in options
            ):
                raise TypeSafeError("Choice criteria require nonempty string labels")
            item["criteria"] = dict(options)
        elif item.get("criteria") is not None and (
            not isinstance(item["criteria"], Mapping) or set(item["criteria"]) - {"true", "false"}
        ):
            raise TypeSafeError("Noul criteria must describe true and/or false")
        data[name] = item
    return data


def prepare_request(config: S1Config, state: Any, questions: Mapping) -> PreparedRequest:
    """Prepare exact wire bytes without credentials, dispatch, or prompt conversion."""
    wire = _question_data(questions)
    sources = dict.fromkeys(wire, "provider")
    forced: dict[str, dict[str, Any]] = {}
    if config.provider == "subq":
        if any(len(name) > 100 for name in wire):
            raise TypeSafeError("Snap question names support at most 100 characters")
        for name, question in list(wire.items()):
            if question["type"] != "choice":
                continue
            options = question["criteria"]
            if len(options) > 255:
                raise TypeSafeError("Snap supports at most 255 options per choice")
            if len(options) == 1:
                selected = next(iter(options))
                forced[name] = {
                    "type": "choice", "choice": selected, "confidence": 1.0,
                    "probabilities": {selected: 1.0},
                }
                sources[name] = "forced_single_option"
                del wire[name]
        if len(wire) > 16:
            raise TypeSafeError("Snap supports at most 16 wire questions")
    body_data = {"state": state, "model": config.model, "questions": wire}
    try:
        # Match the pinned SDK serializer for baseline wire-hash comparisons.
        from typesafe_sdk._core.json import serialize

        # Unlike the SDK codec, reject nonfinite request values before dispatch.
        json.dumps(body_data, allow_nan=False)
        body = serialize(body_data)
    except (TypeError, ValueError, OverflowError):
        raise TypeSafeError("System One request is not finite JSON") from None
    return PreparedRequest(body, wire, forced, sources)


def _valid(condition: bool, path: str) -> None:
    if not condition:
        raise TypeSafeAPIResponseValidationError(200, None, httpx2.Headers(), path)


def _probability(value: Any, path: str) -> None:
    _valid(type(value) in (int, float) and 0 <= value <= 1 and math.isfinite(value), path)


def _usage(raw: Any) -> int | None:
    if not isinstance(raw, dict) or not isinstance(raw.get("usage"), dict):
        return None
    value = raw["usage"].get("input_tokens")
    return value if type(value) is int and value >= 0 else None


def validate_response(config: S1Config, raw: Any, questions: Mapping) -> SystemOneResponse:
    """Validate native values before the SDK can coerce or discard any fields."""
    expected = _question_data(questions) if questions else {}
    _valid(isinstance(raw, dict), "response")
    _valid(raw.get("model") == config.model, "model")
    answers = raw.get("answers")
    _valid(isinstance(answers, dict) and set(answers) == set(expected), "answers")
    for name, question in expected.items():
        answer = answers[name]
        _valid(isinstance(answer, dict) and answer.get("type") == question["type"], "answer.type")
        if question["type"] == "noul":
            _probability(answer.get("noul"), "answer.noul")
        else:
            probabilities = answer.get("probabilities")
            _valid(isinstance(probabilities, dict) and set(probabilities) == set(question["criteria"]),
                   "answer.probabilities")
            for value in probabilities.values():
                _probability(value, "answer.probabilities")
            _valid(abs(sum(probabilities.values()) - 1) <= DISTRIBUTION_TOLERANCE, "answer.probabilities.sum")
            selected = answer.get("choice")
            _valid(isinstance(selected, str) and selected in probabilities, "answer.choice")
            _valid(probabilities[selected] >= max(probabilities.values()), "answer.choice.argmax")
            _probability(answer.get("confidence"), "answer.confidence")
    usage = raw.get("usage")
    _valid(isinstance(usage, dict), "usage")
    for token_field in ("input_tokens", "output_tokens"):
        value = usage.get(token_field)
        _valid(value is None or (type(value) is int and value >= 0), "usage.tokens")
    if config.provider == "subq":
        _valid(usage.get("output_tokens") in (None, 0), "usage.output_tokens")
    try:
        return SystemOneResponse.model_validate(raw)
    except (ValidationError, TypeError, ValueError):
        raise TypeSafeAPIResponseValidationError(200, None, httpx2.Headers(), "response") from None


@dataclass(frozen=True)
class S1Receipt:
    requested_model: str
    returned_model: str | None
    raw_response: Any = field(repr=False)
    request_sha256: str
    answer_sources: dict[str, str]
    transport_latency_ms: float
    input_tokens: int | None


def _reject_constant(_: str) -> None:
    raise ValueError("Nonfinite JSON")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _redact(value: Any, key: str) -> Any:
    if isinstance(value, str):
        return value.replace(key, "[REDACTED]")
    if isinstance(value, dict):
        return {_redact(k, key): _redact(v, key) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v, key) for v in value]
    return value


class SnapClient:
    """Pooled async Snap transport with SDK-compatible errors and answer objects."""

    def __init__(self, config: S1Config, *, api_key: str | None = None, retry: RetryPolicy | None = None,
                 timeout: float = 30.0, transport: httpx.AsyncBaseTransport | None = None,
                 http_client: httpx.AsyncClient | None = None, headers: Mapping | None = None,
                 verify: Any = True):
        if config.provider != "subq":
            raise TypeSafeError("SnapClient requires the SubQ backend")
        key = api_key if api_key is not None else os.environ.get(config.key_env)
        if not isinstance(key, str) or not key.strip() or "\n" in key or "\r" in key:
            raise TypeSafeError("Set SUBQ_API_KEY or pass an API key")
        if transport is not None and http_client is not None:
            raise TypeSafeError("transport and http_client are mutually exclusive")
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise TypeSafeError("timeout must be positive and finite")
        self.config = config
        self._key = key
        self._timeout = timeout
        self._retry = retry or RetryPolicy(max_retries=0)
        self._headers = dict(headers or {})
        self._http_client = http_client or httpx.AsyncClient(timeout=timeout, transport=transport, verify=verify)
        self.last_receipt: S1Receipt | None = None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http_client.aclose()

    async def close(self) -> None:
        await self.aclose()

    async def system_one(self, state: Any, questions: Mapping, *, model: str | None = None,
                         retry: RetryPolicy | None = None, timeout: float | None = None,
                         **kwargs: Any) -> SystemOneResponse:
        if kwargs:
            raise TypeSafeError("Unsupported Snap call options")
        if model is not None and model != self.config.model:
            raise TypeSafeError("Model override does not match the selected System One backend")
        prepared = prepare_request(self.config, state, questions)
        effective_timeout = self._timeout if timeout is None else timeout
        if type(effective_timeout) not in (int, float) or not math.isfinite(effective_timeout) or effective_timeout <= 0:
            raise TypeSafeError("timeout must be positive and finite")
        self.last_receipt = S1Receipt(self.config.model, None, None, hashlib.sha256(prepared.body).hexdigest(),
                                      dict(prepared.answer_sources), 0.0, None)
        if not prepared.wire_questions:
            raw = {"model": self.config.model, "usage": {"input_tokens": 0, "output_tokens": 0}, "answers": {}}
            self.last_receipt = replace(self.last_receipt, raw_response=raw, input_tokens=0)
            return self._merge(raw, prepared)
        policy = self._retry if retry is None else retry
        async for attempt in policy._build_tenacity_async():
            with attempt:
                return await self._send(prepared, effective_timeout)
        raise TypeSafeError("System One request did not execute")

    def _merge(self, raw: dict, prepared: PreparedRequest) -> SystemOneResponse:
        validate_response(self.config, raw, prepared.wire_questions)
        combined = {**raw, "answers": {**raw["answers"], **prepared.forced_answers}}
        return SystemOneResponse.model_validate(combined)

    async def _send(self, prepared: PreparedRequest, timeout: float) -> SystemOneResponse:
        started = time.perf_counter()
        try:
            response = await self._http_client.post(
                self.config.base_url + "/v1/systemone", content=prepared.body, timeout=timeout,
                headers={**self._headers, "Authorization": f"Bearer {self._key}", "Content-Type": "application/json"},
            )
        except httpx.TimeoutException:
            raise TypeSafeAPITimeoutError(timeout) from None
        except httpx.RequestError:
            raise TypeSafeAPIConnectionError("Snap transport failed") from None
        finally:
            self.last_receipt = replace(self.last_receipt, transport_latency_ms=(time.perf_counter() - started) * 1000)
        content = response.content
        limit = 2_000_000 if response.is_success else 16_000
        raw = None
        invalid_json = False
        if len(content) > limit:
            raw = {"error": "response_body_exceeds_local_bound", "body_bytes": len(content)}
            invalid_json = True
        else:
            try:
                raw = json.loads(content, parse_constant=_reject_constant, object_pairs_hook=_unique_object)
            except (ValueError, UnicodeError):
                raw = {"unparsed_response": content.decode("utf-8", errors="replace")}
                invalid_json = True
        returned = raw.get("model") if isinstance(raw, dict) and isinstance(raw.get("model"), str) else None
        self.last_receipt = replace(self.last_receipt, raw_response=_redact(raw, self._key),
                                    returned_model=_redact(returned, self._key), input_tokens=_usage(raw))
        if not response.is_success:
            # Never expose response bodies or echoed request credentials in errors.
            error = TypeSafeRateLimitError if response.status_code == 429 else TypeSafeAPIError
            safe_headers = httpx2.Headers()
            delay = response.headers.get("retry-after", "")
            if delay.replace(".", "", 1).isdigit() and len(delay) < 12:
                safe_headers["retry-after"] = delay
            raise error(response.status_code, None, safe_headers, "Snap request failed")
        if invalid_json:
            raise TypeSafeAPIResponseValidationError(200, None, httpx2.Headers(), "json") from None
        return self._merge(raw, prepared)


def create_s1_client(config: S1Config, *, api_key: str | None = None, **kwargs: Any) -> Any:
    if config.provider == "subq":
        return SnapClient(config, api_key=api_key, **kwargs)
    # Resolve at call time so existing injected SDK clients remain supported.
    from typesafe_sdk import AsyncTypeSafeClient

    return AsyncTypeSafeClient(api_key=api_key, model=config.model, base_url=config.base_url, **kwargs)
