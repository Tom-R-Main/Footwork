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
    Choice,
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
    #: Package E (Q16): "page" is the claim check as Q12 ran it; "page_and_fields" strips a leading
    #: status label ("UNVERIFIED:") and parenthetical asides before taking atoms, treats a clause of
    #: more than six words after a colon as narrative, and also looks for atoms in the values of
    #: the page's non-secret form fields, which innerText leaves out; a space between a currency sign
    #: and its digits in the page text is closed ("$ 9.99" reads "$9.99"). Since 2026-09-27 it also shows
    #: Jev the field values and applies the no-fact rule only to tasks that ask for an answer.
    #: Default since 2026-09-27 (Q16c, results/q16c.md); "page" is Q12 to Q16's check, kept to reproduce them.
    claim_evidence: str = "page_and_fields"


@dataclass(frozen=True)
class ClaimCheck:
    claim: str
    grade: str  # exact | normalized | none | narrative
    start: int
    end: int
    #: where the evidence was found: "page" (visible text), "field" (a form field's value) or "evidence"
    #: (a value the session's own effect evidence establishes, jevdual.completion)
    source: str = "page"

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
            "claims": [c.grade if c.source == "page" else f"{c.grade}:{c.source}" for c in self.claims],
            "unsupported": len(self.unsupported_claims),
            # package E: which claims failed, so a rejection can be audited from the trace (redacted by
            # the trace writer)
            "unsupported_claims": [c[:160] for c in self.unsupported_claims],
            "reason": self.reason,
        }


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def split_claims(answer: str) -> list[str]:
    """Sentences and lines of an answer."""
    parts = [p.strip() for p in _SENTENCE_SPLIT.split(answer)]
    return [p for p in parts if len(p) >= 2]


_URL_RE = re.compile(r"https?://\S+")
_QUOTED_RE = re.compile(r"[\"“”']([^\"“”']{2,120})[\"“”']")
_NUMBER_RE = re.compile(
    r"(?<![\w.])[$€£]?\d[\d,]*(?:\.\d+)?(?:\s?(?:%|per\s+\w+|nautical\s+miles|miles|km|m|kg|items?|results?))?",
    re.IGNORECASE,
)
_AFTER_COLON_RE = re.compile(r":\s*([^:;]{2,160})$")


#: package E: saucedemo renders "$<!-- -->9.99" and the serializer reads "$ 9.99"
_CURRENCY_GAP_RE = re.compile(r"([$€£¥])\s+(?=\d)")


def close_currency_gaps(text: str) -> str:
    return _CURRENCY_GAP_RE.sub(r"\1", text)


_STATUS_LABEL_RE = re.compile(r"^\s*(?:[-*•]\s*)?[A-Z][A-Z _-]{2,}:\s*")
_ASIDE_RE = re.compile(r"\s*\([^()]*\)")
#: package E: a value after a colon is a value only up to this many words; longer is a clause
MAX_VALUE_WORDS = 6


def clean_claim(sentence: str) -> str:
    """Package E: drop a leading status label ("UNVERIFIED:", "RESULT:") and parenthetical asides,
    which are about the claim, not facts in it."""
    return _ASIDE_RE.sub("", _STATUS_LABEL_RE.sub("", sentence)).strip()


def extract_atoms(sentence: str, *, strict: bool = False) -> list[str]:
    """The evidence-bearing pieces of a sentence: quoted spans, numbers with units or currency,
    and the value after a trailing colon. Narrative words are not evidence and are not atoms.
    URLs are stripped first; page innerText never contains them. ``strict`` (package E) cleans the
    sentence first and keeps a value after a colon only when it has at most ``MAX_VALUE_WORDS`` words."""
    text = _URL_RE.sub(" ", clean_claim(sentence) if strict else sentence)
    atoms: list[str] = [m.group(1).strip() for m in _QUOTED_RE.finditer(text)]
    atoms += [m.group(0).strip() for m in _NUMBER_RE.finditer(text)]
    if strict:
        # an aside is dropped from the value it follows, not from the check: quoted text and numbers
        # inside it are claims too ("Price: $9.99 (shipping $50)"; secondary audit 2026-09-27)
        for aside in _ASIDE_RE.findall(_URL_RE.sub(" ", sentence)):
            atoms += [m.group(1).strip() for m in _QUOTED_RE.finditer(aside)]
            atoms += [m.group(0).strip() for m in _NUMBER_RE.finditer(aside)]
    tail = _AFTER_COLON_RE.search(text)
    if tail:
        value = tail.group(1).strip().rstrip(".")
        if not strict or len(value.split()) <= MAX_VALUE_WORDS:
            atoms.append(value)
    seen: set[str] = set()
    out = []
    for a in atoms:
        key = a.casefold()
        if key and key not in seen and not key.isspace():
            seen.add(key)
            out.append(a)
    return out


