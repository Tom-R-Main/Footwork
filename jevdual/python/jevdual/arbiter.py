"""Arbiter: the code-owned policy that decides whether System 1 acts.

Jev supplies calibrated probabilities; this module supplies the thresholds and
the rules. Every rule names itself and its numbers in the ``Verdict.reason`` so
the trace explains each escalation, and ``stats`` counts how often each rule
fired for the eval report. Thresholds live in ``arbiter.toml`` (loaded with
``Arbiter.from_toml``) so tuning in E1 changes data, not code.

Verdicts: ``act`` dispatches the decision; ``escalate`` hands the step to
System 2; ``confirm`` stops before an irreversible action; ``retry_alternate``
tells ``JevS1`` to act on the next-best target instead of paying for another
Jev call.
"""

from __future__ import annotations

import re
import tomllib
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

from jevdual.effects import Effect, diff
from jevdual.menu import Menu
from jevdual.policy import Decision, StepContext
from jevdual.s1 import Verdict

DEFAULT_POLICY_PATH = Path(__file__).with_name("arbiter.toml")

#: Rules in evaluation order; ``stats`` uses these names.
RULES: tuple[str, ...] = (
    "done_requires_verification",
    "blocked",
    "back_on_first_step",
    "goal_done",
    "destructive",
    "needs_reasoning",
    "stuck",
    "head_disagreement",
    "repeated_target",
    "s1_streak",
    "no_effect",
    "operation_confidence",
    "retry_alternate",
    "target_confidence",
    "act",
)


@dataclass(frozen=True)
class ArbiterPolicy:
    act_operation_confidence: float = 0.55
    act_target_confidence: float = 0.45
    #: inside a bounded assignment from System 2 the driver has already bounded the risk, so a flatter
    #: operation head may act (a wrong harmless step costs one step, a handback costs the assignment)
    delegated_operation_confidence: float = 0.45
    goal_done_escalate: float = 0.85
    stuck_escalate: float = 0.85
    stuck_min_step: int = 3
    needs_reasoning_escalate: float = 0.6
    login_required_escalate: float = 0.6
    bot_check_escalate: float = 0.6
    s1_streak_max: int = 8
    no_effect_steps: int = 2
    repeat_target_count: int = 3
    repeat_target_window: int = 6
    destructive_confirm: float = 0.5
    destructive_keywords: tuple[str, ...] = (
        "delete",
        "remove",
        "pay",
        "purchase",
        "buy now",
        "place order",
        "send",
        "submit payment",
        "confirm order",
        "unsubscribe",
        "deactivate",
        "删除",
        "支付",
        "购买",
        "确认订单",
        "发送",
    )
    retry_alternate_margin: float = 0.15
    retry_alternate_lookback: int = 3

    @classmethod
    def from_toml(cls, path: str | Path | None = None) -> ArbiterPolicy:
        data = tomllib.loads(Path(path or DEFAULT_POLICY_PATH).read_text(encoding="utf-8"))
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"unknown arbiter policy keys: {sorted(unknown)}")
        if "destructive_keywords" in data:
            data["destructive_keywords"] = tuple(data["destructive_keywords"])
        return cls(**data)


_LATIN = re.compile(r"^[A-Za-z0-9 _-]+$")


def _keyword_pattern(keyword: str) -> re.Pattern[str] | None:
    """Word-boundary regex for Latin keywords; ``None`` means substring match (CJK etc.)."""
    kw = keyword.strip()
    if not kw or not _LATIN.match(kw):
        return None
    return re.compile(r"(?<![A-Za-z0-9])" + re.escape(kw) + r"(?![A-Za-z0-9])", re.IGNORECASE)


def match_destructive_keyword(text: str, keywords: tuple[str, ...]) -> str | None:
    """Return the first keyword that matches ``text``: word-bounded for Latin, substring otherwise."""
    if not text:
        return None
    lowered = text.casefold()
    for kw in keywords:
        pat = _keyword_pattern(kw)
        if pat is None:
            if kw.strip() and kw.strip().casefold() in lowered:
                return kw
        elif pat.search(text):
            return kw
    return None


OnDone = Callable[[Decision, Menu, StepContext, Any], Verdict]


@dataclass
class _StepLog:
    step: int
    url: str
    operation: str
    target: int | None
    label: str | None
    verdict: Verdict
    effect: str | None


