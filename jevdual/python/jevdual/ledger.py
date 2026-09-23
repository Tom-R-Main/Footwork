"""Trajectory evidence for verification.

Two pieces, both cheap:

* ``trajectory_from_agent`` summarises the run so far from browser-use's history: per step the URL,
  the actions executed (name, index, the element interacted with, redacted text) and the model's
  memory line. The verifier gets it as ``state.trajectory`` next to the current page, so a
  requirement that names an action ("Password entered", "Search submitted", "Signed in") can be
  judged from the trail after the page has moved on. This changes the state, not the number of
  Jev calls.
* ``Ledger`` remembers, per requirement, the lowest ``unmet`` probability any verification in this
  run has assigned it. A requirement judged met once stays met (monotone within a run); the
  band is computed on the ledger-adjusted values. Live validation run 0 showed 120 of 224
  rejections were per-requirement verdicts on actions no longer visible on the final page.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

_LABEL_ATTRS = ("aria-label", "placeholder", "name", "title", "alt", "value", "id")
_TEXT_PARAMS = ("text", "keys", "query", "url")


def _element_label(el: Any) -> str | None:
    if el is None:
        return None
    attrs = getattr(el, "attributes", None) or {}
    for key in _LABEL_ATTRS:
        v = attrs.get(key)
        if v:
            return f"{getattr(el, 'node_name', '?').lower()} {key}={str(v)[:60]!r}"
    value = (getattr(el, "node_value", "") or "").strip()
    if value:
        return f"{getattr(el, 'node_name', '?').lower()} {value[:60]!r}"
    node_type = attrs.get("type")
    name = getattr(el, "node_name", "?").lower()
    return f"{name} type={node_type}" if node_type else name


def _action_line(action: Any, element: Any, redact: Callable[[str], str]) -> str:
    dumped = action.model_dump(exclude_unset=True) if hasattr(action, "model_dump") else dict(action)
    name, params = next(iter(dumped.items()))
    params = dict(params or {})
    parts = []
    if "index" in params:
        parts.append(f"index={params['index']}")
    for key in _TEXT_PARAMS:
        if key in params and params[key] is not None:
            parts.append(f"{key}={redact(str(params[key]))[:80]!r}")
    for key in ("seconds", "down", "pages", "success"):
        if key in params:
            parts.append(f"{key}={params[key]}")
    label = _element_label(element)
    line = f"{name}({', '.join(parts)})"
    return f"{line} on {label}" if label else line


def trajectory_from_agent(
    agent: Any, redact: Callable[[str], str] | None = None, *, max_steps: int = 12
) -> list[dict[str, Any]]:
    """Per-step summary of the run so far, oldest first, at most ``max_steps`` most recent steps."""
    red = redact or (lambda s: s)
    history = getattr(getattr(agent, "history", None), "history", None) or []
    out: list[dict[str, Any]] = []
    for i, h in enumerate(history, start=1):
        model_output = getattr(h, "model_output", None)
        actions = list(getattr(model_output, "action", None) or [])
        elements = list(getattr(getattr(h, "state", None), "interacted_element", None) or [])
        lines = []
        for j, a in enumerate(actions):
            el = elements[j] if j < len(elements) else None
            try:
                lines.append(_action_line(a, el, red))
            except Exception:  # noqa: BLE001 - a malformed action must not break verification
                lines.append("?")
        errors = [r.error for r in (getattr(h, "result", None) or []) if getattr(r, "error", None)]
        entry: dict[str, Any] = {
            "step": i,
            "url": red(getattr(getattr(h, "state", None), "url", "") or ""),
            "actions": lines,
        }
        memory = getattr(model_output, "memory", None)
        if memory:
            entry["note"] = red(str(memory))[:200]
        if errors:
            entry["error"] = red(str(errors[0]))[:120]
        out.append(entry)
    return out[-max_steps:]


KINDS = ("historical_action", "current_state", "answer")


@dataclass
class Ledger:
    """What earlier verifications in this run established, per requirement, with three semantics:

    * ``historical_action`` (a form submitted, a page opened, text entered): once observed done it
      stays done; the lowest ``unmet`` ever seen carries forward.
    * ``current_state`` (an item is in the cart, signed in, a dialog dismissed): can change later, so
      the carried value is overridden by a *confident* fresh ``unmet`` (>= ``invalidate_at``), which is
      the verifier observing that the state no longer holds. A merely uncertain fresh reading keeps
      the carry.
    * ``answer`` (a value reported): evidence is per answer; nothing carries.

    Kinds come from one Choice per requirement asked in the first verification of the run (task
    static, one call). Until they are known every requirement is treated as historical, the
    behaviour before kinds existed.
    """

    best_unmet: dict[str, float] = field(default_factory=dict)
    kinds: dict[str, str] = field(default_factory=dict)
    met_threshold: float = 0.20
    invalidate_at: float = 0.70

    def kind(self, req: str) -> str:
        return self.kinds.get(req, "historical_action")

    def apply(self, unmet: dict[str, float]) -> dict[str, float]:
        out: dict[str, float] = {}
        for req, p in unmet.items():
            best = self.best_unmet.get(req, 1.0)
            k = self.kind(req)
            if k == "answer":
                out[req] = p
            elif k == "current_state" and p >= self.invalidate_at:
                out[req] = p  # fresh confident "not so": the state changed; the carry is void
            else:
                out[req] = min(p, best)
        return out

    def update(self, unmet: dict[str, float]) -> None:
        for req, p in unmet.items():
            k = self.kind(req)
            if k == "current_state" and p >= self.invalidate_at:
                self.best_unmet[req] = p  # reset: it must be observed met again to carry
            else:
                self.best_unmet[req] = min(p, self.best_unmet.get(req, 1.0))

    def set_kinds(self, kinds: dict[str, str]) -> None:
        for req, k in kinds.items():
            if k in KINDS:
                self.kinds[req] = k

    def met(self) -> tuple[str, ...]:
        return tuple(req for req, p in self.best_unmet.items() if p <= self.met_threshold)