def check_claims(
    answer: str | None,
    page_text: str,
    *,
    field_text: str = "",
    strict: bool = False,
    carried: tuple[str, ...] = (),
    evidence: tuple[str, ...] = (),
) -> list[ClaimCheck]:
    """Grade each sentence by its atoms.

    A sentence with no atoms is narrative (grade ``narrative``): kept, never counted as
    evidence. A sentence with atoms is supported only if every atom is found in the page
    text (exact or normalized); the sentence's grade is its worst atom's grade. ``field_text``
    (package E) is the page's form field values: an atom not in the visible text but in a field is
    found there, and the sentence's source says so. ``strict`` is :func:`extract_atoms`'s.
    """
    if not answer:
        return []
    sentences = split_claims(answer)
    if not sentences:
        return []
    per_sentence = [extract_atoms(sn, strict=strict) for sn in sentences]
    # Q19 R4: a value the harness carried is a fact with a recorded source, quoted or not ("by André Gide")
    per_sentence = [
        atoms + [v for v in (*carried, *evidence) if v and v in sn and v not in atoms]
        for sn, atoms in zip(sentences, per_sentence, strict=True)
    ]
    # M1: a value the session's own evidence establishes (a submitted field, a read-back field, a carried
    # read) is supported by that evidence when the final page no longer shows it
    held = {v.casefold() for v in evidence if v}
    if strict:
        page_text, field_text = close_currency_gaps(page_text), close_currency_gaps(field_text)
    flat = [a for atoms in per_sentence for a in atoms]
    results: dict[str, dict[str, Any]] = {}
    field_results: dict[str, dict[str, Any]] = {}
    if flat:
        matcher = native_or_pure("evidence_match")
        for r in matcher(flat, page_text):
            results.setdefault(r["claim"], r)
        missing = [a for a in flat if results.get(a, {}).get("grade", "none") == "none"]
        if field_text and missing:
            for r in matcher(missing, field_text):
                field_results.setdefault(r["claim"], r)
    out: list[ClaimCheck] = []
    order = {"exact": 0, "normalized": 1, "none": 2}
    for sn, atoms in zip(sentences, per_sentence, strict=True):
        if not atoms:
            out.append(ClaimCheck(sn, "narrative", -1, -1))
            continue
        graded = []
        from_field = False
        from_evidence = False
        for a in atoms:
            g = results.get(a, {"grade": "none", "start": -1, "end": -1})
            if g["grade"] == "none" and field_results.get(a, {}).get("grade", "none") != "none":
                g = {**field_results[a], "start": -1, "end": -1}
                from_field = True
            if g["grade"] == "none" and _held(a, sn, held):
                g = {"grade": "exact", "start": -1, "end": -1}
                from_evidence = True
            graded.append(g)
        worst = max(graded, key=lambda g: order.get(g["grade"], 2))
        source = "page"
        if worst["grade"] != "none" and from_evidence:
            source = "evidence"
        elif worst["grade"] != "none" and from_field:
            source = "field"
        out.append(ClaimCheck(sn, worst["grade"], worst.get("start", -1), worst.get("end", -1), source))
    return out


def _held(atom: str, sentence: str, held: set[str]) -> bool:
    """An atom is held by evidence when it is an evidence value, or part of one the sentence states
    whole ("83" of "QUIET-83" in "QUIET-83 27")."""
    a, sn = atom.strip(".,;:!?").casefold(), sentence.casefold()
    return bool(a) and any(a == v or (a in v and v in sn) for v in held)


def field_values(menu: Menu) -> str:
    """Package E: the values of the page's non-secret form fields, one per line, as ``label: value``."""
    lines = []
    for c in menu.candidates:
        if c.value and (c.input_type or "").lower() != "password":
            lines.append(f"{c.label}: {c.value}")
    return "\n".join(lines)


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


