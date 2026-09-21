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

import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from browser_use.dom.enhanced_snapshot import _SENSITIVE_AUTOCOMPLETE_PREFIXES, _SENSITIVE_INPUT_TYPES

if TYPE_CHECKING:
    from browser_use.browser.views import BrowserStateSummary
    from browser_use.dom.views import EnhancedDOMTreeNode

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
    #: page_text is never trimmed below this many characters by budget enforcement.
    min_page_text_chars: int = 1_500


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


# ---------------------------------------------------------------------------
# Element classification
# ---------------------------------------------------------------------------

_TEXT_INPUT_TYPES = frozenset(
    {
        "", "text", "search", "email", "url", "tel", "password", "number", "date", "datetime-local",
        "month", "week", "time", "color",
    }
)
_CLICK_ONLY_INPUT_TYPES = frozenset({"checkbox", "radio", "button", "submit", "reset", "image", "file", "range"})
_CLICK_ROLES = frozenset(
    {
        "button", "link", "checkbox", "radio", "switch", "menuitem", "menuitemcheckbox", "menuitemradio",
        "tab", "option", "treeitem", "listbox", "menu", "menubar", "slider", "spinbutton", "img",
    }
)
_TEXT_ROLES = frozenset({"textbox", "searchbox", "combobox"})
_HEADING_TAGS = frozenset({"H1", "H2", "H3", "H4", "H5", "H6"})
_SKIP_TEXT_TAGS = frozenset({"SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE", "SVG", "HEAD"})
_LABEL_CAP = 80
_HREF_CAP = 200
_MAX_OPTIONS = 50
_WS = re.compile(r"\s+")


def _clean(text: str | None, cap: int | None = None) -> str:
    if not text:
        return ""
    t = _WS.sub(" ", text).strip()
    if cap is not None and len(t) > cap:
        t = t[: cap - 1].rstrip() + "…"
    return t


def _ax_props(node: EnhancedDOMTreeNode) -> dict[str, Any]:
    out: dict[str, Any] = {}
    ax = node.ax_node
    if ax is None or not ax.properties:
        return out
    for prop in ax.properties:
        name = getattr(prop.name, "value", prop.name)
        out[str(name)] = prop.value
    return out


def _tri(value: Any) -> bool | None:
    """Coerce an attribute/AX property to a tri-state bool."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    v = str(value).strip().lower()
    if v in ("true", "1", "checked", "selected", "expanded", "yes"):
        return True
    if v in ("false", "0", "no", "mixed"):
        return False
    if v == "":
        return True  # bare boolean attribute (checked, selected)
    return None


def _label(node: EnhancedDOMTreeNode, attrs: dict[str, str], tag: str) -> str:
    ax_name = node.ax_node.name if node.ax_node is not None else None
    for cand in (ax_name, attrs.get("aria-label")):
        if _clean(cand):
            return _clean(cand, _LABEL_CAP)
    text = _clean(node.get_all_children_text(), _LABEL_CAP)
    if text:
        return text
    for key in ("placeholder", "title", "alt"):
        if _clean(attrs.get(key)):
            return _clean(attrs.get(key), _LABEL_CAP)
    if tag in ("INPUT", "BUTTON") and attrs.get("type", "").lower() in ("submit", "button", "reset") and attrs.get("value"):
        return _clean(attrs["value"], _LABEL_CAP)
    if attrs.get("name"):
        return _clean(attrs["name"], _LABEL_CAP)
    if attrs.get("id"):
        return _clean(attrs["id"], _LABEL_CAP)
    return tag.lower()


def _operations(node: EnhancedDOMTreeNode, attrs: dict[str, str], tag: str, role: str) -> tuple[Operation, ...]:
    ops: list[Operation] = []
    input_type = attrs.get("type", "").lower() if tag == "INPUT" else ""
    contenteditable = attrs.get("contenteditable", "").lower() in ("", "true", "plaintext-only") and "contenteditable" in attrs
    if tag == "TEXTAREA" or contenteditable or (tag == "INPUT" and input_type in _TEXT_INPUT_TYPES) or role in _TEXT_ROLES:
        ops.extend(("type", "click", "enter"))
    elif tag == "SELECT":
        ops.extend(("select", "click"))
    else:
        # Checkbox/radio/button inputs, links, buttons, summaries, options and any other
        # element upstream judged interactive: click is the one operation that always applies.
        ops.append("click")
    if getattr(node, "is_scrollable", None):
        ops.append("scroll")
    haspopup = attrs.get("aria-haspopup", "").lower()
    if (haspopup and haspopup != "false") or role in ("menuitem", "menu") and node.children:
        ops.append("hover")
    # keep declaration order, unique
    seen: set[str] = set()
    return tuple(o for o in ops if not (o in seen or seen.add(o)))  # type: ignore[return-value]


def _section(node: EnhancedDOMTreeNode) -> str | None:
    """Nearest preceding heading: previous siblings' subtrees, then walk up, bounded."""
    budget = 400
    current: EnhancedDOMTreeNode | None = node
    while current is not None and budget > 0:
        parent = current.parent_node
        if parent is None:
            break
        siblings = parent.children
        try:
            idx = siblings.index(current)
        except ValueError:
            idx = 0
        for sib in reversed(siblings[:idx]):
            budget -= 1
            found = _last_heading_in(sib, 3)
            if found:
                return found
            if budget <= 0:
                break
        if parent.node_name.upper() in _HEADING_TAGS:
            return _clean(parent.get_all_children_text(), _LABEL_CAP) or None
        current = parent
    return None


