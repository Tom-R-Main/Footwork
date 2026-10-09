"""Explicit advisory image transport with durable, workflow-owned call reservations.

No keys are loaded implicitly, no actions are produced, and no requests are retried.
Unknown usage retains its pessimistic reservation, including cancellation or timeout.
The caller owns the private ledger directory and observation-generation callback.
Token reservations use standard input pricing, $0.10 per million tokens. They are
local budget accounting, not a provider-enforced input limit; reported overage is
charged and invalidates the answer. Regional pricing is not supported here.
"""
from __future__ import annotations

import asyncio
import base64
import fcntl
import hashlib
import json
import math
import os
import stat
import time
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path
from typing import Self

import httpx

from .decisions import ENDPOINT, MODEL, DecisionsError, _parse, _unique_object, _usage
from .visual_checks import PROMPT_VERSION, QUESTIONS, VisualCheckRequest, VisualCheckResult, route_request

INPUT_USD_PER_TOKEN = 0.1 / 1_000_000
MAX_RESPONSE_BYTES = 65_536


class VisualLedgerError(ValueError):
    """Safe failure code, never ledger or provider contents."""


def _positive(value, code: str) -> None:
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise VisualLedgerError(code)


class VisualCallLedger:
    """An existing private directory holds a locked, fsynced workflow budget file.

    All callers sharing a workflow must share this ledger. Reserving the same role
    and appearance again is refused even with new wording, resource aliases or IDs.
    A crash can leave a reservation charged or an unreadable ledger; both fail closed.
    """

    def __init__(self, path: Path | str, *, max_calls: int = 1,
                 max_input_tokens: int = 64_000, max_cost_usd: float = 0.0064):
        if type(max_calls) is not int or not 1 <= max_calls <= 2:
            raise VisualLedgerError("budget_calls")
        if type(max_input_tokens) is not int or max_input_tokens <= 0:
            raise VisualLedgerError("budget_tokens")
        _positive(max_cost_usd, "budget_cost")
        self.path = Path(path).absolute()
        self.limits = {"calls": max_calls, "tokens": max_input_tokens, "cost": max_cost_usd}

    @contextmanager
    def _locked(self):
        # No symlink component, special file, or broad-readable existing ledger.
        fd = None
        try:
            for parent in self.path.parents:
                if parent.is_symlink() or not parent.is_dir():
                    raise VisualLedgerError("ledger_path")
            # Only this exclusive creator may initialize an empty file. Existing
            # empty state can be a crashed write and must never reset reservations.
            try:
                fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                created = True
            except FileExistsError:
                fd = os.open(self.path, os.O_RDWR | os.O_NOFOLLOW)
                created = False
            fcntl.flock(fd, fcntl.LOCK_EX)
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o077
                    or info.st_uid != os.getuid()):
                raise VisualLedgerError("ledger_path")
            if info.st_size > MAX_RESPONSE_BYTES:
                raise VisualLedgerError("ledger_invalid")
            with os.fdopen(fd, "r+", encoding="utf-8") as file:
                fd = None
                content = file.read()
                if not content and not created:
                    raise VisualLedgerError("ledger_invalid")
                state = json.loads(content, object_pairs_hook=_unique_object) if content else {
                    "version": 1, "limits": self.limits, "entries": [],
                }
                self._validate(state)
                yield file, state
        except VisualLedgerError:
            raise
        except (OSError, UnicodeError, ValueError, DecisionsError, OverflowError, RecursionError):
            raise VisualLedgerError("ledger_unavailable") from None
        finally:
            if fd is not None:
                os.close(fd)

    def _validate(self, state: dict) -> None:
        if (not isinstance(state, dict) or set(state) != {"version", "limits", "entries"}
                or type(state["version"]) is not int or state["version"] != 1
                or not isinstance(state["limits"], dict) or state["limits"] != self.limits
                or type(state["limits"].get("calls")) is not int
                or type(state["limits"].get("tokens")) is not int
                or not isinstance(state["entries"], list) or len(state["entries"]) > 2):
            raise VisualLedgerError("ledger_invalid")
        keys = set()
        for entry in state["entries"]:
            if (not isinstance(entry, dict) or set(entry) != {"key", "tokens", "cost", "settled"}
                    or not isinstance(entry["key"], str) or len(entry["key"]) != 64
                    or any(c not in "0123456789abcdef" for c in entry["key"])
                    or entry["key"] in keys or type(entry["tokens"]) is not int
                    or entry["tokens"] < 0 or type(entry["cost"]) not in (int, float)
                    or not math.isfinite(entry["cost"]) or entry["cost"] < 0
                    or type(entry["settled"]) is not bool):
                raise VisualLedgerError("ledger_invalid")
            keys.add(entry["key"])
            if (abs(entry["cost"] - entry["tokens"] * INPUT_USD_PER_TOKEN) > 1e-12
                    or (not entry["settled"] and entry["tokens"] == 0)):
                raise VisualLedgerError("ledger_invalid")

    def _write(self, file, state: dict) -> None:
        file.seek(0)
        file.write(json.dumps(state, allow_nan=False, separators=(",", ":")))
        file.truncate()
        file.flush()
        os.fsync(file.fileno())
        directory = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def reserve(self, request: VisualCheckRequest) -> str:
        evidence = request.evidence.to_dict()
        capture = evidence["capture"]
        # Appearance recovery requires changed pixels, geometry or accessible text.
        # Resource aliases/revisions and receipt identity are retained in the result
        # binding, but cannot create another appearance judgment on unchanged data.
        appearance = {
            "image": {key: capture["image"][key] for key in ("sha256", "width", "height")},
            "viewport": capture["viewport"],
            "target_bounds": capture["target"]["bounds"],
            "target_pixel_bounds": capture["target"]["pixel_bounds"],
            "reference": None, "source": None,
            "crop": evidence["crop"], "accessible_text_sha256": evidence["accessible_text_sha256"],
        }
        for kind in ("reference", "source"):
            asset = evidence[kind]
            if asset is not None:
                appearance[kind] = {key: asset[key] for key in ("image_sha256", "dimensions")}
        key = hashlib.sha256(json.dumps([
            request.role, appearance,
        ], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        tokens = request.budget.max_input_tokens
        cost = tokens * INPUT_USD_PER_TOKEN
        with self._locked() as (file, state):
            entries = state["entries"]
            if any(entry["key"] == key for entry in entries):
                raise VisualLedgerError("duplicate_evidence")
            if (len(entries) >= min(self.limits["calls"], request.budget.max_calls)
                    or sum(e["tokens"] for e in entries) + tokens > self.limits["tokens"]
                    or sum(e["cost"] for e in entries) + cost > self.limits["cost"] + 1e-12
                    or cost > request.budget.max_cost_usd + 1e-12):
                raise VisualLedgerError("budget_exhausted")
            entries.append({"key": key, "tokens": tokens, "cost": cost, "settled": False})
            self._write(file, state)
        return key

    def settle(self, key: str, tokens: int | None) -> None:
        if tokens is None:
            return
        if type(tokens) is not int or tokens < 0:
            raise VisualLedgerError("usage")
        with self._locked() as (file, state):
            entry = next((e for e in state["entries"] if e["key"] == key), None)
            if entry is None or entry["settled"]:
                raise VisualLedgerError("ledger_invalid")
            entry.update(tokens=tokens, cost=tokens * INPUT_USD_PER_TOKEN, settled=True)
            self._write(file, state)


class VisualDecisionsClient:
    """Pooled official-endpoint client; injected HTTP clients are test-only seams."""

    def __init__(self, api_key: str, *, client: httpx.AsyncClient | None = None):
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("api_key_required")
        self._key = api_key
        self._client = client
        self._owned = client is None
        self._closed = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        self._closed = True
        if self._owned and self._client is not None:
            await self._client.aclose()

    async def check(self, request: VisualCheckRequest, ledger: VisualCallLedger, *,
                    is_current: Callable[[], bool]) -> VisualCheckResult:
        start = time.monotonic()
        prompt_hash = ""
        returned_model = ""
        tokens = None
        phases = []

        def result(status: str, reason: str = "", p: float | None = None):
            return VisualCheckResult(
                request_id=request.request_id, request_digest=request.digest,
                evidence_digest=request.evidence.digest, generation=request.generation,
                role=request.role, status=status, p=p, reason=reason,
                requested_model=MODEL, returned_model=returned_model, input_tokens=tokens,
                prompt_version=PROMPT_VERSION, prompt_sha256=prompt_hash,
                elapsed_ms=(time.monotonic() - start) * 1000, phases_ms=tuple(phases),
            )

        def current() -> bool:
            try:
                return is_current() is True
            except Exception:  # noqa: BLE001 - a failed live callback must withhold every answer
                return False

        reason = route_request(request, now=start, current_generation=request.generation)
        if reason:
            return result("unavailable", reason)
        if self._closed:
            return result("unavailable", "client_closed")
        if not current():
            return result("invalidated", "generation_changed")
        prompt = request.provider_input()
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        if (request.budget.max_bytes > 4_000_000 or request.budget.max_input_tokens > 64_000
                or request.budget.max_calls > 2):
            return result("unavailable", "unsupported_budget")
        questions = [{"name": "required", "type": "predicate", "instructions": QUESTIONS[request.role]}]
        content = [{"type": "input_text", "text": prompt}] + [
            {"type": "input_image", "image_url": "data:image/png;base64," +
             base64.b64encode(image).decode("ascii")} for image in request.images
        ]
        body = json.dumps({"model": MODEL, "input": [{"role": "user", "content": content}],
                           "questions": questions}, allow_nan=False,
                          separators=(",", ":")).encode()
        phases.append(("encoding", (time.monotonic() - start) * 1000))
        if len(body) > request.budget.max_bytes:
            return result("unavailable", "request_too_large")
        try:
            key = ledger.reserve(request)
        except VisualLedgerError as error:
            return result("budget_exhausted", str(error))
        # Everything after reservation can have uncertain cost. No automatic release.
        if not current() or time.monotonic() >= request.deadline_monotonic:
            return result("invalidated", "generation_changed_or_expired")
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60, follow_redirects=False, trust_env=False)
        raw = None
        network_start = time.monotonic()
        try:
            async with asyncio.timeout(max(0, request.deadline_monotonic - network_start)):
                async with self._client.stream("POST", ENDPOINT, content=body, headers={
                    "Authorization": f"Bearer {self._key}", "Content-Type": "application/json",
                }, follow_redirects=False) as response:
                    if not 200 <= response.status_code < 300:
                        return result("error", f"http_{response.status_code}")
                    data = bytearray()
                    async for chunk in response.aiter_bytes():
                        data.extend(chunk)
                        if len(data) > MAX_RESPONSE_BYTES:
                            return result("invalid_response", "response_too_large")
                raw = json.loads(data, object_pairs_hook=_unique_object)
            phases.append(("provider", (time.monotonic() - network_start) * 1000))
        except (TimeoutError, httpx.TimeoutException):
            return result("timeout", "deadline_or_transport_timeout")
        except httpx.RequestError:
            return result("error", "network")
        except (ValueError, UnicodeError, DecisionsError, RecursionError):
            return result("invalid_response", "invalid_json")
        validation_start = time.monotonic()
        try:
            if isinstance(raw, dict):
                tokens = _usage(raw)
                if tokens is not None and tokens > 10_000_000:
                    tokens = None
                    return result("invalid_response", "usage")
                returned_model = raw.get("model", "")
                if (not isinstance(returned_model, str) or len(returned_model) > 128
                        or self._key in returned_model
                        or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._"
                               for c in returned_model)):
                    returned_model = ""
            ledger.settle(key, tokens)
            if returned_model != MODEL:
                return result("invalid_response", "response_model")
            parsed = _parse(raw, questions, time.monotonic() - network_start)
            if tokens is not None and tokens > request.budget.max_input_tokens:
                return result("invalid_response", "usage_exceeds_reservation")
            phases.append(("validation", (time.monotonic() - validation_start) * 1000))
            if not current() or time.monotonic() >= request.deadline_monotonic:
                return result("invalidated", "generation_changed_or_expired")
            return result("valid", p=parsed.answers["required"].probability)
        except DecisionsError as error:
            return result("refusal" if error.code == "refusal" else "invalid_response", error.code)
        except VisualLedgerError:
            return result("invalid_response", "ledger_unavailable")
