"""DualProcessAgent: browser-use's Agent with a System 1 policy at the decision seam.

browser-use's ``Agent.step`` is prepare, decide, execute, post-process. The
decide phase is ``_get_next_action``, whose only contract is to leave an
``AgentOutput`` in ``self.state.last_model_output``. This subclass overrides
that one method: a System 1 policy gets first shot; when it declines (returns
``None``) the stock LLM path runs unchanged. Everything downstream (multi_act,
watchdogs, history, GIF, callbacks) is inherited.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol

from browser_use.agent.service import Agent

if TYPE_CHECKING:
    from browser_use.agent.views import AgentOutput
    from browser_use.browser.views import BrowserStateSummary

log = logging.getLogger("jevdual.agent")


class S1Policy(Protocol):
    """A System 1 decision source.

    ``decide`` returns an ``AgentOutput`` built with ``agent.AgentOutput`` and
    ``agent.ActionModel`` (so it validates against the live tool registry), or
    ``None`` to escalate this step to System 2.
    """

    async def decide(self, agent: DualProcessAgent, state: BrowserStateSummary) -> AgentOutput | None: ...


class DualProcessAgent(Agent):
    """browser-use Agent with an S1 policy in front of the LLM.

    Extra keyword: ``s1_policy``. Everything else is passed to ``Agent``.
    """

    def __init__(
        self,
        *args,
        s1_policy: S1Policy | None = None,
        destructive_keywords: tuple[str, ...] | None = None,
        authorized_destructive: bool = False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.s1_policy = s1_policy
        #: Pre-dispatch gate for BOTH systems: an index-bearing action whose target label matches a
        #: destructive keyword is replaced by a failed done asking for confirmation, unless the task
        #: authorized irreversible actions. System 2 clicked "Delete account" without this.
        if destructive_keywords is None:
            from jevdual.arbiter import ArbiterPolicy

            destructive_keywords = ArbiterPolicy.from_toml().destructive_keywords
        self.destructive_keywords = destructive_keywords
        self.authorized_destructive = authorized_destructive
        self.paused_before_action: dict[str, Any] | None = None
        self.s1_steps = 0
        self.s2_steps = 0
        #: step number -> "s1" | "s2", read by the eval rig when it builds the trace.
        self.step_systems: dict[int, str] = {}

    def _destructive_hit(self, actions: list[Any]) -> tuple[str, str, int] | None:
        from jevdual.arbiter import match_destructive_keyword

        session = self.browser_session
        cached = getattr(session, "_cached_browser_state_summary", None)
        selector_map = getattr(getattr(cached, "dom_state", None), "selector_map", None) or {}
        for action in actions:
            idx = action.get_index()
            if idx is None or idx not in selector_map:
                continue
            node = selector_map[idx]
            label = (node.ax_node.name if node.ax_node and node.ax_node.name else "") or node.get_all_children_text(max_depth=2) or ""
            label = label or (node.attributes or {}).get("value", "") or (node.attributes or {}).get("aria-label", "")
            kw = match_destructive_keyword(label, self.destructive_keywords)
            if kw:
                return label[:80], kw, idx
        return None

    async def _execute_actions(self) -> None:
        out = self.state.last_model_output
        if out is not None and not self.authorized_destructive:
            hit = self._destructive_hit(list(out.action))
            if hit is not None:
                label, kw, idx = hit
                system = self.step_systems.get(self.state.n_steps, "s2")
                self.paused_before_action = {"step": self.state.n_steps, "system": system, "label": label, "keyword": kw, "index": idx}
                log.warning("step %s: %s proposed an action on %r (matches %r); pausing for confirmation", self.state.n_steps, system, label, kw)
                out.action = [
                    self.ActionModel(
                        done={
                            "text": f"Paused before a destructive action: {label!r} matches {kw!r} and needs confirmation. "
                            "Nothing was clicked.",
                            "success": False,
                        }
                    )
                ]
        await super()._execute_actions()

    async def _get_next_action(self, browser_state_summary: BrowserStateSummary) -> None:
        if self.s1_policy is None:
            self.s2_steps += 1
            self.step_systems[self.state.n_steps] = "s2"
            await super()._get_next_action(browser_state_summary)
            return

        decision = await self.s1_policy.decide(self, browser_state_summary)
        if decision is None:
            log.info("step %s: S1 declined, escalating to S2", self.state.n_steps)
            self.s2_steps += 1
            self.step_systems[self.state.n_steps] = "s2"
            await super()._get_next_action(browser_state_summary)
            return

        self.s1_steps += 1
        self.step_systems[self.state.n_steps] = "s1"
        self.state.last_model_output = decision

        # Mirror the upstream method's tail so pause/stop, step callbacks and
        # conversation saving behave the same for S1 steps as for S2 steps.
        await self._check_stop_or_pause()
        await self._handle_post_llm_processing(browser_state_summary, self._message_manager.get_messages())
        await self._check_stop_or_pause()