def _last_heading_in(node: EnhancedDOMTreeNode, depth: int) -> str | None:
    if node.node_name.upper() in _HEADING_TAGS:
        return _clean(node.get_all_children_text(), _LABEL_CAP) or None
    if depth <= 0:
        return None
    for child in reversed(node.children):
        found = _last_heading_in(child, depth - 1)
        if found:
            return found
    return None


@dataclass(frozen=True)
class _Viewport:
    width: int
    height: int
    scroll_x: int = 0
    scroll_y: int = 0


def _offscreen(node: EnhancedDOMTreeNode, vp: _Viewport | None) -> bool:
    """True when the element's box lies entirely outside the current viewport.

    Uses document-coordinate bounds (``absolute_position`` includes iframe offsets)
    minus the scroll position. DOMSnapshot's ``clientRects`` is the content box
    relative to the border box, not viewport coordinates, so it is not used here.
    """
    if vp is None or not vp.width or not vp.height:
        return False
    r = node.absolute_position or (node.snapshot_node.bounds if node.snapshot_node is not None else None)
    if r is None:
        return False
    top = r.y - vp.scroll_y
    left = r.x - vp.scroll_x
    return top >= vp.height or top + r.height <= 0 or left >= vp.width or left + r.width <= 0


def _is_sensitive_input(tag: str, attrs: dict[str, str]) -> bool:
    """Same rule browser-use applies to live snapshot values; static ``value`` attributes need it too."""
    if tag != "INPUT":
        return False
    if attrs.get("type", "").lower() in _SENSITIVE_INPUT_TYPES:
        return True
    return attrs.get("autocomplete", "").lower().startswith(_SENSITIVE_AUTOCOMPLETE_PREFIXES)


def _select_options(node: EnhancedDOMTreeNode) -> tuple[str, ...] | None:
    out: list[str] = []
    stack = list(node.children)
    while stack and len(out) < _MAX_OPTIONS:
        child = stack.pop(0)
        if child.node_name.upper() == "OPTION":
            text = _clean(child.get_all_children_text(), _LABEL_CAP) or _clean(child.attributes.get("value"), _LABEL_CAP)
            if text:
                out.append(text)
        elif child.node_name.upper() == "OPTGROUP":
            stack[0:0] = child.children
    return tuple(out) or None


def candidate_from_node(index: int, node: EnhancedDOMTreeNode, vp: _Viewport | None = None) -> Candidate:
    attrs = dict(node.attributes or {})
    tag = node.node_name.upper()
    sensitive = _is_sensitive_input(tag, attrs)
    if sensitive:
        # browser-use strips live snapshot values for these inputs but a static value="" attribute
        # in the HTML still reaches node.attributes; the menu must never carry it.
        attrs.pop("value", None)
    ax_role = node.ax_node.role if node.ax_node is not None else None
    role = (attrs.get("role") or ax_role or tag.lower()).lower()
    ops = _operations(node, attrs, tag, role)
    props = _ax_props(node)
    input_type = attrs.get("type", "").lower() or None if tag == "INPUT" else None
    value = None
    if "type" in ops or tag == "SELECT":
        value = _clean(attrs.get("value"), _LABEL_CAP) or None
        if tag == "SELECT" and value is None:
            for child in node.children:
                if child.node_name.upper() == "OPTION" and _tri(child.attributes.get("selected")) is True:
                    value = _clean(child.get_all_children_text(), _LABEL_CAP) or None
                    break
    href = None
    if tag == "A" and attrs.get("href"):
        href = _clean(attrs["href"], _HREF_CAP)
    checked = _tri(props.get("checked")) if "checked" in props else _tri(attrs.get("checked")) if "checked" in attrs else None
    if checked is None and "aria-checked" in attrs:
        checked = _tri(attrs["aria-checked"])
    selected = _tri(props.get("selected")) if "selected" in props else _tri(attrs.get("selected")) if "selected" in attrs else None
    if selected is None and "aria-selected" in attrs:
        selected = _tri(attrs["aria-selected"])
    expanded = _tri(props.get("expanded")) if "expanded" in props else None
    if expanded is None and "aria-expanded" in attrs:
        expanded = _tri(attrs["aria-expanded"])
    return Candidate(
        id=index,
        label=_label(node, attrs, tag),
        role=role,
        operations=ops,
        value=value,
        href=href,
        input_type=input_type,
        checked=checked,
        selected=selected,
        expanded=expanded,
        section=_section(node),
        offscreen=_offscreen(node, vp),
        options=_select_options(node) if tag == "SELECT" else None,
    )