@dataclass
class Arbiter:
    policy: ArbiterPolicy = field(default_factory=ArbiterPolicy)
    #: Task D3 plugs verification in here; until then "done" escalates.
    on_done: OnDone | None = None
    stats: Counter[str] = field(default_factory=Counter)
    _prev_menu: Menu | None = field(default=None, repr=False)
    _last_effect: Effect | None = field(default=None, repr=False)
    _no_effect_run: int = 0
    _acted: list[tuple[int, str, int | None]] = field(default_factory=list, repr=False)
    _log: dict[int, _StepLog] = field(default_factory=dict, repr=False)

    @classmethod
    def from_toml(cls, path: str | Path | None = None, *, on_done: OnDone | None = None) -> Arbiter:
        return cls(policy=ArbiterPolicy.from_toml(path), on_done=on_done)

    # ---- helpers -------------------------------------------------------------

    def _observe(self, menu: Menu) -> Effect | None:
        """Track visible change between consecutive judged menus."""
        effect = diff(self._prev_menu, menu) if self._prev_menu is not None else None
        if effect is not None:
            self._no_effect_run = self._no_effect_run + 1 if effect.no_effect else 0
        self._prev_menu = menu
        self._last_effect = effect
        return effect

    @staticmethod
    def _s1_streak(agent: Any, step: int) -> int:
        systems: dict[int, str] = getattr(agent, "step_systems", {}) or {}
        n = 0
        s = step - 1
        while s >= 1 and systems.get(s) == "s1":
            n += 1
            s -= 1
        return n

    def _acted_recently(self, url: str, target: int | None, step: int, window: int) -> int:
        return sum(1 for s, u, t in self._acted if s > step - window and u == url and t == target)

    def _rule(self, name: str, kind: str, reason: str) -> Verdict:
        self.stats[name] += 1
        return Verdict(kind, f"{name}: {reason}")  # type: ignore[arg-type]

    # ---- the ruling ------------------------------------------------------------

    def judge(self, decision: Decision, menu: Menu, ctx: StepContext, agent: Any) -> Verdict:
        p = self.policy
        step = ctx.step
        nouls = decision.nouls
        effect = self._observe(menu)
        target = menu.candidate(decision.target) if decision.target is not None else None
        label = target.label if target is not None else None

        verdict = self._judge(decision, menu, ctx, agent, target_label=label, step=step, nouls=nouls, p=p)
        if verdict.kind in ("act", "retry_alternate"):
            acted_target = decision.target
            if verdict.kind == "retry_alternate" and decision.alternates:
                acted_target = decision.alternates[0]
            self._acted.append((step, menu.url, acted_target))
        self._log[step] = _StepLog(
            step, menu.url, decision.operation, decision.target, label, verdict, effect.summary if effect else None
        )
        return verdict

    def _judge(
        self,
        decision: Decision,
        menu: Menu,
        ctx: StepContext,
        agent: Any,
        *,
        target_label: str | None,
        step: int,
        nouls: dict[str, float],
        p: ArbiterPolicy,
    ) -> Verdict:
        op = decision.operation
        goal_done = nouls.get("goal_done", 0.0)
        stuck = nouls.get("stuck", 0.0)
        destructive = nouls.get("destructive", 0.0)
        needs_reasoning = nouls.get("needs_reasoning", 0.0)
        login = nouls.get("login_required", 0.0)
        bot = nouls.get("bot_check", 0.0)

        if op == "done":
            if self.on_done is not None:
                self.stats["done_requires_verification"] += 1
                return self.on_done(decision, menu, ctx, agent)
            return self._rule("done_requires_verification", "escalate", f"done requires verification (goal_done {goal_done:.2f})")

        if op == "blocked":
            if login >= p.login_required_escalate:
                return self._rule("blocked", "escalate", f"login_required {login:.2f} >= {p.login_required_escalate}")
            if bot >= p.bot_check_escalate:
                return self._rule("blocked", "escalate", f"bot_check {bot:.2f} >= {p.bot_check_escalate}")
            return self._rule("blocked", "escalate", "no offered operation can make progress")

        if op == "back" and step <= 1:
            return self._rule("back_on_first_step", "escalate", "back on first step")

        if goal_done >= p.goal_done_escalate:
            return self._rule("goal_done", "escalate", f"goal_done {goal_done:.2f} >= {p.goal_done_escalate}")

        # A task that authorises irreversible actions (order placed, form sent) turns the confirm rules
        # off here as it does at the agent-level gate; five authorised form fills were paused at zero
        # steps by the destructive noul on 2026-09-22 before this.
        authorized = bool(getattr(agent, "authorized_destructive", False))
        if not authorized and destructive >= p.destructive_confirm:
            return self._rule("destructive", "confirm", f"destructive {destructive:.2f} >= {p.destructive_confirm}")
        if not authorized and target_label is not None:
            hit = match_destructive_keyword(target_label, p.destructive_keywords)
            if hit is not None:
                return self._rule("destructive", "confirm", f"keyword {hit!r} in target {target_label!r}")

        if needs_reasoning >= p.needs_reasoning_escalate:
            return self._rule("needs_reasoning", "escalate", f"needs_reasoning {needs_reasoning:.2f} >= {p.needs_reasoning_escalate}")

        if step >= p.stuck_min_step and stuck >= p.stuck_escalate:
            return self._rule("stuck", "escalate", f"stuck {stuck:.2f} >= {p.stuck_escalate} at step {step}")

        if decision.targeted and (decision.target is None or not decision.target_probabilities):
            return self._rule("head_disagreement", "escalate", f"operation {op!r} chosen but no target head answer")

        if decision.targeted:
            hits = self._acted_recently(menu.url, decision.target, step, p.repeat_target_window)
            if hits >= p.repeat_target_count:
                return self._rule(
                    "repeated_target",
                    "escalate",
                    f"target {decision.target} acted on {hits} times in last {p.repeat_target_window} steps at {menu.url}",
                )

        streak = self._s1_streak(agent, step)
        if streak >= p.s1_streak_max:
            return self._rule("s1_streak", "escalate", f"{streak} consecutive S1 steps >= {p.s1_streak_max}")

        if self._no_effect_run >= p.no_effect_steps:
            return self._rule("no_effect", "escalate", f"{self._no_effect_run} consecutive steps with no visible change")

        op_floor = p.delegated_operation_confidence if getattr(agent, "delegation", None) is not None else p.act_operation_confidence
        if decision.operation_confidence < op_floor:
            return self._rule(
                "operation_confidence",
                "escalate",
                f"operation confidence {decision.operation_confidence:.2f} < {op_floor}",
            )

        if decision.targeted:
            tconf = decision.target_confidence if decision.target_confidence is not None else 0.0
            if tconf < p.act_target_confidence:
                alt = decision.alternates[0] if decision.alternates else None
                if alt is not None:
                    chosen_p = decision.target_probabilities.get(decision.target, 0.0)  # type: ignore[arg-type]
                    alt_p = decision.target_probabilities.get(alt, 0.0)
                    tried = self._acted_recently(menu.url, alt, step, p.retry_alternate_lookback)
                    if chosen_p - alt_p <= p.retry_alternate_margin and tried == 0:
                        return self._rule(
                            "retry_alternate",
                            "retry_alternate",
                            f"target confidence {tconf:.2f} < {p.act_target_confidence}; alternate {alt} p={alt_p:.2f} within {p.retry_alternate_margin} of chosen p={chosen_p:.2f}",
                        )
                return self._rule("target_confidence", "escalate", f"target confidence {tconf:.2f} < {p.act_target_confidence}")

        return self._rule("act", "act", f"operation {decision.operation_confidence:.2f}, target {decision.target_confidence}")

    # ---- reporting -------------------------------------------------------------

    def summary_for_s2(self, agent: Any, n: int = 8) -> str:
        """Compact text of the last ``n`` S1 steps, injected into S2's context on escalation."""
        records: dict[int, Any] = getattr(agent, "s1_records", {}) or {}
        steps = sorted(set(self._log) | set(records))[-n:]
        if not steps:
            return "System 1 has not acted yet."
        lines = ["Recent System 1 steps (fast policy):"]
        for s in steps:
            log = self._log.get(s)
            rec = records.get(s)
            if log is not None:
                where = f" [{log.target}] {log.label[:50]!r}" if log.target is not None and log.label else (f" [{log.target}]" if log.target is not None else "")
                line = f"  step {s}: {log.operation}{where} -> {log.verdict.kind} ({log.verdict.reason})"
                if log.effect:
                    line += f"; effect: {log.effect}"
            else:
                verdict = getattr(rec, "verdict", None)
                err = getattr(rec, "error", None)
                line = f"  step {s}: {'escalated' if verdict is None or verdict.kind != 'act' else 'acted'}"
                if verdict is not None:
                    line += f" ({verdict.reason})"
                if err:
                    line += f"; error: {err}"
            lines.append(line)
        return "\n".join(lines)
