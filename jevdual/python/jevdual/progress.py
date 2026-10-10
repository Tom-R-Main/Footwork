"""Progress in a model-driven run, computed from state rather than asked of the model (M3).

Q19's model spent 40 of its 78 steps on two tasks without progress: alternating between two pages of an
unavailable report (H03) and repeating actions inside a Preview sheet (H08). A step budget ends such a
run but says nothing useful. This module keeps, per surface, a signature of each observed state and the
actions already tried in it, and counts steps without progress (a state not seen before, a newly carried
value, or a confirmed effect). After ``patience`` such steps the run enters a bounded recovery phase; if
``recovery_steps`` more pass without progress, the run ends ``no_progress`` with the states and actions
named. A detector can say "these attempts made no progress"; it never concludes the task is impossible.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

_KEY_FIELDS = ("name", "surface", "op", "target", "text", "keys", "path", "match", "menu_bar")


def signature(state: dict[str, Any]) -> str:
    """A state's identity from a session's last observation: window or page, text, elements and values."""
    parts = [
        str(state.get("last_url") or ""),
        str(state.get("last_title") or ""),
        str(state.get("last_page_text") or "")[:3000],
        *sorted(
            f"{c.get('role')}:{c.get('label')}={c.get('value')}" for c in state.get("last_candidates") or []
        ),
    ]
    return hashlib.sha1("\x1f".join(parts).encode()).hexdigest()[:12]


def action_key(action: dict[str, Any]) -> str:
    return json.dumps(
        {k: action.get(k) for k in _KEY_FIELDS if action.get(k) not in (None, "", [])}, sort_keys=True
    )


@dataclass
class Progress:
    patience: int = 4
    recovery_steps: int = 3
    seen: set[tuple[str, str]] = field(default_factory=set)
    tried: dict[tuple[str, str], dict[str, tuple[int, str]]] = field(default_factory=dict)
    values: set[str] = field(default_factory=set)
    streak: int = 0
    recovery_left: int | None = None
    #: recent steps without progress, for the no_progress reason
    stale: list[str] = field(default_factory=list)

    def enter(self, surface: str, sig: str) -> None:
        """A surface's first observation is not progress; it is where the run starts."""
        self.seen.add((surface, sig))

    def already(self, surface: str, sig: str, action: dict[str, Any]) -> str | None:
        """Why an action should not run again in this state, or None."""
        hit = self.tried.get((surface, sig), {}).get(action_key(action))
        if hit is None:
            return None
        step, summary = hit
        return f"already tried in this same state at step {step} ({summary[:120]}); choose a different action or stop"

    def after(
        self,
        step: int,
        surface: str,
        sig_before: str,
        action: dict[str, Any],
        sig_after: str,
        summary: str,
        *,
        confirmed_effect: bool = False,
        new_values: tuple[str, ...] = (),
    ) -> None:
        self.tried.setdefault((surface, sig_before), {})[action_key(action)] = (step, summary)
        fresh = [v for v in new_values if v not in self.values]
        self.values.update(new_values)
        progressed = (surface, sig_after) not in self.seen or confirmed_effect or bool(fresh)
        self.seen.add((surface, sig_after))
        self.refused_or_idle(step, action, summary, progressed=progressed)

    def refused_or_idle(
        self, step: int, action: dict[str, Any], summary: str, *, progressed: bool = False
    ) -> None:
        if progressed:
            self.streak, self.recovery_left, self.stale = 0, None, []
            return
        self.streak += 1
        self.stale = [*self.stale[-5:], f"step {step} {action_key(action)[:100]}: {summary[:80]}"]
        if self.recovery_left is not None:
            self.recovery_left -= 1
        elif self.streak >= self.patience:
            self.recovery_left = self.recovery_steps

    @property
    def in_recovery(self) -> bool:
        return self.recovery_left is not None

    @property
    def exhausted(self) -> bool:
        return self.recovery_left is not None and self.recovery_left <= 0

    def note(self) -> str | None:
        if not self.in_recovery:
            return None
        return (
            f"RECOVERY ({self.recovery_left} step(s) left): the last {self.streak} steps made no progress (no new "
            "state, no new value, no confirmed effect). Do something that changes the state, or stop with the "
            "reason. Recent steps: " + " | ".join(self.stale[-4:])
        )

    def reason(self) -> str:
        return f"no progress in {self.streak} steps; recent: " + " | ".join(self.stale[-4:])
