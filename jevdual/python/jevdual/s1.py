"""System 1 policy for DualProcessAgent: menu -> Jev -> arbiter -> bridge.

``JevS1`` is the ``S1Policy`` the agent calls each step. It builds the menu
from the live snapshot, asks Jev once, lets the arbiter (task D2) decide
whether to act, escalate, confirm or retry the next-best target, composes
text through ``text_source`` (task D4) when the operation needs it, bridges
the decision to browser-use actions, and refuses to dispatch on a stale
snapshot. Everything it decided is kept in ``agent.s1_records`` for the trace.
"""

from __future__ import annotations

import dataclasses
import inspect
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, Protocol

from jevdual.bridge import Bridge, Bridged, BridgeError, assert_fresh
from jevdual.menu import Candidate, Menu, build_menu
from jevdual.policy import Decision, JevPolicy, PolicyError, StepContext
from jevdual.secrets import SecretStore
from jevdual.trace import ActionRecord

if TYPE_CHECKING:
    from browser_use.browser.views import BrowserStateSummary

    from jevdual.agent import DualProcessAgent

log = logging.getLogger("jevdual.s1")

VerdictKind = Literal["act", "escalate", "confirm", "retry_alternate"]


@dataclass(frozen=True)
class Verdict:
    kind: VerdictKind
    reason: str


class Arbiter(Protocol):
    """Task D2 implements this. ``judge`` never dispatches; it only rules."""

    def judge(self, decision: Decision, menu: Menu, ctx: StepContext, agent: DualProcessAgent) -> Verdict: ...


class AlwaysAct:
    """Arbiter used by the S1-only eval arm and the spike: never escalates."""

    def judge(self, decision: Decision, menu: Menu, ctx: StepContext, agent: Any) -> Verdict:
        return Verdict("act", "always-act arbiter")


TextSource = Callable[[str, Candidate, Menu], Any]  # returns str | None, possibly awaitable


def _known_value_for(target: Candidate, known: tuple[tuple[str, str], ...]) -> str | None:
    """A value System 2 supplied for this field, matched on the field's label or section (case-insensitive)."""
    if not known:
        return None
    hay = " ".join(x for x in (target.label, getattr(target, "section", None) or "") if x).casefold()
    for key, value in known:
        if key.casefold() in hay:
            return value
    return None


def literal_text_source(task: str, target: Candidate, menu: Menu) -> str | None:
    """Placeholder until D4: only a single double-quoted literal in the task is typed verbatim."""
    parts = task.split('"')
    if len(parts) == 3 and parts[1].strip():
        return parts[1].strip()
    return None


@dataclass
class S1Record:
    step: int
    decision: Decision | None
    verdict: Verdict | None
    proposed: tuple[ActionRecord, ...] = ()
    verify: dict[str, Any] | None = None
    menu_omitted: dict[str, int] = field(default_factory=dict)
    error: str | None = None
    menu_ms: float = 0.0
    jev_ms: float = 0.0


def redact_menu(menu: Menu, red: Callable[[str], str]) -> Menu:
    """A copy of the menu with every model-facing string passed through the secret redactor."""

    def rc(c: Candidate) -> Candidate:
        return dataclasses.replace(
            c,
            label=red(c.label),
            value=red(c.value) if c.value else c.value,
            href=red(c.href) if c.href else c.href,
            section=red(c.section) if c.section else c.section,
            options=tuple(red(o) for o in c.options) if c.options else c.options,
        )

    cands = tuple(rc(c) for c in menu.candidates)
    by_id = {c.id: c for c in cands}
    return dataclasses.replace(
        menu,
        url=red(menu.url),
        title=red(menu.title),
        page_text=red(menu.page_text),
        full_text=red(menu.full_text) if menu.full_text else menu.full_text,
        candidates=cands,
        by_operation={op: tuple(by_id[c.id] for c in cs) for op, cs in menu.by_operation.items()},
        tabs=tuple({k: (red(v) if isinstance(v, str) else v) for k, v in t.items()} for t in menu.tabs),
    )


