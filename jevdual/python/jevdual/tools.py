"""act_toward_goal: the System 1 micro-loop packaged as a browser-use tool (task D6).

System 2 can delegate a short subgoal ("get to checkout", "open the pricing
page", "scroll until the table is visible") in one tool call. The loop runs
menu -> Jev -> floors -> bridge -> registry inside that call, through the same
browser session so the watchdogs apply, and returns a structured result plus a
one-paragraph summary for System 2's memory. The host LLM never sees the
micro-steps. It never executes a ``done`` action itself: ``done``/``blocked``
from the policy end the loop with a status, and the caller decides.
"""

import inspect
import json
import logging
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from browser_use.agent.views import ActionResult
from browser_use.browser.session import BrowserSession
from pydantic import BaseModel, Field

from jevdual.bridge import Bridge, BridgeError
from jevdual.effects import diff
from jevdual.menu import Menu, build_menu
from jevdual.policy import Decision, PolicyError, StepContext

log = logging.getLogger("jevdual.tools")

Status = Literal[
    "reached",
    "paused_before_action",
    "blocked",
    "budget_exhausted",
    "low_confidence",
    "needs_text",
    "stuck",
    "error",
]

DEFAULT_PAUSE_KEYWORDS: tuple[str, ...] = (
    "delete",
    "remove",
    "pay",
    "purchase",
    "buy now",
    "place order",
    "send",
    "unsubscribe",
    "deactivate",
    "删除",
    "支付",
    "购买",
    "确认订单",
    "发送",
)


@dataclass(frozen=True)
class MicroLoopConfig:
    max_steps: int = 10
    operation_floor: float = 0.55
    target_floor: float = 0.45
    destructive_floor: float = 0.5
    pause_before_keywords: tuple[str, ...] = DEFAULT_PAUSE_KEYWORDS
    no_effect_limit: int = 2


@dataclass
class MicroLoopResult:
    status: Status
    goal: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    final_url: str | None = None
    reason: str = ""
    jev_calls: int = 0
    wall_ms: float = 0.0

    def summary(self) -> str:
        acts = "; ".join(
            f"{s['operation']} {s.get('label', '')}".strip() for s in self.steps if s.get("executed")
        )
        tail = f" Last: {acts}." if acts else ""
        return f"act_toward_goal({self.goal!r}) -> {self.status} after {len(self.steps)} step(s) at {self.final_url}. {self.reason}{tail}".strip()

    def to_json(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "goal": self.goal,
            "final_url": self.final_url,
            "reason": self.reason,
            "steps": self.steps,
            "jev_calls": self.jev_calls,
            "wall_ms": round(self.wall_ms, 1),
        }


class GoalParams(BaseModel):
    goal: str = Field(
        description="A short, concrete subgoal for the fast navigator, e.g. 'open the pricing page'."
    )
    max_steps: int = Field(default=10, ge=1, le=25, description="Step budget for the micro-loop.")


DecideFn = Callable[[Menu, StepContext], Awaitable[Decision]]
TextFn = Callable[[str, Any, Menu], Any]


def _keyword_hit(label: str, keywords: tuple[str, ...]) -> str | None:
    try:
        from jevdual.arbiter import match_destructive_keyword

        return match_destructive_keyword(label, list(keywords))
    except ImportError:  # pragma: no cover
        low = label.casefold()
        return next((k for k in keywords if k.casefold() in low), None)


