"""Opt-in Responses transport for shadow judging and injected System Two chat.

No runtime defaults, credentials discovery, retries or execution authority live here.
Callers own client lifetime, budget reservation and role-specific admission checks.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, replace
from typing import Any

import httpx

from jevdual.desktop_s2 import ChatReply
from jevdual.judgments import JudgmentError, check_schema, validate_schema


@dataclass(frozen=True)
class ResponsesCall:
    provider: str
    requested_model: str
    model: str | None
    request_id: str | None
    response_id: str | None
    status: str
    input_tokens: int | None
    output_tokens: int | None
    cached_tokens: int | None
    reasoning_tokens: int | None
    usage_known: bool
    latency_ms: float
    http_status: int | None = None
    error_code: str | None = None


@dataclass(frozen=True)
class JudgmentCompletion:
    value: dict[str, Any]
    metadata: ResponsesCall


class ResponsesError(RuntimeError):
    """Safe transport failure. Body, request, refusal text and credentials are absent."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Responses request failed: {code}")


def _json_object(text: str) -> dict[str, Any]:
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError("duplicate JSON key")
            value[key] = item
        return value

    def reject_constant(_value):
        raise ValueError("nonfinite JSON number")

    value = json.loads(text, object_pairs_hook=pairs, parse_constant=reject_constant)
    if not isinstance(value, dict):
        raise TypeError("expected JSON object")
    return value


def _tokens(value: Any) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("invalid token usage")
    return value


class ResponsesChat:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 120.0,
        max_output_tokens: int = 2000,
        reasoning_effort: str = "low",
        schema: dict[str, Any] | None = None,
        schema_name: str = "action",
    ):
        if max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be positive")
        if schema is not None:
            check_schema(schema)
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self.model = model
        self.client = client
        self.timeout = timeout
        self.max_output_tokens = max_output_tokens
        self.reasoning_effort = reasoning_effort
        self.schema = schema
        self.schema_name = schema_name
        self.last_call: ResponsesCall | None = None

    async def __call__(self, messages: list[dict[str, str]]) -> ChatReply:
        # Preserve message ordering and role boundaries instead of flattening prompts.
        content, metadata = await self._request(messages, schema=self.schema, name=self.schema_name)
        return ChatReply(content, metadata.input_tokens or 0, metadata.output_tokens or 0, metadata.model)

    async def judge(
        self,
        state: dict[str, Any],
        schema: dict[str, Any],
        instructions: str,
        name: str,
    ) -> JudgmentCompletion:
        check_schema(schema)
        content, metadata = await self._request(
            [{"role": "user", "content": json.dumps(state, allow_nan=False)}],
            schema=schema,
            name=name,
            instructions=instructions,
        )
        # _request validates this JSON already; parsing again returns the typed value.
        return JudgmentCompletion(_json_object(content), metadata)

    async def _request(
        self,
        messages: list[dict[str, str]],
        *,
        schema: dict[str, Any] | None,
        name: str,
        instructions: str | None = None,
    ) -> tuple[str, ResponsesCall]:
        if schema is not None:
            check_schema(schema)
        body = {
            "model": self.model,
            "input": messages,
            "store": False,
            "reasoning": {"effort": self.reasoning_effort},
            "max_output_tokens": self.max_output_tokens,
        }
        if instructions is not None:
            body["instructions"] = instructions
        if schema is not None:
            body["text"] = {"format": {"type": "json_schema", "name": name, "strict": True, "schema": schema}}
        started = time.perf_counter()
        self.last_call = ResponsesCall(
            "openai", self.model, None, None, None, "pending", None, None, None, None, False, 0.0
        )
        try:
            if self.client is None:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await self._post(client, body)
            else:
                response = await self._post(self.client, body)
        except httpx.HTTPError:
            self._update(started, status="transport_error")
            raise ResponsesError("transport_error") from None
        self._update(
            started, request_id=response.headers.get("x-request-id"), http_status=response.status_code
        )
        if not response.is_success:
            self._update(started, status="http_error")
            raise ResponsesError("http_error")
        try:
            data = response.json()
            if not isinstance(data, dict):
                raise TypeError("expected response object")
            usage = data.get("usage")
            if usage is not None:
                input_tokens = _tokens(usage["input_tokens"])
                output_tokens = _tokens(usage["output_tokens"])
                raw_cached = (usage.get("input_tokens_details") or {}).get("cached_tokens")
                raw_reasoning = (usage.get("output_tokens_details") or {}).get("reasoning_tokens")
                cached = _tokens(raw_cached) if raw_cached is not None else None
                reasoning = _tokens(raw_reasoning) if raw_reasoning is not None else None
                if (cached is not None and cached > input_tokens) or (
                    reasoning is not None and reasoning > output_tokens
                ):
                    raise ValueError("usage breakdown exceeds totals")
                self._update(
                    started,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cached_tokens=cached,
                    reasoning_tokens=reasoning,
                    usage_known=True,
                )
            self._update(started, model=data.get("model"), response_id=data.get("id"))
            status = data.get("status")
            if status != "completed":
                code = (
                    status
                    if status in {"incomplete", "failed", "cancelled", "queued", "in_progress"}
                    else "invalid_status"
                )
                self._update(started, status=code)
                raise ResponsesError(code)
            if data.get("error") is not None:
                raise ResponsesError("provider_error")
            texts = []
            for item in data["output"]:
                if item["type"] == "reasoning":
                    continue
                if (
                    item["type"] != "message"
                    or item.get("role") != "assistant"
                    or item.get("status") != "completed"
                ):
                    raise ResponsesError("unexpected_output_item")
                for part in item["content"]:
                    if part["type"] == "refusal":
                        raise ResponsesError("refusal")
                    if part["type"] != "output_text" or not isinstance(part["text"], str):
                        raise ResponsesError("unexpected_output_content")
                    texts.append(part["text"])
            if not texts:
                raise ResponsesError("missing_output")
            content = "".join(texts)
            if schema is not None:
                validate_schema(_json_object(content), schema)
        except ResponsesError as error:
            self._update(started, status=error.code)
            raise
        except (ValueError, KeyError, TypeError, AttributeError, JudgmentError):
            self._update(started, status="invalid_response")
            raise ResponsesError("invalid_response") from None
        self._update(started, status="completed")
        assert self.last_call is not None
        return content, self.last_call

    async def _post(self, client: httpx.AsyncClient, body: dict[str, Any]) -> httpx.Response:
        return await client.post(
            f"{self.base_url}/responses",
            json=body,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=self.timeout,
        )

    def _update(self, started: float, **changes: Any) -> None:
        assert self.last_call is not None
        if "status" in changes:
            changes["error_code"] = None if changes["status"] == "completed" else changes["status"]
        self.last_call = replace(self.last_call, latency_ms=(time.perf_counter() - started) * 1000, **changes)
