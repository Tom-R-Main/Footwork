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
from typing import TYPE_CHECKING, Protocol

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

    async def decide(self, agent: "DualProcessAgent", state: "BrowserStateSummary") -> "AgentOutput | None": ...


class DualProcessAgent(Agent):
    """browser-use Agent with an S1 policy in front of the LLM.

    Extra keyword: ``s1_policy``. Everything else is passed to ``Agent``.
    """

    def __init__(self, *args, s1_policy: S1Policy | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.s1_policy = s1_policy
        self.s1_steps = 0
        self.s2_steps = 0

    async def _get_next_action(self, browser_state_summary: "BrowserStateSummary") -> None:
        if self.s1_policy is None:
            self.s2_steps += 1
            await super()._get_next_action(browser_state_summary)
            return

        decision = await self.s1_policy.decide(self, browser_state_summary)
        if decision is None:
            log.info("step %s: S1 declined, escalating to S2", self.state.n_steps)
            self.s2_steps += 1
            await super()._get_next_action(browser_state_summary)
            return

        self.s1_steps += 1
        self.state.last_model_output = decision

        # Mirror the upstream method's tail so pause/stop, step callbacks and
        # conversation saving behave the same for S1 steps as for S2 steps.
        await self._check_stop_or_pause()
        await self._handle_post_llm_processing(browser_state_summary, self._message_manager.get_messages())
        await self._check_stop_or_pause()
