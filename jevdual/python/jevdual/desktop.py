"""NativeAgent: the dual-process loop on a native window through Cua Driver.

One step is: observe (with the reobserve rule for partial snapshots) -> redact -> System 1 decides
over the menu -> a ``done`` goes to the verifier, anything else to the arbiter -> act through
:class:`jevdual.native.NativeBridge` -> record. An escalation goes to System 2 when one is
configured (``desktop_s2.NativeS2``); without one the run ends there, which is the ``s1_only`` arm.

Reused unchanged: ``JevPolicy`` and its prompts, ``Arbiter`` and ``arbiter.toml``, ``TextSource``
(literal, secret placeholder, helper), ``ArbiterHook.judge_done``, the schema-2 trace, the
secret redactor. Nothing here subclasses browser-use.

Records are written in the browser trace's vocabulary so ``evals.*`` reads native runs without
change: executed actions are named ``click`` / ``input`` / ``send_keys`` / ``scroll`` / ``done``
with an ``index`` parameter, and the Driver's own effect words ride along in the params.
"""

from __future__ import annotations

import dataclasses
import inspect
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from jevdual.menu import Candidate, Menu
from jevdual.native import NativeBridge, NativeBridgeError, NativeEffect, NativeMenu
from jevdual.policy import Decision, PolicyError, StepContext
from jevdual.s1 import AlwaysAct, Verdict, redact_menu
from jevdual.trace import ActionRecord, Cost, MenuEntry, StepRecord, Timings, TraceWriter

log = logging.getLogger("jevdual.desktop")

Status = Literal["done", "escalated", "paused", "blocked", "budget_exhausted", "error"]

#: action names the eval tooling already knows, by operation
_ACTION_NAMES = {
    "click": "click",
    "type": "input",
    "select": "select_dropdown",
    "enter": "send_keys",
    "scroll": "scroll",
    "hover": "hover",
}
REOBSERVE_MAX = 2


@dataclass
class StepOutcome:
    step: int
    system: Literal["s1", "s2"]
    menu: NativeMenu | None
    decision: Decision | None = None
    verdict: Verdict | None = None
    executed: list[ActionRecord] = field(default_factory=list)
    effect: NativeEffect | None = None
    verify: dict[str, Any] | None = None
    error: str | None = None
    memory_line: str | None = None
    is_done: bool = False
    answer: str | None = None
    menu_ms: float = 0.0
    jev_ms: float = 0.0
    llm_ms: float = 0.0
    exec_ms: float = 0.0
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0


@dataclass
class NativeRun:
    status: Status
    reason: str
    steps: list[StepOutcome]
    answer: str | None = None
    final_menu: NativeMenu | None = None

    @property
    def s1_steps(self) -> int:
        return sum(1 for s in self.steps if s.system == "s1" and s.executed)

    @property
    def s2_steps(self) -> int:
        return sum(1 for s in self.steps if s.system == "s2")

    @property
    def is_done(self) -> bool:
        return self.status == "done"


class SystemTwo:
    """What ``desktop_s2.NativeS2`` implements. ``step`` proposes and executes one bounded action
    (or ``done``) and returns the outcome fields it filled in; the agent records them."""

    async def step(self, agent: NativeAgent, nm: NativeMenu, reason: str, out: StepOutcome) -> None: ...


