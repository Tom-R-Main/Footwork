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
from jevdual.ledger import Ledger, trajectory_from_agent
from jevdual.menu import Menu
from jevdual.policy import DEFAULT_RETRY, JEV_MODEL, PolicyError, SystemOneClient

log = logging.getLogger("jevdual.verify")

Band = Literal["accept", "reject", "verify"]


@dataclass(frozen=True)
class VerifyPolicy:
    """Band thresholds.

    Frozen for the fixture heldout in E1 at accept complete >= 0.85 and every unmet <= 0.20. Widened on
    2026-09-21 after the live ledger smoke (results/ledger-smoke-20260921-141456): with the trajectory
    ledger, the per-requirement ``unmet`` values settle at 0.22 to 0.30 for requirements the predicate
    confirms met, and ``complete`` at 0.84 to 0.91, so the old band left every one of those runs in
    "verify" and then UNVERIFIED. The accept band is a conjunction over all requirements, so a floor of
    0.20 on each is far stricter than 0.20 on one. The reject band is unchanged. Q3 revisits both
    numbers from labelled trajectories; the fixture heldout is rerun once on adoption (program rule).
    """

    accept_complete: float = 0.80
    accept_unmet_max: float = 0.30
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

    @property
    def is_evidence(self) -> bool:
        return self.grade in ("exact", "normalized")


@dataclass(frozen=True)
class Verdict:
    band: Band
    complete: float
    unmet: dict[str, float]
    claims: list[ClaimCheck]
    reason: str
    unmet_effective: dict[str, float] = field(default_factory=dict)
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
            "unmet_effective": {k: round(v, 3) for k, v in self.unmet_effective.items()},
            "unmet": {k: round(v, 3) for k, v in self.unmet.items()},
            "claims": [c.grade for c in self.claims],
            "unsupported": len(self.unsupported_claims),
            "reason": self.reason,
        }


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def split_claims(answer: str) -> list[str]:
    """Sentences and lines of an answer."""
    parts = [p.strip() for p in _SENTENCE_SPLIT.split(answer)]
    return [p for p in parts if len(p) >= 2]


_URL_RE = re.compile(r"https?://\S+")
_QUOTED_RE = re.compile(r"[\"“”']([^\"“”']{2,120})[\"“”']")
_NUMBER_RE = re.compile(r"(?<![\w.])[$€£]?\d[\d,]*(?:\.\d+)?(?:\s?(?:%|per\s+\w+|nautical\s+miles|miles|km|m|kg|items?|results?))?", re.IGNORECASE)
_AFTER_COLON_RE = re.compile(r":\s*([^:;]{2,160})$")


def extract_atoms(sentence: str) -> list[str]:
    """The evidence-bearing pieces of a sentence: quoted spans, numbers with units or currency,
    and the value after a trailing colon. Narrative words are not evidence and are not atoms.
    URLs are stripped first; page innerText never contains them."""
    text = _URL_RE.sub(" ", sentence)
    atoms: list[str] = [m.group(1).strip() for m in _QUOTED_RE.finditer(text)]
    atoms += [m.group(0).strip() for m in _NUMBER_RE.finditer(text)]
    tail = _AFTER_COLON_RE.search(text)
    if tail:
        atoms.append(tail.group(1).strip().rstrip("."))
    seen: set[str] = set()
    out = []
    for a in atoms:
        key = a.casefold()
        if key and key not in seen and not key.isspace():
            seen.add(key)
            out.append(a)
    return out


def check_claims(answer: str | None, page_text: str) -> list[ClaimCheck]:
    """Grade each sentence by its atoms.

    A sentence with no atoms is narrative (grade ``narrative``): kept, never counted as
    evidence. A sentence with atoms is supported only if every atom is found in the page
    text (exact or normalized); the sentence's grade is its worst atom's grade.
    """
    if not answer:
        return []
    sentences = split_claims(answer)
    if not sentences:
        return []
    per_sentence = [extract_atoms(sn) for sn in sentences]
    flat = [a for atoms in per_sentence for a in atoms]
    results = {}
    if flat:
        matcher = native_or_pure("evidence_match")
        for r in matcher(flat, page_text):
            results.setdefault(r["claim"], r)
    out: list[ClaimCheck] = []
    order = {"exact": 0, "normalized": 1, "none": 2}
    for sn, atoms in zip(sentences, per_sentence, strict=True):
        if not atoms:
            out.append(ClaimCheck(sn, "narrative", -1, -1))
            continue
        graded = [results.get(a, {"grade": "none", "start": -1, "end": -1}) for a in atoms]
        worst = max(graded, key=lambda g: order.get(g["grade"], 2))
        out.append(ClaimCheck(sn, worst["grade"], worst.get("start", -1), worst.get("end", -1)))
    return out


_IDENTIFIER = re.compile(r"\b(?:[A-Za-z]+[A-Z][A-Za-z0-9]*|[A-Za-z]+_[A-Za-z0-9_]+|[A-Z][a-z]{3,})\b")


