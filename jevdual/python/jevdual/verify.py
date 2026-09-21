"""Verification: evidence before done.

System 1 never declares a run complete on its own opinion. When the policy
picks ``done`` (or System 2 emits it), the verifier asks Jev absolute questions
over the final page: ``complete`` plus one ``unmet_<i>`` per requirement, worded
independently so neither is derived from the other. Code turns the
probabilities into one of three bands:

* ``accept``: complete is high and every requirement's unmet is low.
* ``reject``: any requirement is clearly unmet, or complete is clearly low; the
  run continues.
* ``verify``: the uncertain band; the caller escalates to System 2 with a
  screenshot.

If the run produced an answer, every claim in it must be quoted from the
captured page text (``evidence_match``). Unsupported claims are dropped from
``supported_answer``; when nothing survives the band is capped at ``verify``.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Literal

from typesafe_sdk import (
    Noul,
    RetryPolicy,
    SystemOneResponse,
    TypeSafeAPIConnectionError,
    TypeSafeAPIError,
    TypeSafeAPITimeoutError,
    TypeSafeError,
    TypeSafeRateLimitError,
)

from jevdual import prompts
from jevdual._native import native_or_pure
from jevdual.menu import Menu
from jevdual.policy import DEFAULT_RETRY, JEV_MODEL, PolicyError, SystemOneClient

log = logging.getLogger("jevdual.verify")

Band = Literal["accept", "reject", "verify"]


@dataclass(frozen=True)
class VerifyPolicy:
    """Band thresholds. Starting points; tuned on the dev split in E1, then frozen."""

    accept_complete: float = 0.85
    accept_unmet_max: float = 0.20
    #: Above this, the task is judged to ask for an answer; a done with none cannot be accepted.
    answer_required: float = 0.60
    reject_unmet: float = 0.70
    reject_complete: float = 0.30


@dataclass(frozen=True)
class ClaimCheck:
    claim: str
    grade: str  # exact | normalized | none
    start: int
    end: int

    @property
    def supported(self) -> bool:
        return self.grade != "none"


@dataclass(frozen=True)
class Verdict:
    band: Band
    complete: float
    unmet: dict[str, float]
    claims: list[ClaimCheck]
    reason: str
    supported_answer: str | None = None
    unsupported_claims: tuple[str, ...] = ()
    model: str = JEV_MODEL
    latency_ms: float = 0.0
    raw: SystemOneResponse | None = field(default=None, compare=False, repr=False)

    def to_trace(self) -> dict[str, Any]:
        """Small dict for StepRecord.effect / arbiter_reason."""
        return {
            "band": self.band,
            "complete": round(self.complete, 3),
            "unmet": {k: round(v, 3) for k, v in self.unmet.items()},
            "claims": [c.grade for c in self.claims],
            "unsupported": len(self.unsupported_claims),
            "reason": self.reason,
        }


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def split_claims(answer: str) -> list[str]:
    """Sentences and lines of an answer, each a claim that must be quoted from the page."""
    parts = [p.strip() for p in _SENTENCE_SPLIT.split(answer)]
    return [p for p in parts if len(p) >= 2]


def check_claims(answer: str | None, page_text: str) -> list[ClaimCheck]:
    if not answer:
        return []
    claims = split_claims(answer)
    if not claims:
        return []
    matcher = native_or_pure("evidence_match")
    return [ClaimCheck(r["claim"], r["grade"], r["start"], r["end"]) for r in matcher(claims, page_text)]


def band_for(complete: float, unmet: dict[str, float], policy: VerifyPolicy) -> tuple[Band, str]:
    worst = max(unmet.values(), default=0.0)
    worst_key = max(unmet, key=unmet.get) if unmet else None
    if worst >= policy.reject_unmet:
        return "reject", f"{worst_key} unmet with p={worst:.2f}"
    if complete <= policy.reject_complete:
        return "reject", f"complete p={complete:.2f}"
    if complete >= policy.accept_complete and worst <= policy.accept_unmet_max:
        return "accept", f"complete p={complete:.2f}, max unmet p={worst:.2f}"
    return "verify", f"uncertain: complete p={complete:.2f}, max unmet p={worst:.2f}"


async def _call_client(
    client: SystemOneClient, state: dict[str, Any], questions: dict[str, Any], *, model: str, retry: RetryPolicy | None
) -> SystemOneResponse:
    """One ``system_one`` call with SDK errors mapped to ``PolicyError`` (mirrors ``JevPolicy._call``)."""
    kwargs: dict[str, Any] = {"model": model}
    if retry is not None:
        kwargs["retry"] = retry
    try:
        return await client.system_one(state, questions, **kwargs)
    except TypeSafeRateLimitError as exc:
        raise PolicyError(f"rate limited: {exc}", retryable=True) from exc
    except (TypeSafeAPITimeoutError, TypeSafeAPIConnectionError) as exc:
        raise PolicyError(f"connection: {exc}", retryable=True) from exc
    except TypeSafeAPIError as exc:
        raise PolicyError(f"api error: {exc}", retryable=exc.status >= 500) from exc
    except TypeSafeError as exc:
        raise PolicyError(f"sdk error: {exc}") from exc


class Verifier:
    def __init__(self, client: SystemOneClient, *, model: str = JEV_MODEL, policy: VerifyPolicy | None = None, retry: RetryPolicy | None = DEFAULT_RETRY):
        self.client = client
        self.model = model
        self.policy = policy or VerifyPolicy()
        self.retry = retry

    def build_questions(self, requirements: tuple[str, ...]) -> dict[str, Noul]:
        questions: dict[str, Noul] = {
            "complete": Noul(
                instructions=prompts.VERIFY_COMPLETE["instructions"],
                criteria={"true": prompts.VERIFY_COMPLETE["true"], "false": prompts.VERIFY_COMPLETE["false"]},
            )
        }
        for i, req in enumerate(requirements):
            spec = prompts.verify_unmet(i, req)
            questions[f"unmet_{i}"] = Noul(instructions=spec["instructions"], criteria={"true": spec["true"], "false": spec["false"]})
        questions["answer_required"] = Noul(
            instructions=prompts.VERIFY_ANSWER_REQUIRED["instructions"],
            criteria={"true": prompts.VERIFY_ANSWER_REQUIRED["true"], "false": prompts.VERIFY_ANSWER_REQUIRED["false"]},
        )
        return questions

    @staticmethod
    def build_state(task: str, requirements: tuple[str, ...], menu: Menu, answer: str | None) -> dict[str, Any]:
        state: dict[str, Any] = {
            "task": task,
            "requirements": list(requirements),
            "page": {"url": menu.url, "title": menu.title, "text": menu.page_text},
        }
        if answer:
            state["answer"] = answer
        return state

    async def verify(self, task: str, requirements: tuple[str, ...], menu: Menu, answer: str | None, *, answer_expected: bool = False) -> Verdict:
        questions = self.build_questions(requirements)
        state = self.build_state(task, requirements, menu, answer)
        started = time.perf_counter()
        response = await _call_client(self.client, state, questions, model=self.model, retry=self.retry)
        latency = (time.perf_counter() - started) * 1000

        if "complete" not in response.nouls:
            raise PolicyError("verification answer missing `complete`")
        complete = response.nouls["complete"].noul
        unmet: dict[str, float] = {}
        for i, req in enumerate(requirements):
            key = f"unmet_{i}"
            if key not in response.nouls:
                raise PolicyError(f"verification answer missing `{key}`")
            unmet[req] = response.nouls[key].noul

        band, reason = band_for(complete, unmet, self.policy)
        if "answer_required" not in response.nouls:
            raise PolicyError("verification answer missing `answer_required`")
        answer_required = response.nouls["answer_required"].noul
        if answer_expected:
            answer_required = max(answer_required, 1.0)

        claims = check_claims(answer, menu.page_text)
        unsupported = tuple(c.claim for c in claims if not c.supported)
        supported_answer: str | None = None
        if claims:
            kept = [c.claim for c in claims if c.supported]
            supported_answer = " ".join(kept) if kept else None
            if not kept and band == "accept":
                band = "verify"
                reason = f"answer has no claim quoted from the page ({len(claims)} unsupported); {reason}"
            elif unsupported:
                reason = f"{len(unsupported)} unsupported claim(s) dropped; {reason}"
        if answer_required >= self.policy.answer_required and not supported_answer and band == "accept":
            # The page may show the outcome, but the task asked for it to be reported; System 1 cannot compose it.
            band = "verify"
            reason = f"task asks for an answer (answer_required={answer_required:.2f}) and none is given; {reason}"

        verdict = Verdict(
            band=band,
            complete=complete,
            unmet=unmet,
            claims=claims,
            reason=reason,
            supported_answer=supported_answer,
            unsupported_claims=unsupported,
            model=response.model,
            latency_ms=latency,
            raw=response,
        )
        log.info("verify: %s (%s)", band, reason)
        return verdict


class ArbiterHook:
    """Minimal surface for task D2: the arbiter calls ``judge_done`` when the policy picks ``done``.

    ``answer`` is the text the run is about to report; pass ``None`` for navigation-only tasks.
    """

    def __init__(self, verifier: Verifier, requirements: tuple[str, ...], *, answer_expected: bool = False):
        self.answer_expected = answer_expected
        self.verifier = verifier
        self.requirements = requirements
        self.last: Verdict | None = None

    async def judge_done(self, agent: Any, menu: Menu, answer: str | None = None) -> tuple[Band, str]:
        verdict = await self.verifier.verify(agent.task, self.requirements, menu, answer, answer_expected=self.answer_expected)
        self.last = verdict
        return verdict.band, verdict.reason
