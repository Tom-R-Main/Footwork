"""Bridge: turn a System 1 Decision into browser-use's AgentOutput.

The model never emits a selector or code; it picked an operation and an ``id``
from the menu. The bridge maps that to the registry's action model, refuses to
dispatch against a snapshot other than the one the decision was made from
(freshness guard), synthesizes the one-line memory that keeps System 2's
history readable, and records the proposed actions for the trace so
proposed-vs-executed is auditable.

Action names and parameters are the ones pinned by the A4 contract tests:
click(index), input(index, text, clear), select_dropdown(index, text),
send_keys(keys), scroll(down, pages, index), go_back(description),
wait(seconds), done(text, success).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from jevdual.menu import Candidate, Menu
from jevdual.policy import Decision
from jevdual.trace import ActionRecord

if TYPE_CHECKING:
    from browser_use.browser.views import BrowserStateSummary

BridgeReason = Literal["stale", "unknown_operation", "target_missing", "text_required", "unsupported"]

WAIT_SECONDS = 2
SCROLL_PAGES = 1.0


class BridgeError(Exception):
    """A decision that cannot be dispatched. ``reason`` is what the arbiter keys on."""

    def __init__(self, reason: BridgeReason, message: str):
        super().__init__(message)
        self.reason: BridgeReason = reason


@dataclass(frozen=True)
class Bridged:
    output: Any
    proposed: tuple[ActionRecord, ...]
    memory_line: str
    operation: str
    target: Candidate | None


def _record(action: Any) -> ActionRecord:
    data = action.model_dump(exclude_unset=True)
    name = next(iter(data))
    return ActionRecord(name=name, params=data[name] or {})


def memory_line(step: int, decision: Decision, target: Candidate | None, menu: Menu) -> str:
    """One line per S1 step; System 2 reads these from history on escalation."""
    where = f"[{target.id}] {target.label[:60]!r}" if target is not None else ""
    tp = f" p={decision.target_confidence:.2f}" if decision.target_confidence is not None else ""
    nouls = " ".join(f"{k}={v:.2f}" for k, v in decision.nouls.items() if k in ("goal_done", "stuck", "destructive"))
    return f"S1 step {step}: {decision.operation} {where}{tp} (op p={decision.operation_confidence:.2f}; {nouls}) on {menu.url}".replace("  ", " ")


class Bridge:
    """Builds actions with the agent's live ActionModel/AgentOutput classes."""

    def __init__(self, action_model: type, output_model: type):
        self.ActionModel = action_model
        self.AgentOutput = output_model

    def build(
        self,
        decision: Decision,
        menu: Menu,
        *,
        step: int,
        text: str | None = None,
        done_text: str | None = None,
        blocked_reason: str | None = None,
    ) -> Bridged:
        op = decision.operation
        target: Candidate | None = None
        if decision.targeted:
            if decision.target is None:
                raise BridgeError("target_missing", f"{op} needs a target but the decision has none")
            target = menu.candidate(decision.target)
            if target is None:
                raise BridgeError("target_missing", f"target {decision.target} is not in the menu")
            if op not in target.operations and not (op == "hover" and "click" in target.operations):
                raise BridgeError("unsupported", f"candidate {target.id} does not support {op} (has {target.operations})")

        A = self.ActionModel
        actions: list[Any]
        if op == "click":
            actions = [A(click={"index": target.id})]
        elif op == "hover":
            # The default registry has no hover; hover-revealed menus almost always open on click too.
            actions = [A(click={"index": target.id})]
        elif op == "type":
            if text is None:
                raise BridgeError("text_required", "type needs composed text (task D4)")
            actions = [A(input={"index": target.id, "text": text, "clear": True})]
        elif op == "select":
            if text is None:
                raise BridgeError("text_required", "select needs the option text (task D4)")
            actions = [A(select_dropdown={"index": target.id, "text": text})]
        elif op == "enter":
            actions = [A(click={"index": target.id}), A(send_keys={"keys": "Enter"})]
        elif op == "scroll":
            actions = [A(scroll={"down": True, "pages": SCROLL_PAGES, "index": target.id})]
        elif op == "scroll_page":
            actions = [A(scroll={"down": True, "pages": SCROLL_PAGES})]
        elif op == "back":
            actions = [A(go_back={})]
        elif op == "wait":
            actions = [A(wait={"seconds": WAIT_SECONDS})]
        elif op == "done":
            actions = [A(done={"text": done_text or "Task complete.", "success": True})]
        elif op == "blocked":
            actions = [A(done={"text": f"Blocked: {blocked_reason or 'no offered operation can make progress'}", "success": False})]
        else:
            raise BridgeError("unknown_operation", f"policy returned unknown operation {op!r}")

        line = memory_line(step, decision, target, menu)
        output = self.AgentOutput(action=actions, memory=line)
        return Bridged(output=output, proposed=tuple(_record(a) for a in actions), memory_line=line, operation=op, target=target)


def assert_fresh(agent: Any, state: BrowserStateSummary, menu: Menu, decision: Decision) -> None:
    """Refuse to dispatch unless the session's cached state is the one the menu came from.

    ``multi_act`` executes against ``browser_session._cached_browser_state_summary``;
    if that object is not the state this menu was built from, the indices may
    point at different elements.
    """
    session = getattr(agent, "browser_session", None)
    cached = getattr(session, "_cached_browser_state_summary", None)
    if cached is not state:
        raise BridgeError("stale", "decision was made on a snapshot that is no longer the session's cached state")
    if menu.url != state.url:
        raise BridgeError("stale", f"menu url {menu.url!r} != state url {state.url!r}")
    if decision.targeted and decision.target is not None and decision.target not in state.dom_state.selector_map:
        raise BridgeError("stale", f"target {decision.target} is no longer in the selector map")