def _excerpt_needles(claim: str) -> list[str]:
    """What to look for in the page for one claim: its evidence atoms, plus identifier-like and
    capitalised tokens (KeyError, font-weight's neighbours, Guido) when a claim carries no atom."""
    needles = list(extract_atoms(claim))
    words = claim.split()
    for tok in _IDENTIFIER.findall(claim):
        if words and tok == words[0].strip(".,:;"):
            continue  # sentence-initial capital is not evidence
        if tok not in needles:
            needles.append(tok)
    return needles


def evidence_excerpt(full_text: str, answer: str | None, *, head: int = 2_500, window: int = 350, cap: int = 6_000) -> str:
    """Page text for verification: the head of the page plus windows around every place the answer's
    evidence atoms occur, so a fact deep in a long page (a definition 9,000 characters down) is in view.
    Without an answer, or when everything fits, this is just the head."""
    if len(full_text) <= cap or not answer:
        return full_text[:cap]
    folded = full_text.casefold()
    spans: list[tuple[int, int]] = [(0, head)]
    for claim in split_claims(answer):
        for atom in _excerpt_needles(claim):
            needle = atom.casefold()
            start = 0
            hits = 0
            while hits < 3:
                i = folded.find(needle, start)
                if i < 0:
                    break
                spans.append((max(0, i - window), min(len(full_text), i + len(needle) + window)))
                start = i + len(needle)
                hits += 1
    spans.sort()
    merged: list[list[int]] = []
    for a, b in spans:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    out: list[str] = []
    used = 0
    for a, b in merged:
        piece = full_text[a:b]
        if used + len(piece) > cap:
            piece = piece[: max(0, cap - used)]
        if piece:
            out.append(piece)
            used += len(piece)
        if used >= cap:
            break
    return " … ".join(out)


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
    def build_state(
        task: str,
        requirements: tuple[str, ...],
        menu: Menu,
        answer: str | None,
        trajectory: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        text = evidence_excerpt(menu.full_text, answer) if (answer and menu.full_text) else menu.page_text
        state: dict[str, Any] = {
            "task": task,
            "requirements": list(requirements),
            "page": {"url": menu.url, "title": menu.title, "text": text},
        }
        if trajectory:
            state["trajectory"] = trajectory
        if answer:
            state["answer"] = answer
        return state

    async def verify(
        self,
        task: str,
        requirements: tuple[str, ...],
        menu: Menu,
        answer: str | None,
        *,
        answer_expected: bool = False,
        trajectory: list[dict[str, Any]] | None = None,
        ledger: Ledger | None = None,
    ) -> Verdict:
        questions = self.build_questions(requirements)
        state = self.build_state(task, requirements, menu, answer, trajectory)
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

        # a requirement judged met earlier in this run stays met (jevdual.ledger)
        unmet_effective = ledger.apply(unmet) if ledger is not None else dict(unmet)
        if ledger is not None:
            ledger.update(unmet)
        band, reason = band_for(complete, unmet_effective, self.policy)
        if ledger is not None and unmet_effective != unmet:
            carried = [req for req in unmet if unmet_effective[req] < unmet[req]]
            reason = f"{reason}; ledger carried {len(carried)} requirement(s)"
        if "answer_required" not in response.nouls:
            raise PolicyError("verification answer missing `answer_required`")
        answer_required = response.nouls["answer_required"].noul
        if answer_expected:
            answer_required = max(answer_required, 1.0)

        claims = check_claims(answer, menu.full_text or menu.page_text)
        unsupported = tuple(c.claim for c in claims if not c.supported)
        supported_answer: str | None = None
        if claims:
            kept = [c.claim for c in claims if c.supported]
            evidence = [c for c in claims if c.is_evidence]
            supported_answer = " ".join(kept) if evidence else None
            if not evidence and band == "accept":
                band = "verify"
                reason = f"answer carries no fact found on the page ({len(unsupported)} unsupported, rest narrative); {reason}"
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
            unmet_effective=unmet_effective,
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

    def __init__(self, verifier: Verifier, requirements: tuple[str, ...], *, answer_expected: bool = False, use_trajectory: bool = True):
        self.answer_expected = answer_expected
        self.verifier = verifier
        self.requirements = requirements
        self.last: Verdict | None = None
        #: one ledger per hook, and the hook is created per run (evals.runner.default_policy_factory)
        self.ledger = Ledger()
        self.use_trajectory = use_trajectory

    async def judge_done(self, agent: Any, menu: Menu, answer: str | None = None) -> tuple[Band, str]:
        trajectory = None
        if self.use_trajectory:
            store = getattr(getattr(agent, "s1_policy", None), "secrets", None)
            trajectory = trajectory_from_agent(agent, store.redactor() if store is not None else None)
        verdict = await self.verifier.verify(
            agent.task, self.requirements, menu, answer, answer_expected=self.answer_expected, trajectory=trajectory, ledger=self.ledger
        )
        self.last = verdict
        return verdict.band, verdict.reason