@dataclass
class Delegation:
    """A bounded assignment System 2 handed to System 1 (docs/experiments/Q9.md)."""

    goal: str
    stop_condition: str
    allowed_operations: tuple[str, ...] = ()
    known_values: tuple[tuple[str, str], ...] = ()
    budget: int = 8
    started_step: int = 0
    steps_taken: int = 0
    escalations: int = 0
    status: str = "active"
    reason: str = ""

    def summary(self, url: str) -> str:
        return (
            f"Fast navigator finished the subgoal {self.goal!r}: {self.status} ({self.reason}) after "
            f"{self.steps_taken} step(s); now at {url}. Decide what to do next."
        )


class GuardOnly:
    """The guarded arm (docs/experiments/Q9.md): never decides, never calls Jev for a menu, but carries
    the verifier and secrets so System 2's done goes through the same verification and the gate as in
    the dual arm. Isolates what the guard contributes from what S1 contributes."""

    def __init__(self, verifier: Any = None, secrets: SecretStore | None = None):
        self.verifier = verifier
        self.secrets = secrets

    async def decide(self, agent: Any, state: Any) -> None:
        return None


class JevS1:
    def __init__(
        self,
        policy: JevPolicy,
        *,
        arbiter: Arbiter | None = None,
        text_source: TextSource | None = None,
        requirements: tuple[str, ...] = (),
        recent_window: int = 8,
        secrets: SecretStore | None = None,
        verifier: Any = None,
        escalation_streak: int = 3,
        s2_control_steps: int = 3,
        only_when_delegated: bool = False,
        subgoal_done_floor: float = 0.85,
    ):
        #: Q9 delegate arms: S1 decides only inside a Delegation; ordinary System 2 steps never call Jev.
        self.only_when_delegated = only_when_delegated
        self.subgoal_done_floor = subgoal_done_floor
        self.policy = policy
        self.arbiter: Arbiter = arbiter or AlwaysAct()
        #: Call economy (Q9 item 5): after ``escalation_streak`` consecutive escalations for the same
        #: reason class at the same URL, hand System 2 ``s2_control_steps`` steps without a menu call;
        #: a URL change ends the stretch early. 0 disables.
        self.escalation_streak = escalation_streak
        self.s2_control_steps = s2_control_steps
        self._s2_control: tuple[int, str] | None = None  # (until step, url the stretch started on)
        self.secrets = secrets
        self.requirements = requirements
        self.recent_window = recent_window
        self.verifier = verifier  # jevdual.verify.ArbiterHook (task D3); None means S1's own done stands
        if text_source is None:
            from jevdual.text import TextSource as _TextSource
            from jevdual.text import helper_from_env, placeholder_from_store

            helper = helper_from_env()
            text_source = _TextSource(
                helper=helper.compose if helper is not None else None,
                secret_placeholder=placeholder_from_store(secrets) if secrets is not None else None,
            ).compose
        self.text_source = text_source
        self.last_menu: Menu | None = None

    async def _delegated_step(self, agent: Any, delegation: Delegation, decision: Decision, menu: Menu, rec: S1Record, step: int) -> bool:
        """Inside a delegation: a done or a confident goal_done means "check the stop condition with
        observed support"; reached ends the delegation, otherwise a done escalates and the delegation
        stays. Returns True when this step must escalate, False to continue with the ordinary act path."""
        goal_done = decision.nouls.get("goal_done", 0.0)
        if decision.operation != "done" and goal_done < self.subgoal_done_floor:
            return False
        if self.verifier is not None and hasattr(self.verifier, "judge_subgoal"):
            met, reason = await self.verifier.judge_subgoal(agent, menu, delegation.goal, delegation.stop_condition)
            rec.verify = {"subgoal": delegation.goal, "met": met, "reason": reason}
        else:
            met, reason = goal_done >= self.subgoal_done_floor, f"goal_done={goal_done:.2f} (unverified)"
        if met:
            self._end_delegation(agent, delegation, "reached", reason, menu.url)
            rec.verdict = Verdict("escalate", f"delegation reached: {reason}")
            return True  # System 2 takes this step with the summary in context
        if decision.operation == "done":
            rec.verdict = Verdict("escalate", f"subgoal not yet met: {reason}")
            log.info("step %s: %s", step, rec.verdict.reason)
            return True
        return False  # goal_done was high but unsupported: keep acting

    def _end_delegation(self, agent: Any, delegation: Delegation, status: str, reason: str, url: str) -> None:
        delegation.status, delegation.reason = status, reason
        agent.delegation = None
        agent.__dict__.setdefault("delegations", []).append(delegation)
        log.info("delegation %r ended: %s (%s) after %s step(s)", delegation.goal, status, reason, delegation.steps_taken)
        mm = getattr(agent, "_message_manager", None)
        if mm is not None and hasattr(mm, "_add_context_message"):
            from browser_use.llm.messages import UserMessage

            mm._add_context_message(UserMessage(content=delegation.summary(url)))

    def _s2_control_reason(self, agent: Any, records: dict[int, S1Record], step: int, url: str) -> str | None:
        """None when S1 should be consulted; otherwise the reason this step is left to System 2."""
        if self.escalation_streak <= 0:
            return None
        if self._s2_control is not None:
            until, start_url = self._s2_control
            if step <= until and url == start_url:
                return f"s2_control: System 2 keeps control until step {until} (no menu call)"
            self._s2_control = None
        recent = [records[i] for i in range(step - self.escalation_streak, step) if i in records]
        if len(recent) < self.escalation_streak:
            return None
        reasons = {(r.verdict.reason.split(":", 1)[0].strip() if r.verdict else "") for r in recent}
        if len(reasons) != 1 or not all(r.verdict is not None and r.verdict.kind == "escalate" for r in recent):
            return None
        reason = reasons.pop()
        if reason in ("s2_control", "destructive", "verification accept", "act"):
            return None
        self._s2_control = (step + self.s2_control_steps - 1, url)
        return f"s2_control: {self.escalation_streak} consecutive escalations on {reason!r}; System 2 keeps control until step {self._s2_control[0]} (no menu call)"

    def _context(self, agent: DualProcessAgent) -> StepContext:
        lines = [h.model_output.memory for h in agent.history.history if h.model_output and h.model_output.memory]
        if self.secrets is not None:
            red = self.secrets.redactor()
            lines = [red(line) for line in lines]
        d: Delegation | None = getattr(agent, "delegation", None)
        return StepContext(
            task=agent.task,
            requirements=self.requirements,
            recent_actions=tuple(lines[-self.recent_window :]),
            step=agent.state.n_steps,
            secrets_names=self.secrets.names() if self.secrets is not None else (),
            subgoal=d.goal if d is not None else None,
            allowed_operations=d.allowed_operations if d is not None else (),
            known_values=d.known_values if d is not None else (),
            stop_condition=d.stop_condition if d is not None else None,
        )

    async def decide(self, agent: DualProcessAgent, state: BrowserStateSummary) -> Any | None:
        step = agent.state.n_steps
        records: dict[int, S1Record] = agent.__dict__.setdefault("s1_records", {})
        rec = S1Record(step=step, decision=None, verdict=None)
        records[step] = rec

        delegation: Delegation | None = getattr(agent, "delegation", None)
        if self.only_when_delegated and delegation is None:
            rec.verdict = Verdict("escalate", "idle: no delegation from System 2 (no menu call)")
            return None
        if delegation is not None and delegation.steps_taken >= delegation.budget:
            self._end_delegation(agent, delegation, "budget_exhausted", f"{delegation.budget} step budget used", getattr(state, "url", "") or "")
            rec.verdict = Verdict("escalate", "delegation ended: budget_exhausted")
            return None

        skip = None if delegation is not None else self._s2_control_reason(agent, records, step, getattr(state, "url", "") or "")
        if skip is not None:
            rec.verdict = Verdict("escalate", skip)
            log.info("step %s: %s", step, skip)
            return None

        t0 = time.perf_counter()
        menu = build_menu(state)
        live_url = menu.url
        if self.secrets is not None:
            # Nothing model-facing may carry a secret value, however it got onto the page.
            menu = redact_menu(menu, self.secrets.redactor())
        rec.menu_ms = (time.perf_counter() - t0) * 1000
        rec.menu_omitted = dict(menu.omitted)
        self.last_menu = menu
        ctx = self._context(agent)

        try:
            decision = await self.policy.decide(menu, ctx)
            if decision.two_stage and decision.pending_group:
                decision = await self.policy.decide_target(menu, ctx, decision.operation, decision.pending_group)
        except PolicyError as exc:
            rec.error = f"policy: {exc}"
            rec.verdict = Verdict("escalate", f"policy error: {exc}")
            log.warning("step %s: %s; escalating", step, rec.error)
            return None
        rec.jev_ms = decision.latency_ms
        rec.decision = decision

        done_text: str | None = None
        if delegation is not None and await self._delegated_step(agent, delegation, decision, menu, rec, step):
            return None
        if delegation is None and decision.operation == "done" and self.verifier is not None and getattr(self.verifier, "answer_expected", False):
            # S1 cannot compose an answer, so its done on an answer task is refused every time; skip the
            # verification call (14 of 77 S1 vetoes on the post-ledger live run were exactly this).
            rec.verdict = Verdict("escalate", "done without an answer on an answer task; not verified")
            log.info("step %s: done vetoed without a call, %s", step, rec.verdict.reason)
            return None
        if delegation is None and decision.operation == "done" and self.verifier is not None:
            band, reason = await self.verifier.judge_done(agent, menu)
            last = getattr(self.verifier, "last", None)
            rec.verify = last.to_trace() if last is not None and hasattr(last, "to_trace") else {"band": band, "reason": reason}
            if band != "accept":
                rec.verdict = Verdict("escalate", f"verification {band}: {reason}")
                log.info("step %s: done vetoed, %s", step, rec.verdict.reason)
                return None
            done_text = getattr(last, "supported_answer", None) or None
            verdict = Verdict("act", f"verification accept: {reason}")
        else:
            verdict = self.arbiter.judge(decision, menu, ctx, agent)
        if verdict.kind == "retry_alternate" and decision.alternates:
            decision = dataclasses.replace(decision, target=decision.alternates[0], alternates=decision.alternates[1:])
            rec.decision = decision
            verdict = Verdict("act", f"retry_alternate: {verdict.reason}")
        rec.verdict = verdict
        if verdict.kind in ("escalate", "confirm"):
            log.info("step %s: %s (%s)", step, verdict.kind, verdict.reason)
            if delegation is not None:
                head = verdict.reason.split(":", 1)[0].strip()
                delegation.escalations += 1
                if head in ("stuck", "blocked", "no_effect", "repeated_target") or verdict.kind == "confirm":
                    self._end_delegation(agent, delegation, head if verdict.kind != "confirm" else "paused_before_action", verdict.reason, menu.url)
            return None

        text = None
        if decision.operation in ("type", "select") and decision.target is not None:
            target = menu.candidate(decision.target)
            if target is not None:
                text = _known_value_for(target, delegation.known_values) if delegation is not None else None
                if text is None:
                    text = self.text_source(agent.task, target, menu)
                if inspect.isawaitable(text):
                    text = await text
            if text is None:
                rec.verdict = Verdict("escalate", f"{decision.operation} needs composed text")
                return None
            if isinstance(text, str) and text.startswith("<secret>") and self.secrets is not None:
                name = text[len("<secret>") : text.index("</secret>")] if "</secret>" in text else ""
                if not name or not self.secrets.allowed_for(live_url, name):
                    rec.verdict = Verdict("escalate", f"secret {name!r} is not allowed on {live_url}")
                    log.warning("step %s: refusing to type secret %r on %s", step, name, live_url)
                    return None

        try:
            bridged: Bridged = Bridge(agent.ActionModel, agent.AgentOutput).build(decision, menu, step=step, text=text, done_text=done_text)
            assert_fresh(agent, state, menu, decision)
        except BridgeError as exc:
            rec.error = f"bridge/{exc.reason}: {exc}"
            rec.verdict = Verdict("escalate", rec.error)
            log.warning("step %s: %s; escalating", step, rec.error)
            return None
        rec.proposed = bridged.proposed
        if delegation is not None:
            delegation.steps_taken += 1
        return bridged.output