class NativeAgent:
    def __init__(
        self,
        bridge: NativeBridge,
        policy: Any,
        *,
        task: str,
        requirements: tuple[str, ...] = (),
        arbiter: Any = None,
        verifier: Any = None,
        text_source: Callable[[str, Candidate, Menu], Any] | None = None,
        secrets: Any = None,
        s2: SystemTwo | None = None,
        trace: TraceWriter | None = None,
        run_id: str = "native",
        max_steps: int = 25,
        recent_window: int = 8,
        answer_expected: bool = False,
        gate: Callable[[NativeMenu, Candidate], Awaitable[str | None] | str | None] | None = None,
        s1_enabled: bool = True,
    ):
        self.bridge = bridge
        self.policy = policy
        self.task = task
        self.requirements = requirements
        self.arbiter = arbiter or AlwaysAct()
        self.verifier = verifier
        self.secrets = secrets
        self.s2 = s2
        self.trace = trace
        self.run_id = run_id
        self.max_steps = max_steps
        self.recent_window = recent_window
        self.answer_expected = answer_expected
        #: returns a reason string when the target must not be clicked without confirmation
        self.gate = gate
        #: False is the guarded arm: System 2 decides every step behind the same gate, System 1 is never asked
        self.s1_enabled = s1_enabled
        if text_source is None:
            from jevdual.text import TextSource, helper_from_env, placeholder_from_store

            helper = helper_from_env()
            text_source = TextSource(
                helper=helper.compose if helper is not None else None,
                secret_placeholder=placeholder_from_store(secrets) if secrets is not None else None,
            ).compose
        self.text_source = text_source
        #: browser-compatible bookkeeping the arbiter and verifier read
        self.step_systems: dict[int, str] = {}
        self.memory: list[str] = []
        self.steps: list[StepOutcome] = []
        self.jev_calls = 0
        self.s1_policy = _PolicyShim(secrets)  # ArbiterHook reads agent.s1_policy.secrets

    # ---- observation -------------------------------------------------------------------

    async def observe(self) -> tuple[NativeMenu, float]:
        """Observe; a truncated or degraded snapshot is taken again up to ``REOBSERVE_MAX`` times."""
        t0 = time.perf_counter()
        nm = await self.bridge.observe()
        tries = 0
        while (nm.truncated or nm.degraded) and tries < REOBSERVE_MAX:
            tries += 1
            log.info(
                "snapshot %s partial (truncated=%s degraded=%s); reobserving",
                nm.snapshot_id,
                nm.truncated,
                nm.degraded,
            )
            nm = await self.bridge.observe(max_elements=4000)
        if self.secrets is not None:
            nm = dataclasses.replace(nm, menu=redact_menu(nm.menu, self.secrets.redactor()))
        return nm, (time.perf_counter() - t0) * 1000

    def context(self, step: int) -> StepContext:
        lines = self.memory[-self.recent_window :]
        if self.secrets is not None:
            red = self.secrets.redactor()
            lines = [red(x) for x in lines]
        return StepContext(
            task=self.task,
            requirements=self.requirements,
            recent_actions=tuple(lines),
            step=step,
            secrets_names=self.secrets.names() if self.secrets is not None else (),
        )

    # ---- one step ----------------------------------------------------------------------

    async def _decide(self, nm: NativeMenu, ctx: StepContext) -> Decision:
        decision = await self.policy.decide(nm.menu, ctx)
        self.jev_calls += 1
        if decision.two_stage and decision.pending_group:
            second = await self.policy.decide_target(nm.menu, ctx, decision.operation, decision.pending_group)
            self.jev_calls += 1
            decision = dataclasses.replace(
                decision,
                target=second.target,
                target_confidence=second.target_confidence,
                target_probabilities=second.target_probabilities,
                alternates=second.alternates,
                two_stage=False,
                pending_group=(),
                request_tokens=(decision.request_tokens or 0) + (second.request_tokens or 0),
                latency_ms=decision.latency_ms + second.latency_ms,
                raw=second.raw,
            )
        return decision

    async def _text_for(self, target: Candidate, nm: NativeMenu) -> str | None:
        text = self.text_source(self.task, target, nm.menu)
        if inspect.isawaitable(text):
            text = await text
        if isinstance(text, str) and text.startswith("<secret>") and self.secrets is not None:
            name = text[len("<secret>") : text.index("</secret>")] if "</secret>" in text else ""
            if not name or not self.secrets.allowed_for(nm.menu.url, name):
                raise NativeBridgeError("secret", f"secret {name!r} is not allowed on {nm.menu.url}")
            value = dict(self.secrets.values()).get(name)
            if value is None:
                raise NativeBridgeError("secret", f"secret {name!r} has no value")
            return value
        return text

    def trajectory(self, max_steps: int = 12) -> list[dict[str, Any]]:
        """Per-step lines for the verifier, in the shape ``ledger.trajectory_from_agent`` produces."""
        red = self.secrets.redactor() if self.secrets is not None else (lambda s: s)
        out = []
        for o in self.steps:
            if not o.executed:
                continue
            entry: dict[str, Any] = {
                "step": o.step,
                "url": o.menu.menu.url if o.menu is not None else "",
                "actions": [red(f"{a.name}({a.params.get('index', '')})") for a in o.executed],
            }
            if o.memory_line or self.memory:
                entry["note"] = red(o.memory_line or "")[:200] if o.memory_line else ""
            if o.error:
                entry["error"] = red(o.error)[:120]
            out.append({k: v for k, v in entry.items() if v != ""})
        return out[-max_steps:]

    async def _judge_done(self, nm: NativeMenu, answer: str | None = None) -> tuple[str, str]:
        """The verifier's accept band for a done on this menu. An ``ArbiterHook`` is driven through
        its ``Verifier`` with our own trajectory (its browser-history helper reads browser-use
        shapes); anything else is asked through ``judge_done``."""
        inner = getattr(self.verifier, "verifier", None)
        if inner is not None and hasattr(inner, "verify"):
            verdict = await inner.verify(
                self.task,
                self.requirements,
                nm.menu,
                answer,
                answer_expected=self.answer_expected,
                trajectory=self.trajectory(),
                ledger=getattr(self.verifier, "ledger", None),
            )
            self.verifier.last = verdict
            return verdict.band, verdict.reason
        return await self.verifier.judge_done(self, nm.menu, answer)

    async def s1_step(self, step: int, nm: NativeMenu, out: StepOutcome) -> Verdict:
        """System 1 decides and, when the arbiter allows, acts. Returns the verdict; ``out`` carries
        the decision, verification, executed action and effect."""
        ctx = self.context(step)
        try:
            decision = await self._decide(nm, ctx)
        except PolicyError as exc:
            out.error = f"policy: {exc}"
            out.verdict = Verdict("escalate", f"policy error: {exc}")
            return out.verdict
        out.decision = decision
        out.jev_ms = decision.latency_ms
        target = nm.menu.candidate(decision.target) if decision.target is not None else None

        if decision.operation == "done":
            if self.answer_expected:
                out.verdict = Verdict("escalate", "done without an answer on an answer task; not verified")
                return out.verdict
            if self.verifier is None:
                out.verdict = self.arbiter.judge(decision, nm.menu, ctx, self)
                return out.verdict
            band, reason = await self._judge_done(nm)
            self.jev_calls += 1
            last = getattr(self.verifier, "last", None)
            out.verify = (
                last.to_trace()
                if last is not None and hasattr(last, "to_trace")
                else {"band": band, "reason": reason}
            )
            if band != "accept":
                out.verdict = Verdict("escalate", f"verification {band}: {reason}")
                return out.verdict
            out.verdict = Verdict("act", f"verification accept: {reason}")
            out.is_done = True
            out.answer = getattr(last, "supported_answer", None) or None
            out.executed = [ActionRecord(name="done", params={"text": out.answer or "", "success": True})]
            return out.verdict

        verdict = self.arbiter.judge(decision, nm.menu, ctx, self)
        if verdict.kind == "retry_alternate" and decision.alternates:
            decision = dataclasses.replace(
                decision, target=decision.alternates[0], alternates=decision.alternates[1:]
            )
            out.decision = decision
            target = nm.menu.candidate(decision.target) if decision.target is not None else None
            verdict = Verdict("act", f"retry_alternate: {verdict.reason}")
        out.verdict = verdict
        if verdict.kind != "act":
            return verdict
        if not decision.targeted or target is None:
            out.verdict = Verdict(
                "escalate", f"{decision.operation} has no native dispatch; System 2 decides"
            )
            return out.verdict

        text: str | None = None
        if decision.operation in ("type", "select"):
            try:
                text = await self._text_for(target, nm)
            except NativeBridgeError as exc:
                out.verdict = Verdict("escalate", f"{exc.reason}: {exc}")
                return out.verdict
            if text is None:
                out.verdict = Verdict("escalate", f"{decision.operation} needs composed text")
                return out.verdict
        if self.gate is not None and decision.operation == "click":
            hit = self.gate(nm, target)
            if inspect.isawaitable(hit):
                hit = await hit
            if hit:
                out.verdict = Verdict("confirm", f"destructive: {hit}")
                return out.verdict
        await self.execute(nm, decision.operation, target, text, out)
        return out.verdict

    async def execute(
        self, nm: NativeMenu, operation: str, target: Candidate, text: str | None, out: StepOutcome
    ) -> NativeEffect | None:
        """Dispatch one operation and record it in the browser vocabulary. Never raises for a
        Driver refusal; a bridge error (stale, unsupported) is recorded as ``result_error``."""
        t0 = time.perf_counter()
        params: dict[str, Any] = {"index": target.id, "label": target.label[:60]}
        if operation == "type":
            params["text"] = text if self.secrets is None else self.secrets.redactor()(text or "")
        if operation == "enter":
            params = {"keys": "Enter", "index": target.id}
        if operation == "scroll":
            params = {"down": True, "pages": 1.0, "index": target.id}
        try:
            effect = await self.bridge.act(nm, operation, target.id, text)
        except NativeBridgeError as exc:
            out.error = f"bridge/{exc.reason}: {exc}"
            out.exec_ms = (time.perf_counter() - t0) * 1000
            out.executed = [ActionRecord(name=_ACTION_NAMES.get(operation, operation), params=params)]
            self.memory.append(
                f"step {out.step}: {operation} [{target.id}] {target.label[:60]!r} -> not dispatched ({exc.reason})"
            )
            return None
        out.exec_ms = (time.perf_counter() - t0) * 1000
        out.effect = effect
        params.update({"effect": effect.effect, "route": effect.route})
        out.executed = [ActionRecord(name=_ACTION_NAMES.get(operation, operation), params=params)]
        if effect.effect == "refused":
            out.error = f"driver refused: {effect.error_code or ''} {effect.summary[:120]}".strip()
        self.memory.append(
            f"step {out.step}: {operation} [{target.id}] {target.label[:60]!r} -> {effect.effect}"
            + (f" ({effect.error_code})" if effect.error_code else "")
        )
        return effect

    # ---- the run -----------------------------------------------------------------------

    async def run(self) -> NativeRun:
        final: NativeMenu | None = None
        for step in range(1, self.max_steps + 1):
            try:
                nm, menu_ms = await self.observe()
            except Exception as exc:  # noqa: BLE001 - a lost window ends the run as an error row, not a crash
                log.warning("observation failed at step %s: %s", step, exc)
                return NativeRun(
                    "error",
                    f"observation failed: {type(exc).__name__}: {str(exc)[:160]}",
                    self.steps,
                    None,
                    final,
                )
            final = nm
            out = StepOutcome(step=step, system="s1", menu=nm, menu_ms=menu_ms)
            self.steps.append(out)
            if not self.s1_enabled:
                if self.s2 is None:
                    return NativeRun("error", "no System 1 and no System 2", self.steps, None, nm)
                verdict = Verdict("escalate", "guarded arm: System 2 decides every step")
                out.verdict = verdict
            else:
                verdict = await self.s1_step(step, nm, out)
            self.step_systems[step] = "s1"
            if out.is_done:
                self._write(out, nm)
                return NativeRun("done", verdict.reason, self.steps, out.answer, nm)
            if verdict.kind == "act":
                self._write(out, nm)
                continue
            if verdict.kind == "confirm" and self.s2 is None:
                self._write(out, nm)
                return NativeRun("paused", verdict.reason, self.steps, None, nm)
            if self.s2 is None:
                self._write(out, nm)
                if out.decision is not None and out.decision.operation == "blocked":
                    return NativeRun("blocked", verdict.reason, self.steps, None, nm)
                return NativeRun("escalated", verdict.reason, self.steps, None, nm)
            # System 2 takes this step with S1's record in view
            out.system = "s2"
            self.step_systems[step] = "s2"
            t0 = time.perf_counter()
            await self.s2.step(self, nm, verdict.reason, out)
            out.llm_ms = (time.perf_counter() - t0) * 1000
            self._write(out, nm)
            if out.is_done:
                return NativeRun("done", "System 2 done", self.steps, out.answer, nm)
            if out.verdict is not None and out.verdict.kind == "confirm":
                return NativeRun("paused", out.verdict.reason, self.steps, None, nm)
            if out.error == "s2 fatal: blocked":
                return NativeRun(
                    "blocked", out.verdict.reason if out.verdict else out.error, self.steps, None, nm
                )
            if out.error and out.error.startswith("s2 fatal"):
                return NativeRun("error", out.error, self.steps, None, nm)
        return NativeRun("budget_exhausted", f"{self.max_steps} steps", self.steps, None, final)

    def _write(self, out: StepOutcome, nm: NativeMenu) -> None:
        if self.trace is None:
            return
        menu = [
            MenuEntry(
                id=c.id,
                label=c.label[:120],
                role=c.role,
                section=c.section,
                value=(c.value[:80] if c.value else None),
                input_type=c.input_type,
                offscreen=c.offscreen,
            )
            for c in nm.menu.candidates
        ]
        omitted = sum(nm.menu.omitted.values())
        self.trace.write(
            StepRecord(
                run_id=self.run_id,
                step=out.step,
                system=out.system,  # type: ignore[arg-type]
                url_before=nm.menu.url,
                url_after=nm.menu.url,
                decision=out.decision.to_trace(omitted) if out.decision is not None else None,
                arbiter_reason=out.verdict.reason if out.verdict is not None else None,
                executed=list(out.executed),
                result_error=out.error,
                is_done=out.is_done,
                effect=(out.effect.summary[:200] if out.effect is not None and out.effect.summary else None),
                memory_line=self.memory[-1] if self.memory else None,
                menu=menu,
                verify=out.verify,
                timings=Timings(
                    dom_ms=out.menu_ms,
                    jev_ms=out.jev_ms or None,
                    llm_ms=out.llm_ms or None,
                    exec_ms=out.exec_ms or None,
                ),
                cost=Cost(llm_input_tokens=out.llm_input_tokens, llm_output_tokens=out.llm_output_tokens),
            )
        )


@dataclass
class _PolicyShim:
    secrets: Any = None


def keyword_gate(
    policy: Any = None, *, authorized_actions: tuple[str, ...] = (), authorize_all: bool = False
) -> Callable[[NativeMenu, Candidate], str | None]:
    """The keyword fast path of the destructive gate for System 1 clicks (System 1 decisions are not
    judged twice: its own ``destructive`` noul already went through the arbiter)."""
    from jevdual.arbiter import ArbiterPolicy, destructive_match

    pol = policy or ArbiterPolicy.from_toml()
    allowed = tuple(a.casefold() for a in authorized_actions)

    def gate(nm: NativeMenu, target: Candidate) -> str | None:
        if authorize_all or any(a in target.label.casefold() for a in allowed):
            return None
        context = " ".join(x for x in (target.section or "", nm.menu.title) if x)
        hit = destructive_match(target.label, context, pol)
        return f"keyword {hit!r}" if hit else None

    return gate
