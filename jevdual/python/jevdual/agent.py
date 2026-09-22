"""DualProcessAgent: browser-use's Agent with a System 1 policy at the decision seam.

browser-use's ``Agent.step`` is prepare, decide, execute, post-process. The
decide phase is ``_get_next_action``, whose only contract is to leave an
``AgentOutput`` in ``self.state.last_model_output``. This subclass overrides
that one method: a System 1 policy gets first shot; when it declines (returns
``None``) the stock LLM path runs unchanged. Everything downstream (multi_act,
watchdogs, history, GIF, callbacks) is inherited.
"""

from __future__ import annotations

import dataclasses
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
        authorized_actions: tuple[str, ...] = (),
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.s1_policy = s1_policy
        #: Pre-dispatch gate for BOTH systems: an index-bearing action whose target label matches a
        #: destructive keyword is replaced by a failed done asking for confirmation, unless the task
        #: authorized irreversible actions. System 2 clicked "Delete account" without this.
        from jevdual.arbiter import ArbiterPolicy

        self.gate_policy = ArbiterPolicy.from_toml()
        if destructive_keywords is not None:
            self.gate_policy = dataclasses.replace(self.gate_policy, destructive_keywords=tuple(destructive_keywords))
        self.destructive_keywords = self.gate_policy.destructive_keywords
        #: Q8: `evaluate` is refused recoverably (the step becomes a wait plus a message) up to this many
        #: times per run, then paused. Three of every arm's live misses were terminal evaluate pauses.
        self.max_evaluate_refusals = 2
        self.evaluate_refusals = 0
        self.authorized_destructive = authorized_destructive
        #: Scope of the task's authorisation: keywords a target must match for the gate and the
        #: arbiter to stand down (place order, submit, finish). Empty with authorized_destructive
        #: means task-wide, which is the old behaviour and is reported as such.
        self.authorized_actions = tuple(k.casefold() for k in authorized_actions)
        self.paused_before_action: dict[str, Any] | None = None
        self.s2_verifications: list[dict[str, Any]] = []
        self.s2_done_rejections = 0
        self.max_done_rejections = 2
        self.s1_steps = 0
        self.s2_steps = 0
        #: step number -> "s1" | "s2", read by the eval rig when it builds the trace.
        self.step_systems: dict[int, str] = {}
        #: Q9: the bounded assignment System 2 handed to System 1, if any, and the finished ones.
        self.delegation: Any = None
        self.delegations: list[Any] = []

    def is_authorized(self, text: str | None) -> bool:
        """Whether the task authorises an irreversible action on ``text`` (a target label, URL or keyword)."""
        if not self.authorized_destructive:
            return False
        if not self.authorized_actions:
            return True  # task-wide authorisation
        low = (text or "").casefold()
        return any(k in low for k in self.authorized_actions)

    def _gate_rules(self) -> Any:
        """The gate's keyword policy; a stand-in agent without one gets the shipped defaults."""
        policy = getattr(self, "gate_policy", None)
        if policy is None:
            from jevdual.arbiter import ArbiterPolicy

            policy = ArbiterPolicy.from_toml()
            if getattr(self, "destructive_keywords", None):
                policy = dataclasses.replace(policy, destructive_keywords=tuple(self.destructive_keywords))
        return policy

    def _destructive_hit(self, actions: list[Any]) -> tuple[str, str, int] | None:
        from jevdual.arbiter import destructive_match

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
            kw = destructive_match(label, DualProcessAgent._gate_context(self, node), DualProcessAgent._gate_rules(self))
            if kw:
                return label[:80], kw, idx
        return None

    def _gate_context(self, node: Any = None) -> str:
        """URL, title and the nearest ancestor text of a node: what a contextual keyword is judged against."""
        cached = getattr(self.browser_session, "_cached_browser_state_summary", None)
        parts = [str(getattr(cached, "url", "") or ""), str(getattr(cached, "title", "") or "")]
        parent = getattr(node, "parent_node", None)
        hops = 0
        while parent is not None and hops < 4:
            attrs = getattr(parent, "attributes", None) or {}
            for key in ("aria-label", "id", "class", "name"):
                if attrs.get(key):
                    parts.append(str(attrs[key]))
            parent = getattr(parent, "parent_node", None)
            hops += 1
        return " ".join(parts)

    async def _active_element_label(self) -> str:
        """Label of the focused element and its form's submit control, for gating Enter."""
        js = (
            "(()=>{const a=document.activeElement;if(!a)return '';const f=a.form||a.closest('form');"
            "const p=[a.getAttribute('aria-label')||'',a.value||'',a.innerText||''];"
            "if(f){const b=f.querySelector('button[type=submit],input[type=submit],button:not([type])');"
            "if(b)p.push(b.innerText||b.value||'');p.push(f.getAttribute('action')||'')}"
            "return p.join(' | ').slice(0,300)})()"
        )
        try:
            cdp = await self.browser_session.get_or_create_cdp_session()
            r = await cdp.cdp_client.send.Runtime.evaluate(params={"expression": js, "returnByValue": True}, session_id=cdp.session_id)
            return str(r.get("result", {}).get("value") or "")
        except Exception as exc:  # noqa: BLE001 - if we cannot see the focus, we gate conservatively below
            log.warning("active element lookup failed: %s", exc)
            return ""

    async def _destructive_hit_any(self, actions: list[Any]) -> tuple[str, str, int] | None:
        """Extend the index-based gate to actions that carry no index.

        evaluate runs arbitrary page script and is refused outright without authorization;
        navigate is checked against the destination url; send_keys with Enter is checked
        against the focused element and its form's submit control.
        """
        from jevdual.arbiter import destructive_match

        hit = self._destructive_hit(actions)
        if hit is not None:
            return hit
        keywords = tuple(k.casefold() for k in self.destructive_keywords)
        context = DualProcessAgent._gate_context(self)
        for action in actions:
            data = action.model_dump(exclude_unset=True)
            name = next(iter(data))
            params = data[name] or {}
            if name == "evaluate":
                return ("evaluate (arbitrary page script)", "evaluate", -1)
            if name == "navigate":
                url = str(params.get("url", ""))
                path = url.casefold()
                kw = next((k for k in keywords if k in path), None)
                if kw:
                    return (f"navigate to {url}", kw, -1)
            if name == "send_keys" and "enter" in str(params.get("keys", "")).casefold():
                label = await self._active_element_label()
                if not label:
                    return ("Enter with unknown focused element", "enter", -1)
                kw = destructive_match(label, context, DualProcessAgent._gate_rules(self))
                if kw:
                    return (f"Enter in {label[:80]!r}", kw, -1)
        return None

    async def _verify_s2_done(self, out: Any) -> None:
        """System 2's own done goes through the same verifier as System 1's.

        A rejected done is replaced by a one-second wait plus a context message so the run
        continues; after ``max_done_rejections`` the done is allowed but marked UNVERIFIED with
        success=False so it can never count as a claimed completion.
        """
        verifier = getattr(self.s1_policy, "verifier", None)
        if verifier is None:
            return
        done = next((a for a in out.action if a.model_dump(exclude_unset=True).get("done") is not None), None)
        if done is None:
            return
        params = dict(done.model_dump(exclude_unset=True)["done"] or {})
        if params.get("success", True) is False:
            return
        from jevdual.menu import build_menu

        state = getattr(self.browser_session, "_cached_browser_state_summary", None)
        if state is None:
            return
        menu = build_menu(state)
        store = getattr(self.s1_policy, "secrets", None)
        if store is not None:
            from jevdual.s1 import redact_menu

            menu = redact_menu(menu, store.redactor())
        band, reason = await verifier.judge_done(self, menu, answer=params.get("text"))
        last = getattr(verifier, "last", None)
        scores = last.to_trace() if last is not None and hasattr(last, "to_trace") else {"band": band, "reason": reason}
        self.s2_verifications.append({"step": self.state.n_steps, "band": band, "reason": reason, **{k: v for k, v in scores.items() if k not in ("band", "reason")}})
        if band == "accept":
            return
        self.s2_done_rejections += 1
        if self.s2_done_rejections <= self.max_done_rejections:
            from browser_use.llm.messages import UserMessage

            log.info("step %s: System 2 done rejected by verification (%s): %s", self.state.n_steps, band, reason)
            out.action = [self.ActionModel(wait={"seconds": 1})]
            self._message_manager._add_context_message(
                UserMessage(
                    content=f"Your done was not accepted by verification ({band}): {reason}. Continue the task. "
                    "If it asks for an answer, the answer must quote what the page shows."
                )
            )
        else:
            params["success"] = False
            params["text"] = "UNVERIFIED: " + str(params.get("text", ""))
            out.action = [self.ActionModel(done=params)]

    async def _execute_actions(self) -> None:
        out = self.state.last_model_output
        if out is not None and self.step_systems.get(self.state.n_steps) == "s2":
            await self._verify_s2_done(out)
        if out is not None:
            hit = await self._destructive_hit_any(list(out.action))
            if hit is not None and self.is_authorized(f"{hit[0]} {hit[1]}"):
                hit = None  # within the task's authorised scope (matched by label or keyword)
            if hit is not None and hit[1] == "evaluate" and self.evaluate_refusals < self.max_evaluate_refusals:
                # recoverable refusal: the driver loses this step and is told what it may use instead
                from browser_use.llm.messages import UserMessage

                self.evaluate_refusals += 1
                log.warning("step %s: evaluate refused (%s of %s); the driver keeps control", self.state.n_steps, self.evaluate_refusals, self.max_evaluate_refusals)
                out.action = [self.ActionModel(wait={"seconds": 1})]
                self._message_manager._add_context_message(
                    UserMessage(
                        content="evaluate (page script) is not permitted here. Use click, input, select_dropdown, send_keys, "
                        "scroll, navigate, extract or find_evidence instead, or report what you found. If a click had no effect, "
                        "try the element's text or a different control rather than scripting it."
                    )
                )
                hit = None
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
