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
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, Protocol

from jevdual.bridge import Bridge, Bridged, BridgeError, assert_fresh
from jevdual.menu import Candidate, Menu, build_menu
from jevdual.policy import Decision, JevPolicy, PolicyError, StepContext
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


TextSource = Callable[[str, Candidate, Menu], str | None]


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
    menu_omitted: dict[str, int] = field(default_factory=dict)
    error: str | None = None
    menu_ms: float = 0.0
    jev_ms: float = 0.0


class JevS1:
    def __init__(
        self,
        policy: JevPolicy,
        *,
        arbiter: Arbiter | None = None,
        text_source: TextSource = literal_text_source,
        requirements: tuple[str, ...] = (),
        recent_window: int = 8,
    ):
        self.policy = policy
        self.arbiter: Arbiter = arbiter or AlwaysAct()
        self.text_source = text_source
        self.requirements = requirements
        self.recent_window = recent_window
        self.last_menu: Menu | None = None

    def _context(self, agent: DualProcessAgent) -> StepContext:
        lines = [h.model_output.memory for h in agent.history.history if h.model_output and h.model_output.memory]
        return StepContext(
            task=agent.task,
            requirements=self.requirements,
            recent_actions=tuple(lines[-self.recent_window :]),
            step=agent.state.n_steps,
        )

    async def decide(self, agent: DualProcessAgent, state: BrowserStateSummary) -> Any | None:
        step = agent.state.n_steps
        records: dict[int, S1Record] = agent.__dict__.setdefault("s1_records", {})
        rec = S1Record(step=step, decision=None, verdict=None)
        records[step] = rec

        t0 = time.perf_counter()
        menu = build_menu(state)
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

        verdict = self.arbiter.judge(decision, menu, ctx, agent)
        if verdict.kind == "retry_alternate" and decision.alternates:
            decision = dataclasses.replace(decision, target=decision.alternates[0], alternates=decision.alternates[1:])
            rec.decision = decision
            verdict = Verdict("act", f"retry_alternate: {verdict.reason}")
        rec.verdict = verdict
        if verdict.kind in ("escalate", "confirm"):
            log.info("step %s: %s (%s)", step, verdict.kind, verdict.reason)
            return None

        text = None
        if decision.operation in ("type", "select") and decision.target is not None:
            target = menu.candidate(decision.target)
            if target is not None:
                text = self.text_source(agent.task, target, menu)
            if text is None:
                rec.verdict = Verdict("escalate", f"{decision.operation} needs composed text")
                return None

        try:
            bridged: Bridged = Bridge(agent.ActionModel, agent.AgentOutput).build(decision, menu, step=step, text=text)
            assert_fresh(agent, state, menu, decision)
        except BridgeError as exc:
            rec.error = f"bridge/{exc.reason}: {exc}"
            rec.verdict = Verdict("escalate", rec.error)
            log.warning("step %s: %s; escalating", step, rec.error)
            return None
        rec.proposed = bridged.proposed
        return bridged.output