# ---------------------------------------------------------------------------
# Page text
# ---------------------------------------------------------------------------


def _page_text(root: EnhancedDOMTreeNode | None, cap: int) -> str:
    """Visible text of the page in document order, whitespace-collapsed, capped."""
    if root is None:
        return ""
    from browser_use.dom.views import NodeType

    parts: list[str] = []
    total = 0
    stack: list[EnhancedDOMTreeNode] = [root]
    while stack and total < cap:
        node = stack.pop()
        if node.node_type == NodeType.TEXT_NODE:
            parent = node.parent_node
            if parent is not None and parent.node_name.upper() in _SKIP_TEXT_TAGS:
                continue
            if parent is not None and parent.is_visible is False:
                continue
            t = _clean(node.node_value)
            if t:
                parts.append(t)
                total += len(t) + 1
            continue
        if node.node_name.upper() in _SKIP_TEXT_TAGS:
            continue
        kids = node.children_and_shadow_roots
        if node.content_document is not None:
            kids = [*kids, node.content_document]
        stack.extend(reversed(kids))
    text = " ".join(parts)
    return text[:cap]


def _root_of(state: BrowserStateSummary) -> EnhancedDOMTreeNode | None:
    simplified = getattr(state.dom_state, "_root", None)
    if simplified is not None:
        node = simplified.original_node
        while node.parent_node is not None:
            node = node.parent_node
        return node
    for node in state.dom_state.selector_map.values():
        while node.parent_node is not None:
            node = node.parent_node
        return node
    return None


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------


def estimate_tokens(page_text: str, candidates: tuple[Candidate, ...], chars_per_token: float) -> int:
    payload = json.dumps({"text": page_text, "elements": [c.to_state() for c in candidates]}, ensure_ascii=False)
    return int(len(payload) / chars_per_token) + 1


def _by_operation(candidates: tuple[Candidate, ...]) -> dict[Operation, tuple[Candidate, ...]]:
    return {op: tuple(c for c in candidates if op in c.operations) for op in OPERATIONS}


def build_menu(state: BrowserStateSummary, budget: MenuBudget | None = None) -> Menu:
    """Build the menu from a BrowserStateSummary. ``budget`` defaults to ``MenuBudget()``."""
    budget = budget or MenuBudget()
    info = state.page_info
    vp = (
        _Viewport(info.viewport_width, info.viewport_height, info.scroll_x, info.scroll_y) if info is not None else None
    )

    selector_map = state.dom_state.selector_map
    candidates = tuple(candidate_from_node(idx, node, vp) for idx, node in sorted(selector_map.items()))
    page_text = _page_text(_root_of(state), budget.max_page_text_chars)
    omitted: dict[str, int] = {}

    tokens = estimate_tokens(page_text, candidates, budget.chars_per_token)
    if tokens > budget.state_tokens:
        # 1. Trim page text down to the floor.
        over_chars = int((tokens - budget.state_tokens) * budget.chars_per_token)
        keep = max(budget.min_page_text_chars, len(page_text) - over_chars)
        if keep < len(page_text):
            omitted["page_text_chars"] = len(page_text) - keep
            page_text = page_text[:keep]
        tokens = estimate_tokens(page_text, candidates, budget.chars_per_token)
    if tokens > budget.state_tokens:
        # 2. Drop off-screen candidates, farthest-from-document-order-end first (i.e. from the tail).
        kept = list(candidates)
        dropped = 0
        for i in range(len(kept) - 1, -1, -1):
            if tokens <= budget.state_tokens:
                break
            if kept[i].offscreen:
                del kept[i]
                dropped += 1
                tokens = estimate_tokens(page_text, tuple(kept), budget.chars_per_token)
        if dropped:
            omitted["offscreen"] = dropped
        candidates = tuple(kept)
    if tokens > budget.state_tokens:
        # 3. Drop on-screen candidates from the end of the document (only once no off-screen ones remain).
        kept = list(candidates)
        dropped = 0
        while kept and tokens > budget.state_tokens:
            kept.pop()
            dropped += 1
            tokens = estimate_tokens(page_text, tuple(kept), budget.chars_per_token)
        if dropped:
            omitted["overflow"] = dropped
        candidates = tuple(kept)

    tabs = tuple(
        {"tab_id": getattr(t, "target_id", None), "url": t.url, "title": t.title} for t in (state.tabs or [])
    )
    return Menu(
        url=state.url,
        title=state.title,
        page_text=page_text,
        candidates=candidates,
        by_operation=_by_operation(candidates),
        omitted=omitted,
        tabs=tabs,
        estimated_tokens=tokens,
    )


def group_candidates(candidates: tuple[Candidate, ...], size: int = 40) -> tuple[tuple[Candidate, ...], ...]:
    """Chunk candidates for a two-stage group-then-element choice, preserving order."""
    if size <= 0:
        raise ValueError("size must be positive")
    return tuple(candidates[i : i + size] for i in range(0, len(candidates), size))
