"""System 1 policy: one speculative fan-out Jev request per step.

Every question the step needs goes in a single ``system_one`` call: an
``operation`` Choice over the offered operations, one ``<op>_target`` Choice per
targeted operation (only the chosen operation's head is consumed; the rest were
free pre-computation), and six absolute Nouls. Code validates the answers,
keeps the full distributions for next-best retry, and never lets the model emit
anything but an option id.

Heads that would exceed Jev's option cap become a ``<op>_group`` Choice plus one
speculative ``<op>_target_g<i>`` head per group. When even that does not fit the
token budget the per-group heads are dropped and ``Decision.two_stage`` is set;
the caller then asks ``decide_target`` with the chosen group's candidate ids.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from typesafe_sdk import (
    Choice,
    ChoiceAnswer,
    Noul,
    RetryPolicy,
    SystemOneResponse,
    TypeSafeAPIConnectionError,
    TypeSafeAPIError,
    TypeSafeAPITimeoutError,
    TypeSafeError,
    TypeSafeRateLimitError,
)

from jevdual import menu as menu_mod
from jevdual import prompts
from jevdual.menu import (
    OPERATIONS,
    REQUEST_TOKEN_BUDGET,
    STATE_TOKEN_BUDGET,
    Candidate,
    Menu,
    MenuBudget,
)
from jevdual.trace import DecisionRecord, JevHead

log = logging.getLogger("jevdual.policy")

#: Pinned, not the ``jev-latest`` alias: every arbiter threshold is tuned against one version.
JEV_MODEL = "jev-1.13.0"

#: Operations that need no element target. Always offered.
NON_TARGETED: tuple[str, ...] = ("scroll_page", "back", "wait", "done", "blocked")

#: Honor retry-after on 429/5xx; the SDK retries connection and timeout errors by default.
DEFAULT_RETRY = RetryPolicy(max_retries=2, respect_retry_after=True, timeout=30.0)

PROBABILITY_SUM_TOLERANCE = 0.02


class PolicyError(Exception):
    """A step could not get a valid decision. ``retryable`` says whether waiting may help."""

    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class SystemOneClient(Protocol):
    async def system_one(self, state: Any, questions: Any, *, model: str | None = None, **kwargs: Any) -> SystemOneResponse: ...


@dataclass(frozen=True)
class StepContext:
    task: str
    requirements: tuple[str, ...] = ()
    notes: str = ""
    recent_actions: tuple[str, ...] = ()
    step: int = 1
    secrets_names: tuple[str, ...] = ()
    subgoal: str | None = None
    #: Bounded assignment from System 2 (jevdual.s1.Delegation): only these targeted operations are
    #: offered; known field values are typed without composing text; the stop condition is stated.
    allowed_operations: tuple[str, ...] = ()
    known_values: tuple[tuple[str, str], ...] = ()
    stop_condition: str | None = None


@dataclass(frozen=True)
class Request:
    """A built request plus the bookkeeping needed to consume its answers."""

    state: dict[str, Any]
    questions: dict[str, Choice | Noul]
    targets: dict[str, tuple[Candidate, ...]]
    groups: dict[str, tuple[tuple[Candidate, ...], ...]]
    group_heads: dict[str, bool]
    offered: tuple[str, ...]
    estimated_tokens: int

    @property
    def two_stage_ops(self) -> tuple[str, ...]:
        return tuple(op for op, has_heads in self.group_heads.items() if not has_heads)


@dataclass(frozen=True)
class Decision:
    operation: str
    operation_confidence: float
    operation_probabilities: dict[str, float]
    target: int | None
    target_confidence: float | None
    target_probabilities: dict[int, float]
    alternates: tuple[int, ...]
    nouls: dict[str, float]
    model: str
    request_tokens: int | None
    latency_ms: float
    two_stage: bool = False
    pending_group: tuple[int, ...] = ()
    group_confidence: float | None = None
    raw: SystemOneResponse | None = field(default=None, compare=False, repr=False)

    @property
    def targeted(self) -> bool:
        return self.operation in OPERATIONS

    def to_trace(self, omitted_elements: int = 0) -> DecisionRecord:
        target_head = None
        if self.targeted and (self.target is not None or self.target_probabilities):
            target_head = JevHead(
                choice=str(self.target) if self.target is not None else "",
                confidence=self.target_confidence,
                probabilities={str(k): v for k, v in self.target_probabilities.items()},
            )
        return DecisionRecord(
            operation=JevHead(
                choice=self.operation,
                confidence=self.operation_confidence,
                probabilities=dict(self.operation_probabilities),
            ),
            target=target_head,
            nouls=dict(self.nouls),
            model=self.model,
            request_tokens=self.request_tokens,
            latency_ms=self.latency_ms,
            omitted_elements=omitted_elements,
        )


def _chunk(candidates: tuple[Candidate, ...], size: int) -> tuple[tuple[Candidate, ...], ...]:
    """Group candidates for the two-stage choice (delegates to ``menu.group_candidates``)."""
    return menu_mod.group_candidates(candidates, size)


def _estimate_tokens(obj: Any, chars_per_token: float) -> int:
    return int(len(json.dumps(obj, ensure_ascii=False)) / chars_per_token) + 1


def _question_tokens(question: Choice | Noul, chars_per_token: float) -> int:
    return _estimate_tokens(question.model_dump(), chars_per_token)


class JevPolicy:
    """Builds and consumes the per-step fan-out request."""

    def __init__(
        self,
        client: SystemOneClient,
        *,
        model: str = JEV_MODEL,
        budget: MenuBudget | None = None,
        retry: RetryPolicy | None = DEFAULT_RETRY,
    ):
        self.client = client
        self.model = model
        self.budget = budget or MenuBudget()
        self.retry = retry

    # ---- request building -----------------------------------------------------------------

    def build_state(self, menu: Menu, ctx: StepContext) -> dict[str, Any]:
        state: dict[str, Any] = {
            "task": ctx.task,
            "requirements": list(ctx.requirements),
            "notes": ctx.notes,
            "recent_actions": list(ctx.recent_actions),
            "page": {"url": menu.url, "title": menu.title, "text": menu.page_text},
            "elements": [c.to_state() for c in menu.candidates],
        }
        if menu.omitted:
            state["omitted_elements"] = dict(menu.omitted)
        if len(menu.tabs) > 1:
            state["tabs"] = [dict(t) for t in menu.tabs]
        if ctx.secrets_names:
            state["stored_secrets"] = list(ctx.secrets_names)
        if ctx.subgoal:
            state["subgoal"] = ctx.subgoal
        if ctx.stop_condition:
            state["stop_condition"] = ctx.stop_condition
        if ctx.known_values:
            state["known_values"] = {k: v for k, v in ctx.known_values}
        return state

    def offered_operations(self, menu: Menu, ctx: StepContext | None = None) -> tuple[str, ...]:
        targeted = tuple(op for op in OPERATIONS if menu.by_operation.get(op))
        if ctx is not None and ctx.allowed_operations:
            targeted = tuple(op for op in targeted if op in ctx.allowed_operations)
        return targeted + NON_TARGETED

    def build_request(self, menu: Menu, ctx: StepContext) -> Request:
        b = self.budget
        state = self.build_state(menu, ctx)
        offered = self.offered_operations(menu, ctx)
        questions: dict[str, Choice | Noul] = {
            "operation": Choice(
                instructions=prompts.operation_instructions(ctx.task, ctx.subgoal, ctx.stop_condition),
                criteria={op: prompts.operation_criteria_for(ctx.subgoal)[op] for op in offered},
            )
        }
        targets: dict[str, tuple[Candidate, ...]] = {}
        groups: dict[str, tuple[tuple[Candidate, ...], ...]] = {}
        group_heads: dict[str, bool] = {}
        for op in offered:
            if op not in OPERATIONS:
                continue
            cands = tuple(menu.by_operation[op])
            if len(cands) <= b.max_options:
                targets[op] = cands
                questions[f"{op}_target"] = self._target_question(ctx, op, cands)
                continue
            chunks = _chunk(cands, b.group_size)
            if len(chunks) > b.max_options:
                raise PolicyError(f"{op}: {len(cands)} candidates exceed even the grouped option cap")
            groups[op] = chunks
            questions[f"{op}_group"] = Choice(
                instructions=prompts.group_instructions(ctx.task, op, ctx.subgoal),
                criteria={str(i): " | ".join(c.label[:40] for c in chunk) for i, chunk in enumerate(chunks)},
            )
            for i, chunk in enumerate(chunks):
                questions[f"{op}_target_g{i}"] = self._target_question(ctx, op, chunk)
            group_heads[op] = True
        for name, spec in prompts.nouls_for(ctx.subgoal).items():
            questions[name] = Noul(
                instructions=spec["instructions"], criteria={"true": spec["true"], "false": spec["false"]}
            )

        # Budget check; drop speculative per-group heads first, then fail loudly.
        est = self._fits(state, questions)
        if est is None and groups:
            for op, chunks in groups.items():
                for i in range(len(chunks)):
                    questions.pop(f"{op}_target_g{i}", None)
                group_heads[op] = False
            est = self._fits(state, questions)
        if est is None:
            raise PolicyError("request exceeds the Jev token budget; the menu builder must trim further")
        return Request(state, questions, targets, groups, group_heads, offered, est)

    def _target_question(self, ctx: StepContext, op: str, cands: tuple[Candidate, ...]) -> Choice:
        # Attributes go in the criteria, not only in state: fastbrowse measured that a criterion the
        # model has to look up elsewhere is a worse criterion, and the request was never the slow part.
        return Choice(
            instructions=prompts.target_instructions(ctx.task, op, ctx.subgoal),
            criteria={str(c.id): c.to_state() for c in cands},
        )

    def _fits(self, state: dict[str, Any], questions: dict[str, Choice | Noul]) -> int | None:
        cpt = self.budget.chars_per_token
        s = _estimate_tokens(state, cpt)
        sizes = [_question_tokens(q, cpt) for q in questions.values()]
        largest = s + max(sizes)
        total = s + sum(sizes)
        if largest > min(self.budget.state_tokens, STATE_TOKEN_BUDGET) or total > REQUEST_TOKEN_BUDGET:
            return None
        return total

    # ---- calling and consuming ------------------------------------------------------------

    async def _call(self, state: dict[str, Any], questions: dict[str, Choice | Noul]) -> tuple[SystemOneResponse, float]:
        kwargs: dict[str, Any] = {"model": self.model}
        if self.retry is not None:
            kwargs["retry"] = self.retry
        started = time.perf_counter()
        try:
            response = await self.client.system_one(state, questions, **kwargs)
        except TypeSafeRateLimitError as exc:
            raise PolicyError(f"rate limited: {exc}", retryable=True) from exc
        except (TypeSafeAPITimeoutError, TypeSafeAPIConnectionError) as exc:
            raise PolicyError(f"connection: {exc}", retryable=True) from exc
        except TypeSafeAPIError as exc:
            raise PolicyError(f"api error: {exc}", retryable=exc.status >= 500) from exc
        except TypeSafeError as exc:
            raise PolicyError(f"sdk error: {exc}") from exc
        return response, (time.perf_counter() - started) * 1000

    async def decide(self, menu: Menu, ctx: StepContext) -> Decision:
        request = self.build_request(menu, ctx)
        last_error: str | None = None
        for attempt in (1, 2):
            response, latency = await self._call(request.state, request.questions)
            try:
                return self._consume(request, response, latency)
            except _InvalidAnswer as exc:
                last_error = str(exc)
                log.warning("step %s attempt %s: invalid Jev answer: %s", ctx.step, attempt, exc)
        raise PolicyError(f"invalid answer twice: {last_error}")

    async def decide_target(self, menu: Menu, ctx: StepContext, operation: str, candidate_ids: tuple[int, ...]) -> Decision:
        """Second stage after a ``two_stage`` decision: pick the element inside the chosen group."""
        cands = tuple(c for c in menu.candidates if c.id in set(candidate_ids))
        if not cands:
            raise PolicyError("decide_target: no candidates for the pending group")
        state = self.build_state(menu, ctx)
        key = f"{operation}_target"
        questions: dict[str, Choice | Noul] = {key: self._target_question(ctx, operation, cands)}
        last_error: str | None = None
        for _ in (1, 2):
            response, latency = await self._call(state, questions)
            try:
                answer = _validate_choice(response.choices.get(key), {str(c.id) for c in cands}, key)
            except _InvalidAnswer as exc:
                last_error = str(exc)
                continue
            probs = {int(k): v for k, v in answer.probabilities.items()}
            chosen = int(answer.choice)
            return Decision(
                operation=operation,
                operation_confidence=1.0,
                operation_probabilities={operation: 1.0},
                target=chosen,
                target_confidence=answer.confidence,
                target_probabilities=probs,
                alternates=_alternates(probs, chosen),
                nouls={},
                model=response.model,
                request_tokens=response.usage.input_tokens,
                latency_ms=latency,
                raw=response,
            )
        raise PolicyError(f"invalid target answer twice: {last_error}")

    def _consume(self, request: Request, response: SystemOneResponse, latency: float) -> Decision:
        op_answer = _validate_choice(response.choices.get("operation"), set(request.offered), "operation")
        op = op_answer.choice
        nouls = {name: response.nouls[name].noul for name in prompts.NOULS if name in response.nouls}
        missing = [name for name in prompts.NOULS if name not in nouls]
        if missing:
            raise _InvalidAnswer(f"missing noul answers: {missing}")

        target: int | None = None
        target_conf: float | None = None
        target_probs: dict[int, float] = {}
        two_stage = False
        pending: tuple[int, ...] = ()
        group_conf: float | None = None

        if op in request.targets:
            key = f"{op}_target"
            answer = _validate_choice(response.choices.get(key), {str(c.id) for c in request.targets[op]}, key)
            target_probs = {int(k): v for k, v in answer.probabilities.items()}
            target, target_conf = int(answer.choice), answer.confidence
        elif op in request.groups:
            chunks = request.groups[op]
            g_answer = _validate_choice(response.choices.get(f"{op}_group"), {str(i) for i in range(len(chunks))}, f"{op}_group")
            gi = int(g_answer.choice)
            group_conf = g_answer.confidence
            chunk = chunks[gi]
            if request.group_heads.get(op):
                key = f"{op}_target_g{gi}"
                answer = _validate_choice(response.choices.get(key), {str(c.id) for c in chunk}, key)
                target_probs = {int(k): v for k, v in answer.probabilities.items()}
                target = int(answer.choice)
                # The element was only chosen inside the group: a doubtful group is a doubtful target.
                target_conf = g_answer.confidence * answer.confidence
            else:
                two_stage = True
                pending = tuple(c.id for c in chunk)

        return Decision(
            operation=op,
            operation_confidence=op_answer.confidence,
            operation_probabilities=dict(op_answer.probabilities),
            target=target,
            target_confidence=target_conf,
            target_probabilities=target_probs,
            alternates=_alternates(target_probs, target),
            nouls=nouls,
            model=response.model,
            request_tokens=response.usage.input_tokens,
            latency_ms=latency,
            two_stage=two_stage,
            pending_group=pending,
            group_confidence=group_conf,
            raw=response,
        )


class _InvalidAnswer(Exception):
    pass


def _validate_choice(answer: ChoiceAnswer | None, options: set[str], key: str) -> ChoiceAnswer:
    if answer is None:
        raise _InvalidAnswer(f"{key}: no choice answer")
    if answer.choice not in options:
        raise _InvalidAnswer(f"{key}: choice {answer.choice!r} not in options")
    if set(answer.probabilities) != options:
        raise _InvalidAnswer(f"{key}: probability keys do not match options")
    total = sum(answer.probabilities.values())
    if abs(total - 1.0) > PROBABILITY_SUM_TOLERANCE:
        raise _InvalidAnswer(f"{key}: probabilities sum to {total:.3f}")
    argmax = max(answer.probabilities, key=lambda k: answer.probabilities[k])
    if answer.probabilities[argmax] > answer.probabilities[answer.choice] + 1e-9:
        raise _InvalidAnswer(f"{key}: choice {answer.choice!r} is not the argmax ({argmax!r})")
    return answer


def _alternates(probs: dict[int, float], chosen: int | None) -> tuple[int, ...]:
    return tuple(k for k, _ in sorted(probs.items(), key=lambda kv: -kv[1]) if k != chosen)