def evidence_excerpt(
    full_text: str, answer: str | None, *, head: int = 2_500, window: int = 350, cap: int = 6_000
) -> str:
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
    client: SystemOneClient,
    state: dict[str, Any],
    questions: dict[str, Any],
    *,
    model: str,
    retry: RetryPolicy | None,
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
    def __init__(
        self,
        client: SystemOneClient,
        *,
        model: str = JEV_MODEL,
        policy: VerifyPolicy | None = None,
        retry: RetryPolicy | None = DEFAULT_RETRY,
    ):
        self.client = client
        self.model = model
        self.policy = policy or VerifyPolicy()
        self.retry = retry

    def build_questions(self, requirements: tuple[str, ...], *, ask_kinds: bool = False) -> dict[str, Any]:
        questions: dict[str, Any] = {
            "complete": Noul(
                instructions=prompts.VERIFY_COMPLETE["instructions"],
                criteria={"true": prompts.VERIFY_COMPLETE["true"], "false": prompts.VERIFY_COMPLETE["false"]},
            )
        }
        for i, req in enumerate(requirements):
            spec = prompts.verify_unmet(i, req)
            questions[f"unmet_{i}"] = Noul(
                instructions=spec["instructions"], criteria={"true": spec["true"], "false": spec["false"]}
            )
        questions["answer_required"] = Noul(
            instructions=prompts.VERIFY_ANSWER_REQUIRED["instructions"],
            criteria={
                "true": prompts.VERIFY_ANSWER_REQUIRED["true"],
                "false": prompts.VERIFY_ANSWER_REQUIRED["false"],
            },
        )
        if ask_kinds:
            # task-static: asked in the first verification of a run only, in the same request
            for i, req in enumerate(requirements):
                spec = prompts.verify_kind(i, req)
                questions[f"kind_{i}"] = Choice(instructions=spec["instructions"], criteria=spec["criteria"])
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

    async def judge_destructive(
        self, task: str, targets: list[dict[str, str]], *, url: str, title: str
    ) -> list[float]:
        """Q8 gate: one Noul per proposed click target, asked together, before System 2's action executes.

        The System 1 arbiter already answers this for its own decisions; System 2's proposals went
        through the keyword list alone and posted an unauthorised order labelled "Submit order"
        (results/q8-consent.md). ``targets`` carry ``label`` and ``context`` (URL, title, ancestor text).
        """
        if not targets:
            return []
        state = {
            "task": task,
            "page": {"url": url, "title": title},
            "targets": [
                {"label": t.get("label", ""), "context": t.get("context", "")[:300]} for t in targets
            ],
        }
        questions = {
            f"destructive_{i}": Noul(
                instructions=(
                    f"Would clicking the control `targets[{i}].label` on this page do something that cannot be undone "
                    "by going back: place, finish or submit an order, submit a form that sends data to someone else, "
                    "make a payment, delete or remove stored data, send or publish a message? Judge the control, "
                    "not whether `task` asks for it."
                ),
                criteria={
                    "true": "The control commits: place order, finish, submit order, confirm purchase, pay, checkout "
                    "and pay, send, publish, delete account, remove stored data.",
                    "false": "The control navigates, opens, sorts, filters, selects, adds to a cart, signs in, continues "
                    "to a later step that does not itself commit, or fills a field.",
                },
            )
            for i in range(len(targets))
        }
        response = await _call_client(self.client, state, questions, model=self.model, retry=self.retry)
        out = []
        for i in range(len(targets)):
            key = f"destructive_{i}"
            if key not in response.nouls:
                raise PolicyError(f"gate answer missing `{key}`")
            out.append(float(response.nouls[key].noul))
        return out

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
        answer_matters: bool = True,
        carried: tuple[str, ...] = (),
        effects: tuple[Any, ...] = (),
    ) -> Verdict:
        ask_kinds = ledger is not None and not ledger.kinds and bool(requirements)
        questions = self.build_questions(requirements, ask_kinds=ask_kinds)
        state = self.build_state(task, requirements, menu, answer, trajectory)
        if effects:
            # M1: what this run's own records establish about the requested effect, each with its kind,
            # step and limits, apart from the memory lines of the trajectory
            state["evidence"] = [e.line() for e in effects]
        strict = self.policy.claim_evidence == "page_and_fields"
        if strict and (fields := field_values(menu)):
            # the form's values are part of what the page shows; innerText leaves them out, so Jev judged
            # a filled form unfilled (claims audit A4, 2026-09-27)
            state["page"]["fields"] = fields
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

        if ask_kinds and ledger is not None:
            kinds = {}
            for i, req in enumerate(requirements):
                ans = response.choices.get(f"kind_{i}")
                if ans is not None and getattr(ans, "choice", None) in (
                    "historical_action",
                    "current_state",
                    "answer",
                ):
                    kinds[req] = ans.choice
            ledger.set_kinds(kinds)
        # what earlier verifications in this run established, by requirement kind (jevdual.ledger)
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

        claims = check_claims(
            answer,
            menu.full_text or menu.page_text,
            field_text=field_values(menu) if strict else "",
            strict=strict,
            carried=carried,
            evidence=tuple(v for e in effects if e.usable for v in e.values),
        )
        unsupported = tuple(c.claim for c in claims if not c.supported)
        supported_answer: str | None = None
        if claims:
            kept = [c.claim for c in claims if c.supported]
            evidence = [c for c in claims if c.is_evidence]
            supported_answer = " ".join(kept) if evidence else None
            # strict: a done that states no fact at all ("Opened the cart.") needs none on a task that asks
            # no answer (claims audit A8); a done that states a fact the page lacks is demoted whatever
            # the task (test_confidently_wrong_done_cannot_accept_without_evidence caught the looser
            # rule at adoption: "45 metres" passed when Jev judged the task not to ask for an answer)
            states_facts = any(c.grade != "narrative" for c in claims)
            needs_fact = not strict or states_facts or answer_required >= self.policy.answer_required
            if not evidence and band == "accept" and needs_fact:
                band = "verify"
                reason = f"answer carries no fact found on the page ({len(unsupported)} unsupported, rest narrative); {reason}"
            elif unsupported:
                reason = f"{len(unsupported)} unsupported claim(s) dropped; {reason}"
        if (
            answer_matters
            and answer_required >= self.policy.answer_required
            and not supported_answer
            and band == "accept"
        ):
            # The page may show the outcome, but the task asked for it to be reported; System 1 cannot compose it.
            band = "verify"
            reason = (
                f"task asks for an answer (answer_required={answer_required:.2f}) and none is given; {reason}"
            )

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

    async def verify_subgoal(
        self,
        task: str,
        subgoal: str,
        stop_condition: str,
        menu: Menu,
        trajectory: list[dict[str, Any]] | None = None,
    ) -> tuple[float, str]:
        """Observed support for a delegated subgoal: one Noul over the page and the trajectory."""
        questions = {
            "subgoal_met": Noul(
                instructions=prompts.VERIFY_SUBGOAL["instructions"],
                criteria={"true": prompts.VERIFY_SUBGOAL["true"], "false": prompts.VERIFY_SUBGOAL["false"]},
            )
        }
        state: dict[str, Any] = {
            "task": task,
            "subgoal": subgoal,
            "stop_condition": stop_condition,
            "page": {"url": menu.url, "title": menu.title, "text": menu.page_text},
        }
        if trajectory:
            state["trajectory"] = trajectory
        response = await _call_client(self.client, state, questions, model=self.model, retry=self.retry)
        if "subgoal_met" not in response.nouls:
            raise PolicyError("subgoal verification answer missing `subgoal_met`")
        p = response.nouls["subgoal_met"].noul
        return p, f"subgoal_met p={p:.2f}"