async def run_micro_loop(
    goal: str,
    browser_session: BrowserSession,
    tools: Any,
    *,
    decide: DecideFn,
    text_source: TextFn | None = None,
    config: MicroLoopConfig | None = None,
    max_steps: int | None = None,
) -> MicroLoopResult:
    cfg = config or MicroLoopConfig()
    budget = max_steps or cfg.max_steps
    action_model = tools.registry.create_action_model()
    bridge = Bridge(action_model, _OutputShim)
    result = MicroLoopResult(status="budget_exhausted", goal=goal)
    t0 = time.perf_counter()
    prev_menu: Menu | None = None
    no_effect = 0
    lines: list[str] = []

    for step in range(1, budget + 1):
        state = await browser_session.get_browser_state_summary(include_screenshot=False)
        menu = build_menu(state)
        result.final_url = menu.url
        effect = diff(prev_menu, menu)
        if prev_menu is not None:
            no_effect = no_effect + 1 if effect.no_effect else 0
            if no_effect >= cfg.no_effect_limit:
                result.status, result.reason = (
                    "stuck",
                    f"{no_effect} consecutive steps with no visible change",
                )
                break
        prev_menu = menu
        ctx = StepContext(task=goal, step=step, recent_actions=tuple(lines[-6:]))
        try:
            decision = await decide(menu, ctx)
        except PolicyError as exc:
            result.status, result.reason = "error", f"policy: {exc}"
            break
        result.jev_calls += 1
        target = menu.candidate(decision.target) if decision.target is not None else None
        rec: dict[str, Any] = {
            "step": step,
            "operation": decision.operation,
            "target": decision.target,
            "label": target.label[:60] if target else None,
            "op_p": round(decision.operation_confidence, 2),
            "target_p": decision.target_confidence,
            "url": menu.url,
            "executed": False,
        }
        result.steps.append(rec)

        if decision.operation == "done":
            result.status, result.reason = (
                "reached",
                f"policy reports goal reached (goal_done={decision.nouls.get('goal_done', 0):.2f})",
            )
            break
        if decision.operation == "blocked":
            result.status, result.reason = "blocked", "policy reports no operation can make progress"
            break
        if decision.operation_confidence < cfg.operation_floor or (
            decision.targeted and (decision.target_confidence or 0.0) < cfg.target_floor
        ):
            result.status, result.reason = (
                "low_confidence",
                f"op p={decision.operation_confidence:.2f}, target p={decision.target_confidence}",
            )
            break
        if decision.nouls.get("destructive", 0.0) >= cfg.destructive_floor or (
            target and _keyword_hit(target.label, cfg.pause_before_keywords)
        ):
            result.status, result.reason = (
                "paused_before_action",
                f"would act on {target.label!r} " if target else "destructive",
            )
            result.reason += f"(destructive={decision.nouls.get('destructive', 0):.2f})"
            break

        text = None
        if decision.operation in ("type", "select") and target is not None and text_source is not None:
            text = text_source(goal, target, menu)
            if inspect.isawaitable(text):
                text = await text
        if decision.operation in ("type", "select") and text is None:
            result.status, result.reason = (
                "needs_text",
                f"{decision.operation} into {target.label!r} needs composed text",
            )
            break

        try:
            bridged = bridge.build(decision, menu, step=step, text=text)
        except BridgeError as exc:
            result.status, result.reason = "error", f"bridge/{exc.reason}: {exc}"
            break
        for action in bridged.output.action:
            res = await tools.act(action, browser_session=browser_session)
            if res.error:
                result.status, result.reason = "error", res.error
                rec["error"] = res.error
                break
        else:
            rec["executed"] = True
            lines.append(bridged.memory_line)
            continue
        break
    result.wall_ms = (time.perf_counter() - t0) * 1000
    if result.final_url is None:
        result.final_url = await browser_session.get_current_page_url()
    return result


class _OutputShim:
    """Stands in for AgentOutput inside the micro-loop; only .action is read."""

    def __init__(self, action: list[Any], memory: str | None = None):
        self.action = action
        self.memory = memory


def register_act_toward_goal(
    tools: Any, *, decide: DecideFn, text_source: TextFn | None = None, config: MicroLoopConfig | None = None
) -> None:
    """Register ``act_toward_goal`` on a browser-use Tools registry."""

    @tools.action(
        "Delegate a short, concrete subgoal to the fast navigator (System 1), e.g. 'open the pricing page', "
        "'get to checkout', 'scroll until the results table is visible'. It clicks, types literal text, scrolls and "
        "navigates on its own for up to max_steps, never confirms destructive actions, and returns a status "
        "(reached, paused_before_action, blocked, low_confidence, needs_text, stuck, budget_exhausted, error) with "
        "a step summary. Do not use it to read or answer; observe the page yourself afterwards.",
        param_model=GoalParams,
    )
    async def act_toward_goal(params: GoalParams, browser_session: BrowserSession) -> ActionResult:
        result = await run_micro_loop(
            params.goal,
            browser_session,
            tools,
            decide=decide,
            text_source=text_source,
            config=config,
            max_steps=params.max_steps,
        )
        log.info("act_toward_goal: %s", result.summary())
        return ActionResult(
            extracted_content=json.dumps(result.to_json(), ensure_ascii=False),
            long_term_memory=result.summary(),
        )


# --- Q9: delegation as a mode of the evaluated agent -------------------------------------------


