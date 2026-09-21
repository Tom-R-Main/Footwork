"""Menu builder: turn browser-use's selector_map into Jev candidate lists.

The menu is the action space System 1 chooses from. Code owns it entirely: the
model only ever picks an ``id`` (browser-use's ``selector_index``), and the
bridge re-validates that id against the same snapshot before dispatch.

Contract (stable; ``policy.py`` builds questions from these types):

* ``Candidate`` is one interactive element with the fields Jev needs to pick it.
* ``Menu`` holds the page summary, all candidates, the per-operation views, and
  what was omitted to fit the token budget so the model knows the menu is partial.
* ``build_menu`` enforces the budget: page text is trimmed first, then
  off-screen candidates, and the omissions are reported, never silent.
* ``group_candidates`` chunks a head that exceeds Jev's 255-option cap into
  group heads (fastbrowse's two-stage choice).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from browser_use.browser.views import BrowserStateSummary

Operation = Literal["click", "type", "select", "enter", "hover", "scroll"]
OPERATIONS: tuple[Operation, ...] = ("click", "type", "select", "enter", "hover", "scroll")

#: Jev 1.13 limits (docs.typesafe.ai/models): 255 options per Choice; 32k tokens for
#: state plus the longest question; 64k for the whole request.
MAX_CHOICE_OPTIONS = 255
STATE_TOKEN_BUDGET = 32_000
REQUEST_TOKEN_BUDGET = 64_000


@dataclass(frozen=True)
class Candidate:
    id: int
    label: str
    role: str
    operations: tuple[Operation, ...]
    value: str | None = None
    href: str | None = None
    input_type: str | None = None
    checked: bool | None = None
    selected: bool | None = None
    expanded: bool | None = None
    section: str | None = None
    offscreen: bool = False
    options: tuple[str, ...] | None = None

    def to_state(self) -> dict[str, Any]:
        """Compact JSON object for Jev state and Choice criteria (no None fields)."""
        out: dict[str, Any] = {"id": self.id, "label": self.label, "role": self.role, "operations": list(self.operations)}
        for key in ("value", "href", "input_type", "checked", "selected", "expanded", "section"):
            val = getattr(self, key)
            if val is not None:
                out[key] = val
        if self.options:
            out["options"] = list(self.options)
        if self.offscreen:
            out["offscreen"] = True
        return out


@dataclass(frozen=True)
class MenuBudget:
    state_tokens: int = STATE_TOKEN_BUDGET
    max_page_text_chars: int = 6_000
    chars_per_token: float = 3.0
    max_options: int = MAX_CHOICE_OPTIONS
    group_size: int = 40


@dataclass(frozen=True)
class Menu:
    url: str
    title: str
    page_text: str
    candidates: tuple[Candidate, ...]
    by_operation: dict[Operation, tuple[Candidate, ...]]
    omitted: dict[str, int] = field(default_factory=dict)
    tabs: tuple[dict[str, Any], ...] = ()
    estimated_tokens: int = 0

    def candidate(self, id: int) -> Candidate | None:
        for c in self.candidates:
            if c.id == id:
                return c
        return None


def build_menu(state: BrowserStateSummary, budget: MenuBudget | None = None) -> Menu:
    """Build the menu from a BrowserStateSummary. ``budget`` defaults to ``MenuBudget()``. Implemented in task C1."""
    raise NotImplementedError("C1")


def group_candidates(candidates: tuple[Candidate, ...], size: int = 40) -> tuple[tuple[Candidate, ...], ...]:
    """Chunk candidates for a two-stage group-then-element choice. Implemented in task C1."""
    raise NotImplementedError("C1")