class ArbiterHook:
    """Minimal surface for task D2: the arbiter calls ``judge_done`` when the policy picks ``done``.

    ``answer`` is the text the run is about to report; pass ``None`` for navigation-only tasks.
    """

    def __init__(
        self,
        verifier: Verifier,
        requirements: tuple[str, ...],
        *,
        answer_expected: bool = False,
        use_trajectory: bool = True,
    ):
        self.answer_expected = answer_expected
        self.verifier = verifier
        self.requirements = requirements
        self.last: Verdict | None = None
        #: one ledger per hook, and the hook is created per run (evals.runner.default_policy_factory)
        self.ledger = Ledger()
        self.use_trajectory = use_trajectory
        self.subgoal_met_threshold = 0.80

    async def judge_done(self, agent: Any, menu: Menu, answer: str | None = None) -> tuple[Band, str]:
        trajectory = None
        if self.use_trajectory:
            store = getattr(getattr(agent, "s1_policy", None), "secrets", None)
            trajectory = trajectory_from_agent(agent, store.redactor() if store is not None else None)
        verdict = await self.verifier.verify(
            agent.task,
            self.requirements,
            menu,
            answer,
            answer_expected=self.answer_expected,
            trajectory=trajectory,
            ledger=self.ledger,
        )
        self.last = verdict
        return verdict.band, verdict.reason

    async def judge_subgoal(
        self, agent: Any, menu: Menu, subgoal: str, stop_condition: str
    ) -> tuple[bool, str]:
        """True when the delegated subgoal's stop condition has observed support. Uses the same
        verification and accept band as a done (complete on the subgoal, unmet on the stop condition,
        trajectory in view) so a page the done verifier accepts is not refused as a subgoal: the
        single-noul check refused a reached sign-in at p=0.75 (Q9c)."""
        trajectory = None
        if self.use_trajectory:
            store = getattr(getattr(agent, "s1_policy", None), "secrets", None)
            trajectory = trajectory_from_agent(agent, store.redactor() if store is not None else None)
        # the subgoal alone is the task here: the whole task's wording made the answer-required rule
        # refuse navigation subgoals on answer tasks (Q8/Q9e second launch)
        verdict = await self.verifier.verify(
            subgoal, (stop_condition,), menu, None, trajectory=trajectory, answer_matters=False
        )
        return verdict.band == "accept", f"subgoal {verdict.band}: {verdict.reason}"