_NEEDS_VALUES = re.compile(
    r"\b(sign|log)[ -]?in\b|\bfill\b|\benter\b|\btype\b|\bform\b|\busername\b|\bpassword\b|\bsearch\b|\bquery\b",
    re.IGNORECASE,
)
_QUOTED = re.compile(r"[\"'\u201c\u2018]([^\"'\u201d\u2019]{1,120})[\"'\u201d\u2019]")


class SubgoalParams(BaseModel):
    goal: str = Field(
        description="One concrete subgoal for the fast navigator, e.g. 'add the Sauce Labs Backpack to the cart'."
    )
    stop_condition: str = Field(
        description="The observable outcome that means the subgoal is done, e.g. 'the cart badge shows 1 and the backpack button reads Remove'."
    )
    allowed_operations: list[str] = Field(
        default_factory=list,
        description="Operations the navigator may use: click, type, select, enter. Empty means all.",
    )
    known_values: dict[str, str] = Field(
        default_factory=dict,
        description="Field name or label -> value to type, e.g. {'search': 'Eiffel Tower'} or {'First Name': 'Ada'}; secrets by placeholder as usual. Required for any goal that searches, signs in or fills a form.",
    )
    max_steps: int = Field(default=8, ge=1, le=20, description="Step budget before it reports back.")


def register_delegation(tools: Any, agent_ref: Callable[[], Any]) -> None:
    """Register ``delegate_subgoal`` on a Tools registry. The action starts a bounded delegation on the
    agent returned by ``agent_ref``; the agent's own loop then runs System 1 under that assignment
    (gate, secrets, freshness and verification apply as for any step) until the stop condition has
    observed support, the budget is used, or it gets stuck, and System 2 gets a summary message."""
    from jevdual.s1 import Delegation

    @tools.action(
        "Delegate one bounded, mechanical subgoal (navigate, search, fill and submit a form, add an item, sign in) to a "
        "fast navigator that acts without you. Give it a concrete goal, the observable stop condition, the values it "
        "should type, and a step budget. It reports back with a summary; you then continue. Do not delegate reading, "
        "comparing or answering.",
        param_model=SubgoalParams,
    )
    async def delegate_subgoal(params: SubgoalParams) -> ActionResult:
        agent = agent_ref()
        if agent is None:
            return ActionResult(error="delegation unavailable: no agent")
        if getattr(agent, "delegation", None) is not None:
            return ActionResult(error="a delegation is already active")
        if _NEEDS_VALUES.search(params.goal) and not params.known_values and not _QUOTED.search(params.goal):
            return ActionResult(
                error="this assignment types into a field but gave no value: pass known_values (e.g. {'search': 'Eiffel Tower'} "
                "or {'username': 'standard_user', 'password': '<secret>sauce_password</secret>'}) or put the exact text in "
                "quotes in the goal"
            )
        agent.delegation = Delegation(
            goal=params.goal,
            stop_condition=params.stop_condition,
            allowed_operations=tuple(params.allowed_operations),
            known_values=tuple((k, v) for k, v in params.known_values.items()),
            budget=params.max_steps,
            started_step=getattr(getattr(agent, "state", None), "n_steps", 0),
        )
        log.info("delegation started: %r (budget %s)", params.goal, params.max_steps)
        return ActionResult(
            extracted_content=f"Delegated to the fast navigator: {params.goal!r} until {params.stop_condition!r} (budget {params.max_steps}). It will report back.",
            include_in_memory=True,
        )


DELEGATION_GUIDANCE = """
You have a fast navigator you can hand a bounded assignment to with `delegate_subgoal`. It acts on its own and
reports back with a summary; control is yours again afterwards.

Always delegate these workflows as your first step on them: signing in (username, password and the submit);
filling and submitting a form with values you already know; adding a named item to the cart and opening the
cart; running a search and opening the matching result; opening a named page or article from a search box or
menu; dismissing a dialog and then continuing. Give it a concrete goal, the observable stop condition (what
the page will show when it is done), the values to type, and a step budget of 6 to 10.

Do it yourself when the whole remaining job is one click on a target you can already see. Keep for yourself:
reading, comparing, choosing between options, composing the final answer, and any action that pays, deletes
or sends. If the navigator reports not reached, stuck or paused, decide the next step yourself; do not
re-delegate the same goal more than once.
""".strip()

EVIDENCE_GUIDANCE = """
Before answering a question from a page, call `find_evidence` with the exact question; quote from the
spans it returns. If it reports no answer present, navigate elsewhere rather than guessing.
""".strip()
