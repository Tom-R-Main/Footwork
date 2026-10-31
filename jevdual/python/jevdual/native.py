"""Native desktop backend: Cua Driver window snapshots as System 1 menus, and a bridge that
dispatches a decision through the Driver with background delivery.

Cua Driver (MIT, ``external/cua/libs/cua-driver``; consumed as the ``cua-driver`` wheel) owns
capture, target identity, action dispatch and its ``ActionResult`` evidence. This module owns
what the browser side owns too: the menu is built by code, the model only ever picks an ``id``,
and the id is re-validated against the snapshot it came from before anything is dispatched
(RFC 3931's "one capture, one action, then reobserve" rule, which is also ours).

Contract:

* ``menu_from_snapshot`` turns a ``WindowStateOutput`` (or an equivalent dict, so recorded
  snapshots can be replayed offline) into a :class:`NativeMenu`: the ordinary :class:`Menu`
  plus the per-id ``element_token`` map and the snapshot identity.
* ``NativeBridge`` observes a window and executes one ``(operation, id)`` against the menu it
  was decided from, refusing a stale menu. Each :class:`NativeEffect` names its producer:
  SDK results preserve the Driver's account, while bounded AX routes retain their own
  acknowledgement and exact readback predicate. Neither establishes overall task correctness.

Role mapping is conservative: an element becomes a candidate only when the Driver gave it a
token (it advertises an action or a writable value) and its role maps to one of our operations.
The menu bar subtree is excluded by default: it is 110 of 155 elements on Calculator and its
items are reachable through ``invoke_menu`` when we add a ``menu`` operation.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
import math
import re
import sys
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jevdual.menu import (
    Candidate,
    ControlState,
    Menu,
    MenuBudget,
    Operation,
    estimate_tokens,
    peer_position,
)

log = logging.getLogger("jevdual.native")

#: AX role -> (menu role, operations). Roles absent here fall back to ``click`` when the element
#: advertises AXPress, and are skipped otherwise.
ROLE_MAP: dict[str, tuple[str, tuple[Operation, ...]]] = {
    "AXButton": ("button", ("click",)),
    "AXMenuButton": ("button", ("click",)),
    "AXPopUpButton": ("combobox", ("click",)),
    "AXComboBox": ("combobox", ("type", "click")),
    "AXCheckBox": ("checkbox", ("click",)),
    "AXRadioButton": ("radio", ("click",)),
    "AXTextField": ("textbox", ("type", "enter")),
    "AXSecureTextField": ("textbox", ("type", "enter")),
    "AXTextArea": ("textbox", ("type", "append")),
    "AXSearchField": ("searchbox", ("type", "enter")),
    "AXLink": ("link", ("click",)),
    "AXTab": ("tab", ("click",)),
    "AXMenuItem": ("menuitem", ("click",)),
    "AXMenuBarItem": ("menubar", ("click",)),
    "AXDisclosureTriangle": ("button", ("click",)),
    "AXIncrementor": ("spinbutton", ("click",)),
    "AXSlider": ("slider", ("click",)),
    "AXRow": ("option", ("click",)),
    "AXCell": ("option", ("click",)),
    "AXOutlineRow": ("treeitem", ("click",)),
    "AXScrollArea": ("scrollable", ("scroll",)),
    "AXTable": ("table", ("scroll",)),
    "AXOutline": ("tree", ("scroll",)),
    "AXList": ("list", ("scroll",)),
}
_SECTION_ROLES = frozenset(
    {"AXGroup", "AXToolbar", "AXTabGroup", "AXSheet", "AXDialog", "AXSplitGroup", "AXMenu", "AXMenuBarItem"}
)
_MENU_BAR_ROLES = frozenset({"AXMenuBar", "AXMenuBarItem", "AXMenu", "AXMenuItem"})
_TEXT_ROLES = frozenset({"textbox", "searchbox", "combobox"})
_LABEL_CAP = 80
_VALUE_CAP = 120
_INVISIBLE = re.compile("[" + "\u200e\u200f\u202a-\u202e\u2066-\u2069" + "]")
_WS = re.compile(r"\s+")
#: ``AXStaticText = "..."`` optionally followed by ``[actions=[...]]`` or other bracketed attributes
#: (Chrome renders those on web content; Calculator and TextEdit do not). The old end-anchored form
#: captured no web text at all, which blinded the verifier on every page (P0, 2026-09-25).
_STATIC_LINE = re.compile(r'AXStaticText = "(.*)"(?:\s+\[.*\])?\s*$')


def _clean(text: Any, cap: int | None = None) -> str:
    if text is None:
        return ""
    s = _WS.sub(" ", _INVISIBLE.sub("", str(text))).strip()
    if cap is not None and len(s) > cap:
        s = s[: cap - 1] + "…"
    return s


_WS_INLINE = re.compile(r"[ \t\r\f\v]+")


def _clean_multiline(text: Any, cap: int | None = None) -> str:
    """Like ``_clean`` but line breaks survive: a document's body is lines, and collapsing them made
    System 2 retype a two-line document ten times (Q10)."""
    if text is None:
        return ""
    raw = _INVISIBLE.sub("", str(text)).replace("\r\n", "\n")
    lines = [_WS_INLINE.sub(" ", ln).strip() for ln in raw.split("\n")]
    s = "\n".join(lines).strip("\n")
    if cap is not None and len(s) > cap:
        s = s[: cap - 1] + "…"
    return s


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


@dataclass(frozen=True)
class NativeVisualCapture:
    """Geometry supplied with the same explicit bound-window capture, not action authority."""

    path: str
    captured_at: str
    viewport: tuple[float, float, float, float]
    width: int
    height: int
    reported_scale: float | None


def _visual_capture(snapshot: Any, requested_path: str) -> tuple[NativeVisualCapture | None, str | None]:
    """Refuse geometry that the Driver did not bind to this exact PNG request."""
    if _get(snapshot, "screenshot_frame_valid") is not True:
        return None, "capture_frame_unverified"
    actual_path = _get(snapshot, "screenshot_file_path")
    if not actual_path or Path(str(actual_path)).resolve() != Path(requested_path).resolve():
        return None, "capture_path_mismatch"
    if not Path(requested_path).is_file():
        return None, "capture_png_missing"
    bounds = _get(snapshot, "window_bounds")
    if bounds is None:
        return None, "capture_viewport_missing"
    try:
        viewport = tuple(float(_get(bounds, name)) for name in ("x", "y", "width", "height"))
        width, height = int(_get(snapshot, "screenshot_width")), int(_get(snapshot, "screenshot_height"))
        scale = _get(snapshot, "screenshot_scale")
        scale = float(scale) if scale is not None else None
        if (
            not all(math.isfinite(value) for value in viewport)
            or viewport[2] <= 0
            or viewport[3] <= 0
            or width <= 0
            or height <= 0
            or (scale is not None and (not math.isfinite(scale) or scale <= 0))
        ):
            return None, "capture_geometry_invalid"
        return NativeVisualCapture(
            str(Path(requested_path).resolve()),
            datetime.now(UTC).isoformat(),
            viewport,
            width,
            height,
            scale,
        ), None
    except (TypeError, ValueError):
        return None, "capture_geometry_missing"


@dataclass(frozen=True)
class NativeMenu:
    """A menu plus what is needed to act on it: the token behind each id and the snapshot it came from."""

    menu: Menu
    tokens: dict[int, str]
    snapshot_id: str
    pid: int
    window_id: int
    app_name: str
    elements_complete: bool
    truncated: bool
    degraded: bool
    #: raw element rows kept for redaction-free diagnostics (role, label, frame); never sent to the model
    frames: dict[int, tuple[float, float, float, float]] = field(default_factory=dict)
    #: execution data, never rendered to a model or a trace: each non-secure text element's value as the
    #: Driver reports it (whole, not the 480-character preview; the Driver strips trailing whitespace, so
    #: the append route reads the exact value through ``jevdual.ax``) and each candidate's AX role
    values: dict[int, str] = field(default_factory=dict)
    ax_roles: dict[int, str] = field(default_factory=dict)
    #: ids of elements inside web content (an AXWebArea ancestor): WebKit ignores AXValue writes there
    web: frozenset[int] = frozenset()
    visual_capture: NativeVisualCapture | None = None
    visual_capture_error: str | None = None
    #: Pre-pruning address bars for scope checks; deduplication cannot prove uniqueness.
    scope_address_bars: tuple[tuple[int, str | None], ...] | None = None
    chrome_scope: Any = None

    def token(self, id: int) -> str | None:
        return self.tokens.get(id)


def _checked(value: Any) -> ControlState:
    """An AX checkbox/radio/switch value: 0 off, 1 on, 2 mixed (NSControlStateValueMixed)."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in ("1", "true", "on", "checked"):
        return True
    if s in ("0", "false", "off", "unchecked"):
        return False
    if s in ("2", "mixed"):
        return "mixed"
    return None


def _in_menu_bar(el: Any, by_index: dict[int, Any]) -> bool:
    cur = el
    seen = 0
    while cur is not None and seen < 64:
        if _get(cur, "role") in _MENU_BAR_ROLES:
            return True
        parent = _get(cur, "parent_index")
        cur = by_index.get(int(parent)) if parent is not None else None
        seen += 1
    return False


def _section_of(el: Any, by_index: dict[int, Any]) -> str | None:
    parent = _get(el, "parent_index")
    seen = 0
    while parent is not None and seen < 64:
        p = by_index.get(int(parent))
        if p is None:
            return None
        if _get(p, "role") in _SECTION_ROLES:
            label = _clean(_get(p, "label"), 60)
            if label:
                return label
        parent = _get(p, "parent_index")
        seen += 1
    return None


def _offscreen(frame: Any, bounds: Any) -> bool:
    if frame is None or bounds is None:
        return False
    fx, fy, fw, fh = (_get(frame, k) for k in ("x", "y", "w", "h"))
    bx, by, bw, bh = (_get(bounds, k) for k in ("x", "y", "width", "height"))
    if None in (fx, fy, fw, fh, bx, by, bw, bh):
        return False
    return fx + fw <= bx or fy + fh <= by or fx >= bx + bw or fy >= by + bh


_TEXT_AX_ROLES = frozenset({"AXTextArea", "AXTextField", "AXComboBox", "AXSearchField"})


def _page_text(tree_markdown: str | None, elements: list[Any], cap: int) -> str:
    """Static text in reading order, from the markdown the Driver renders (leaf text carries no
    token, so it is not in ``elements``), then the current value of every text field and area
    (a document's body is the value of its AXTextArea, not a static-text leaf)."""
    lines: list[str] = []
    for raw in (tree_markdown or "").splitlines():
        m = _STATIC_LINE.search(raw.strip())
        if m:
            t = _clean(m.group(1).replace('\\"', '"'))
            if t:
                lines.append(t)
    for el in elements:
        if _get(el, "role") in _TEXT_AX_ROLES and _get(el, "role") != "AXSecureTextField":
            v = (
                _clean_multiline(_get(el, "value"))
                if _get(el, "role") == "AXTextArea"
                else _clean(_get(el, "value"))
            )
            if v and v not in lines:
                lines.append(v)
    out = "\n".join(lines)
    return out[:cap]


#: candidates a native menu offers Jev at most; beyond this the tail is dropped (``omitted["cap"]``).
#: A Chrome window offered 296 and Jev refused the request as too large twice per step.
NATIVE_MENU_CAP = 160
#: same-key toggles kept per key: a table of unlabelled checkboxes (labelled by their raw value) must
#: not crowd the window's other controls past the cap
TOGGLE_REPEATS_KEPT = 4


def _prune(
    candidates: list[Candidate],
    tokens: dict[int, str],
    frames: dict[int, tuple[float, float, float, float]],
    omitted: dict[str, int],
    budget: MenuBudget,
) -> tuple[list[Candidate], dict[int, str], dict[int, tuple[float, float, float, float]]]:
    """Drop what System 1 cannot choose between: a control whose label is only its role (``button
    'button'``) unless it is a text field, and repeats of the same (role, label, value, section) beyond
    the first (a page with 27 identical "More actions" buttons offers one). A toggle that reports its
    state is kept even when repeated, when its whole group is: two "Enabled" switches are two settings,
    and dropping the second hid its change from the effect diff. The ``do`` and ``_live`` identity
    checks tell repeats apart by their position among the offered peers, which only holds when every
    peer is offered, so a group larger than ``TOGGLE_REPEATS_KEPT`` or cut by the cap offers its first
    member only, as any other repeat. Then cap the count."""

    def key_of(c: Candidate) -> tuple[str, str, str | None, str | None]:
        return (c.role, c.label, c.value, c.section)

    named = []
    for c in candidates:
        if c.label == c.role and c.role not in _TEXT_ROLES:
            omitted["unnamed"] = omitted.get("unnamed", 0) + 1
            continue
        named.append(c)
    group: dict[tuple[str, str, str | None, str | None], int] = {}
    for c in named:
        group[key_of(c)] = group.get(key_of(c), 0) + 1

    def dedupe(
        cands: list[Candidate], whole: set[tuple[str, str, str | None, str | None]]
    ) -> list[Candidate]:
        out: list[Candidate] = []
        seen: set[tuple[str, str, str | None, str | None]] = set()
        for c in cands:
            stateful = c.checked is not None or c.pressed is not None or c.expanded is not None
            if key_of(c) in seen and not (stateful and key_of(c) in whole):
                omitted["duplicate"] = omitted.get("duplicate", 0) + 1
                continue
            seen.add(key_of(c))
            out.append(c)
        return out

    whole = {k for k, n in group.items() if n <= TOGGLE_REPEATS_KEPT}
    kept = dedupe(named, whole)
    if len(kept) > NATIVE_MENU_CAP:
        # a repeated group the cap would cut stops being offered whole: keep its first member only
        tail = {key_of(c) for c in kept[NATIVE_MENU_CAP:]}
        if tail & whole:
            omitted.pop("duplicate", None)
            kept = dedupe(named, whole - tail)
    if len(kept) > NATIVE_MENU_CAP:
        omitted["cap"] = len(kept) - NATIVE_MENU_CAP
        kept = kept[:NATIVE_MENU_CAP]
    ids = {c.id for c in kept}
    return kept, {i: t for i, t in tokens.items() if i in ids}, {i: f for i, f in frames.items() if i in ids}


_TREE_LINE = re.compile(r"^(\s*)- \[(\d+)\] (AX\w+)(.*)$")


def child_text_labels(tree_markdown: str | None) -> dict[int, str]:
    """Element index -> the first static-text leaf beneath it, for controls that carry no label of
    their own (System Settings' sidebar rows, Finder's sidebar: an AXRow whose only text is a child
    AXStaticText the Driver renders in the markdown but not in ``elements``)."""
    out: dict[int, str] = {}
    stack: list[tuple[int, int]] = []  # (indent, element index) of open ancestors
    for raw in (tree_markdown or "").splitlines():
        m = _TREE_LINE.match(raw)
        if not m:
            continue
        indent, idx, role = len(m.group(1)), int(m.group(2)), m.group(3)
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if role == "AXStaticText":
            t = _STATIC_LINE.search(raw.strip())
            text = _clean(t.group(1).replace('\\"', '"')) if t else ""
            if text:
                for _, anc in stack:
                    out.setdefault(anc, text)
        stack.append((indent, idx))
    return out


def menu_from_snapshot(
    snapshot: Any,
    *,
    budget: MenuBudget | None = None,
    include_menu_bar: bool = False,
    linux_text: dict[int, dict[str, Any]] | None = None,
) -> NativeMenu:
    """Build the System 1 menu from a Driver ``get_window_state`` result (SDK object or dict)."""
    b = budget or MenuBudget()
    elements = list(_get(snapshot, "elements") or [])
    by_index: dict[int, Any] = {}
    for el in elements:
        idx = _get(el, "element_index")
        if idx is not None:
            by_index[int(idx)] = el
    bounds = _get(snapshot, "window_bounds")
    child_labels = child_text_labels(_get(snapshot, "tree_markdown"))
    candidates: list[Candidate] = []
    tokens: dict[int, str] = {}
    frames: dict[int, tuple[float, float, float, float]] = {}
    values: dict[int, str] = {}
    ax_roles: dict[int, str] = {}
    web: set[int] = set()
    omitted: dict[str, int] = {}
    for el in elements:
        token = _get(el, "element_token")
        idx = _get(el, "element_index")
        if not token or idx is None:
            continue
        ax_role = str(_get(el, "role") or "")
        linux_role = linux_text is not None and not ax_role.startswith("AX")
        if ax_role == "AXWindow":
            continue
        if not include_menu_bar and _in_menu_bar(el, by_index):
            omitted["menu_bar"] = omitted.get("menu_bar", 0) + 1
            continue
        actions = {str(a) for a in (_get(el, "actions") or ())}
        mapped = ROLE_MAP.get(ax_role)
        text_proof = (linux_text or {}).get(int(idx), {})
        if linux_role:
            from jevdual.linux_projection import project_element

            mapped = project_element(
                ax_role, actions,
                editable=text_proof.get("writable") is True,
                multiline=text_proof.get("multiline") is True,
            )
            if mapped is None:
                omitted["unmapped_role"] = omitted.get("unmapped_role", 0) + 1
                continue
        if mapped is None and ax_role == "AXImage" and "AXOpen" in actions:
            # a Finder icon-view item: an image that opens (P0 breadth, 2026-09-25); clicking selects it
            mapped = ("file", ("click",))
        if mapped is None:
            if "AXPress" not in actions:
                omitted["unmapped_role"] = omitted.get("unmapped_role", 0) + 1
                continue
            mapped = (ax_role.removeprefix("AX").lower() or "element", ("click",))
        role, ops = mapped
        if not linux_role and role == "menuitem" and "AXPress" not in actions and "AXPick" not in actions:
            omitted["inert_menu_item"] = omitted.get("inert_menu_item", 0) + 1
            continue
        if _get(el, "enabled") is False:
            omitted["disabled"] = omitted.get("disabled", 0) + 1
            continue
        raw_value = text_proof.get("value") if linux_role else _get(el, "value")
        label = _clean(_get(el, "label"), _LABEL_CAP)
        if not label:
            label = _clean(_get(el, "value_description"), _LABEL_CAP)
        if not label and role not in _TEXT_ROLES:
            label = _clean(child_labels.get(int(idx)), _LABEL_CAP)
        if not label and role not in _TEXT_ROLES:
            label = _clean(raw_value, _LABEL_CAP)
        if not label:
            label = role
        sensitive = ax_role == "AXSecureTextField" or (linux_role and ax_role.casefold() == "password text")
        multiline = ax_role == "AXTextArea" or (linux_role and text_proof.get("multiline") is True)
        if role in _TEXT_ROLES and raw_value not in (None, "") and label == _clean(raw_value, _LABEL_CAP):
            label = "text area" if multiline else role  # the Driver echoed the content as the label
        value: str | None = None
        if role in _TEXT_ROLES and not sensitive and raw_value not in (None, ""):
            value = (
                _clean_multiline(raw_value, _VALUE_CAP * 4) if multiline else _clean(raw_value, _VALUE_CAP)
            )
        checked = _checked(raw_value) if role in ("checkbox", "radio", "switch") else None
        if linux_role and role in ("checkbox", "radio"):
            checked = _get(el, "selected")
        frame = _get(el, "frame")
        cand = Candidate(
            id=int(idx),
            label=label,
            role=role,
            operations=ops,
            value=value,
            input_type="password" if sensitive else ("textarea" if multiline else None),
            has_value=(raw_value not in (None, "")) if sensitive else None,
            checked=checked,
            selected=_get(el, "selected"),
            section=_section_of(el, by_index),
            offscreen=_offscreen(frame, bounds),
        )
        candidates.append(cand)
        tokens[cand.id] = str(token)
        ax_roles[cand.id] = ax_role
        if _get(el, "in_web_content"):
            web.add(cand.id)
        if role in _TEXT_ROLES and not sensitive and raw_value is not None:
            values[cand.id] = str(raw_value)
        if frame is not None:
            fx, fy, fw, fh = (_get(frame, k) for k in ("x", "y", "w", "h"))
            if None not in (fx, fy, fw, fh):
                frames[cand.id] = (float(fx), float(fy), float(fw), float(fh))

    scope_address_bars = tuple(
        (candidate.id, values.get(candidate.id))
        for candidate in candidates
        if candidate.role in ("textbox", "searchbox")
        and any(hint in candidate.label.casefold() for hint in ADDRESS_BAR_HINTS)
    )
    candidates, tokens, frames = _prune(candidates, tokens, frames, omitted, b)
    kept = {c.id for c in candidates}
    values = {i: v for i, v in values.items() if i in kept}
    ax_roles = {i: r for i, r in ax_roles.items() if i in kept}
    app_name = str(_get(snapshot, "app_name") or "")
    title = _clean(_get(snapshot, "window_title"), 120)
    page_text = _page_text(_get(snapshot, "tree_markdown"), elements, b.max_page_text_chars)
    if linux_text is not None and any(not str(_get(e, "role") or "").startswith("AX") for e in elements):
        from jevdual.linux_static_text import project_static_text

        # Passive display text is an explicitly marked preview. Editable values
        # come from independent complete reads, never CUA's 4096-char preview.
        static = project_static_text(_get(snapshot, "tree_markdown"), max_chars=b.max_page_text_chars)
        parts = [*static.lines, *(str(p["value"]) for p in linux_text.values() if p.get("value"))]
        page_text = "\n".join(parts)
        if static.lines:
            omitted["static_text_preview"] = 1
        if static.ambiguous_records:
            omitted["static_text_ambiguous"] = static.ambiguous_records
        if static.input_truncated or static.output_truncated:
            omitted["text_truncated"] = 1
        if len(page_text) > b.max_page_text_chars:
            omitted["text_truncated"] = 1
            page_text = page_text[:b.max_page_text_chars]
    if not _get(snapshot, "elements_complete", True):
        omitted["elements_incomplete"] = 1
    if _get(snapshot, "truncated"):
        omitted["truncated"] = 1
    by_op: dict[Operation, tuple[Candidate, ...]] = {}
    for c in candidates:
        for op in c.operations:
            by_op.setdefault(op, ())
            by_op[op] = by_op[op] + (c,)
    cands = tuple(candidates)
    menu = Menu(
        url=f"app://{app_name}",
        title=title or app_name,
        page_text=page_text,
        candidates=cands,
        by_operation=by_op,
        omitted=omitted,
        estimated_tokens=estimate_tokens(page_text, cands, b.chars_per_token),
        full_text=page_text,
    )
    return NativeMenu(
        menu=menu,
        tokens=tokens,
        snapshot_id=str(_get(snapshot, "snapshot_id") or ""),
        pid=int(_get(snapshot, "pid") or 0),
        window_id=int(_get(snapshot, "window_id") or 0),
        app_name=app_name,
        elements_complete=bool(_get(snapshot, "elements_complete", True)),
        truncated=bool(_get(snapshot, "truncated") or False),
        degraded=bool(_get(snapshot, "degraded") or False),
        frames=frames,
        values=values,
        ax_roles=ax_roles,
        web=frozenset(i for i in web if i in kept),
        scope_address_bars=scope_address_bars,
    )


# ---------------------------------------------------------------------------
# Execution through the Driver
# ---------------------------------------------------------------------------


class NativeBridgeError(Exception):
    def __init__(self, reason: str, message: str, *, dispatched: bool = False):
        super().__init__(message)
        self.reason = reason
        self.dispatched = dispatched


def accessibility_status() -> str:
    """Read the current host permission without prompting or changing it."""
    from jevdual.capability.setup import permission_status

    return permission_status()["accessibility"]


def require_accessibility() -> None:
    status = accessibility_status()
    if sys.platform == "linux" and status == "not_checked":
        # Linux has no macOS permission API. Actual scoped CUA/AT-SPI reads
        # qualify availability; environment presence never grants it.
        return
    if status not in ("granted", "unsupported"):
        raise NativeBridgeError(
            "accessibility_not_granted" if status == "not_granted" else "accessibility_unavailable",
            "Native observation requires Accessibility permission for the process hosting Footwork. "
            "Check System Settings > Privacy & Security > Accessibility, then run footwork doctor "
            "from the same host before retrying.",
        )


@dataclass(frozen=True)
class NativeEffect:
    """One native producer's account of an action and its declared local predicate.
    ``effect`` uses confirmed, partial, unverifiable, suspected_noop or refused.
    ``delivery_basis`` identifies the SDK or source-qualified AX route.

    ``delivery`` is how the bridge declared it would reach the target before sending anything
    (background, foreground, desktop; see ``jevdual.posture``) and ``driver_delivery`` how the Driver says
    it did. ``dispatched`` is False when nothing was sent: the posture refused the step
    (``requires_foreground``, ``requires_desktop``, ``human_active``) or the Driver refused before
    delivering (``same_pid_keyboard_ambiguity``). ``foreground`` carries the front app before and after a
    foreground step."""

    operation: str
    target: int
    label: str
    effect: str
    route: str | None = None
    evidence: tuple[str, ...] = ()
    summary: str = ""
    error_code: str | None = None
    delivery: str | None = None
    driver_delivery: str | None = None
    dispatched: bool = True
    foreground: dict[str, Any] | None = None
    #: package G: after a save, the file the window names read against its text (``save_readback``)
    readback: dict[str, Any] | None = None
    #: Qualified acknowledged-input lower bound; uncounted SDK input is excluded.
    #: Dispatched alone only means input was attempted.
    delivered_count: int | None = None
    #: Producer of qualified delivery; an attempted input has basis ``unknown``.
    delivery_basis: str = "unknown"
    #: Exact AX current-state readback, separate from disk/window persistence.
    field_readback: dict[str, Any] | None = None
    #: Source-qualified non-text UI predicates, never task-correctness claims.
    native_readback: dict[str, Any] | None = None

    @property
    def ok(self) -> bool:
        return self.effect in ("confirmed", "partial", "unverifiable")

    def to_record(self) -> dict[str, Any]:
        rec = {
            "operation": self.operation,
            "target": self.target,
            "label": self.label,
            "effect": self.effect,
            "route": self.route,
            "evidence": list(self.evidence),
            "summary": self.summary[:200],
            "error_code": self.error_code,
            "delivery": self.delivery,
            "driver_delivery": self.driver_delivery,
            "dispatched": self.dispatched,
            "delivered_count": self.delivered_count,
            "delivery_basis": self.delivery_basis,
        }
        if self.foreground is not None:
            rec["foreground"] = dict(self.foreground)
        if self.field_readback is not None:
            rec["field_readback"] = dict(self.field_readback)
        if self.native_readback is not None:
            rec["native_readback"] = dict(self.native_readback)
        return rec


def _enum_name(v: Any) -> str | None:
    if v is None:
        return None
    name = getattr(v, "name", None)
    return str(name).lower() if name is not None else str(v).lower()


def effect_from_action_result(operation: str, target: int, label: str, result: Any) -> NativeEffect:
    """Map an SDK ``ActionResult`` (or a ``ToolResult`` carrying one) to :class:`NativeEffect`."""
    action = getattr(result, "action", None) or result
    effect = _enum_name(getattr(action, "effect", None)) or "unverifiable"
    route = _enum_name(getattr(action, "route", None))
    evidence = tuple(
        f"{_enum_name(getattr(e, 'kind', None))}: {getattr(e, 'detail', '') or ''}".strip()
        for e in (getattr(action, "evidence", None) or ())
    )
    summary = str(getattr(action, "summary", None) or getattr(result, "text", "") or "")
    code = getattr(result, "error_code", None) or getattr(getattr(action, "error", None), "code", None)
    delivered = _enum_name(getattr(getattr(action, "delivery", None), "mode", None))
    if getattr(result, "is_error", False) and effect != "refused":
        # An error reply alone cannot establish that input was never delivered.
        effect = "unverifiable"
    count = getattr(getattr(action, "delivery", None), "delivered_count", None)
    count = count if type(count) is int and count >= 0 else None
    if effect == "refused" and count is not None and count > 0:
        effect = "unverifiable"
    return NativeEffect(
        operation,
        target,
        label,
        effect,
        route,
        evidence,
        summary,
        code,
        driver_delivery=delivered,
        dispatched=effect != "refused",
        delivered_count=count,
        delivery_basis=(
            "qualified_gate"
            if effect == "refused"
            else "sdk_delivery_count"
            if count is not None and count > 0
            else "unknown"
        ),
    )


_MENU_NOT_PRESSED = frozenset({"not_key", "menu_missing", "menu_ambiguous", "menu_disabled"})
#: what a menu press through AX returns: delivered, no readback (the receipt's reobservation decides)
_PRESSED = type(
    "Pressed",
    (),
    {"action": None, "text": "menu item pressed through AX", "is_error": False, "error_code": None},
)()

#: the Driver's refusal when a process owns several eligible windows and a process-scoped key event
#: cannot be proven to reach the bound one (measured 2026-09-25: an element token does not lift it)
AMBIGUITY = "same_pid_keyboard_ambiguity"
_TEXT_EDIT_ROLES = frozenset({"AXTextArea", "AXTextField", "AXComboBox", "AXSearchField"})


def _linux_foreground_no_send(outcome: Any) -> bool:
    """Recognize the pinned X11 activation gate, never an opaque error message.

    platform-linux input/foreground.rs returns CODE_UNAVAILABLE before its
    input body; tools/impl_.rs input_error_result publishes the core fields.
    recovery_hint.rs then adds optional advisory hint/next_call metadata;
    neither field is interpreted or executed here.
    Timeout and post-dispatch failures retain uncertain delivery semantics.
    """
    if (getattr(outcome, "action", None) is not None
            or getattr(outcome, "is_error", None) is not True
            or getattr(outcome, "error_code", None) != "foreground_unavailable"):
        return False
    structured = getattr(outcome, "structured_json", None)
    if not isinstance(structured, str):
        return False
    try:
        record = json.loads(structured)
    except ValueError:
        return False
    return (isinstance(record, dict)
            and {"code", "detail", "effect", "suggestion"} <= set(record)
            <= {"code", "detail", "effect", "suggestion", "hint", "next_call"}
            and record["code"] == "foreground_unavailable" and record["effect"] == "none"
            and isinstance(record["detail"], str) and isinstance(record["suggestion"], str))


def _keyboard_ambiguity_no_send(outcome: Any, effect: NativeEffect, pid: int, window_id: int) -> bool:
    if isinstance(outcome, BaseException) or effect.error_code != AMBIGUITY:
        return False
    if not effect.dispatched:
        return True
    if getattr(outcome, "action", None) is not None or not getattr(outcome, "is_error", False):
        return False
    # The pinned SDK leaves action=None for error replies. Its native background
    # gate publishes this exact target-bound shape before running an actuator.
    structured = getattr(outcome, "structured_json", None)
    try:
        record = json.loads(structured) if isinstance(structured, str) else structured
    except (TypeError, ValueError):
        return False
    return (
        isinstance(record, dict)
        and set(record) <= {"code", "effect", "pid", "window_id", "reason", "escalation"}
        and record.get("code") == AMBIGUITY
        and record.get("effect") == "refused"
        and all(
            type(record.get(key)) is int and record[key] == expected
            for key, expected in (("pid", pid), ("window_id", window_id))
        )
    )


def _norm_tail(s: str) -> str:
    """The comparison the Driver's value supports: it strips trailing whitespace."""
    return s.rstrip()


@dataclass(frozen=True)
class AppendPrecondition:
    """An exact AX baseline for callers that have independently qualified a field."""

    value: str
    role: str
    frame: tuple[float, float, float, float]
    document: str | None = None
    resource_check: Callable[[], bool] | None = field(default=None, repr=False, compare=False)


def preview_menu_readback(path: list[str], before: Any, after: Any) -> dict[str, Any] | None:
    """Qualify only the named Preview UI transition, independently of image correctness."""
    if not isinstance(before, dict) or not isinstance(after, dict):
        return None
    for item in (before, after):
        identity = item.get("identity")
        if (
            not isinstance(item.get("document"), str)
            or not Path(item["document"]).is_absolute()
            or not isinstance(identity, dict)
            or set(identity) != {"device", "inode"}
            or any(type(value) is not int or value < 0 for value in identity.values())
            or any(type(item.get(key)) is not int or item[key] <= 0 for key in ("pid", "window_id"))
            or not isinstance(item.get("undo"), list)
            or any(not isinstance(title, str) for title in item["undo"])
        ):
            return None
    if (
        not before.get("document")
        or not before.get("identity")
        or before.get("document") != after.get("document")
        or before["pid"] != after["pid"]
        or before["window_id"] != after["window_id"]
    ):
        return None
    predicate = None
    if path in (["Tools", "Rotate Left"], ["Tools", "Rotate Right"]):
        undo = f"Undo {path[1]}"
        if (
            before.get("identity") == after.get("identity")
            and undo not in before.get("undo", [])
            and undo in after.get("undo", [])
        ):
            predicate = "preview_rotate_" + path[1].split()[-1].lower() + "_ui_transition"
    elif path == ["File", "Save"] and before.get("edited") is True and after.get("edited") is False:
        predicate = "preview_save_ui_transition"
    elif (
        path == ["File", "Save"]
        and all(
            isinstance(item.get("sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
            for item in (before, after)
        )
        and before["sha256"] != after["sha256"]
    ):
        predicate = "preview_save_file_transition"
    if predicate is None:
        return None
    return {
        "schema_version": 1,
        "producer": "footwork.ax.preview",
        "predicate": predicate,
        "before": before,
        "after": after,
    }


class NativeBridge:
    """Observe one native window through the Driver and execute menu decisions against it.

    Every dispatch declares its delivery and asks the session's :class:`~jevdual.posture.ExecutionPolicy`
    before anything is sent; the default is ``background_only``. With ``live_check`` every element action
    first reobserves and requires the target to be the same element in the same state (identity and
    precondition), then acts on the fresh token."""

    def __init__(
        self,
        driver: Any,
        pid: int,
        window_id: int,
        *,
        session: str | None = None,
        policy: Any = None,
        live_check: bool = False,
        ax: Any = None,
        observation_guard: Callable[[NativeMenu], None] | None = None,
        finder_scope: dict[str, Any] | None = None,
    ):
        from jevdual.posture import ExecutionPolicy

        self.driver = driver
        self.pid = pid
        self.window_id = window_id
        # CUA's screenshot file authorization rebuilds the request from public
        # arguments. Its implicit-direct binding is lost at that boundary;
        # an explicit runtime-scoped session survives and binds the capture.
        self.session = session or f"footwork-native-{uuid.uuid4().hex}"
        self.policy = policy if policy is not None else ExecutionPolicy("background_only")
        self.live_check = live_check
        self.observation_guard = observation_guard
        self.finder_scope = finder_scope
        self._foreground_inputs = 0
        self._ax = ax
        self.last: NativeMenu | None = None
        self.dispatches = 0

    @property
    def ax(self) -> Any:
        if self._ax is None:
            if sys.platform == "linux":
                from jevdual import linux_ax as _ax
            else:
                from jevdual import ax as _ax

            self._ax = _ax
        return self._ax

    async def observe(
        self,
        *,
        query: str | None = None,
        max_elements: int | None = None,
        include_menu_bar: bool = False,
        budget: MenuBudget | None = None,
        screenshot_path: str | None = None,
    ) -> NativeMenu:
        from jevdual.effectors import require_available

        require_available("desktop")
        from jevdual.effectors.cua import window_state_input

        if self.policy.locked():
            # nothing on a locked screen can be observed, so nothing can be decided or sent: stop and say why
            raise NativeBridgeError("screen_locked", "the screen is locked; unlock it to continue")
        require_accessibility()
        # Scope must be checked before retaining pixels. This bounded route uses
        # AX observations only rather than capture a possibly changed page.
        capture_path = screenshot_path if self.observation_guard is None else None
        snap = await self.driver.get_window_state(
            window_state_input(
                pid=self.pid,
                window_id=self.window_id,
                session=self.session,
                query=query,
                include_accessibility_tree=True,
                include_screenshot=capture_path is not None,
                screenshot_out_file=capture_path,
                max_elements=max_elements,
                max_depth=None,
                max_dimension=None,
                max_image_dimension=None,
                # Compact SDK defaults omit the structured elements and static-text detail.
                full_output=True,
            )
        )
        self.last = None
        linux_text = None
        if sys.platform == "linux":
            from jevdual.linux_projection import PASSWORD_ROLES, TEXT_ROLES, normalize_role

            linux_text = {}
            deadline = asyncio.get_running_loop().time() + 12.0
            attempts = 0
            for element in _get(snap, "elements") or []:
                role = str(_get(element, "role") or "")
                index = _get(element, "element_index")
                frame = _get(element, "frame")
                if (normalize_role(role) not in TEXT_ROLES or normalize_role(role) in PASSWORD_ROLES
                        or index is None or frame is None or not _get(element, "element_token")):
                    continue
                if attempts >= 32 or asyncio.get_running_loop().time() >= deadline:
                    linux_text[int(index)] = {}
                    continue
                attempts += 1

                def qualify(element_role: str = role, element_frame: Any = frame) -> dict[str, Any]:
                    coordinates = [_get(element_frame, k) for k in ("x", "y", "w", "h")]
                    if any(value is None for value in coordinates):
                        return {}
                    target = self.ax.resolve(self.pid, self.window_id, element_role, self.ax.Frame(*coordinates))
                    proof = self.ax.text_capabilities(target)
                    if proof["readable"]:
                        proof["value"] = self.ax.value(target)
                    return proof

                try:
                    linux_text[int(index)] = await asyncio.to_thread(qualify)
                except self.ax.AXError:
                    linux_text[int(index)] = {}
        observed = menu_from_snapshot(
            snap, budget=budget, include_menu_bar=include_menu_bar, linux_text=linux_text
        )
        if linux_text is not None:
            # Linux window managers may report the desktop ID as the app name.
            # Resolve its display name only through a unique same-process row;
            # an unrelated name or different PID must still fail caller scope.
            if (observed.pid == self.pid and "." in observed.app_name
                    and callable(getattr(self.driver, "list_apps", None))):
                from jevdual.effectors.cua import list_apps_input

                apps = (await self.driver.list_apps(list_apps_input())).apps
                matches = [app for app in apps if app.pid == self.pid and observed.app_name.casefold() in {
                    str(app.name or "").casefold(), str(getattr(app, "bundle_id", None) or "").casefold()
                }]
                if len(matches) == 1 and matches[0].name:
                    observed = dataclasses.replace(
                        observed, app_name=matches[0].name,
                        menu=dataclasses.replace(observed.menu, url=f"app://{matches[0].name}"),
                    )
            unavailable = sum("value" not in proof for proof in linux_text.values())
            if unavailable:
                observed.menu.omitted["exact_text_unqualified"] = unavailable
        if self.observation_guard is not None and observed.app_name in {"Chrome", "Google Chrome"}:
            from jevdual.chrome_scope import capture

            observed = dataclasses.replace(
                observed, chrome_scope=capture(observed.pid, observed.window_id).to_record()
            )
        if self.observation_guard is not None:
            self.observation_guard(observed)
        if capture_path is not None:
            capture, error = _visual_capture(snap, capture_path)
            observed = dataclasses.replace(observed, visual_capture=capture, visual_capture_error=error)
        elif screenshot_path is not None:
            observed = dataclasses.replace(observed, visual_capture_error="scope_guard_withheld_pixels")
        self.last = observed
        return self.last

    def _target(self) -> Any:
        from jevdual.effectors.cua import window_target

        return window_target(pid=self.pid, window_id=self.window_id)

    def _require_fresh(self, nm: NativeMenu, id: int) -> tuple[Candidate, str]:
        if self.last is None or nm.snapshot_id != self.last.snapshot_id:
            raise NativeBridgeError(
                "stale",
                f"decision came from snapshot {nm.snapshot_id!r}, current is "
                f"{getattr(self.last, 'snapshot_id', None)!r}; reobserve",
            )
        cand = nm.menu.candidate(id)
        token = nm.token(id)
        if cand is None or token is None:
            raise NativeBridgeError("target_missing", f"id {id} is not on the menu from {nm.snapshot_id}")
        return cand, token

    async def _live(self, nm: NativeMenu, id: int, operation: str) -> tuple[NativeMenu, int]:
        """Reobserve and find the decided element again: the same (role, label, section), its id kept
        when it still names it, else the unique element that does. A text field whose value changed, a
        checkbox whose state changed, or an element that is gone or no longer unique refuses the step:
        the person or another agent changed the window since the decision."""
        cand = nm.menu.candidate(id)
        assert cand is not None
        fresh = await self.observe()
        key = (cand.role, cand.label, cand.section)
        same = fresh.menu.candidate(id)
        decided = peer_position(nm.menu.candidates, id)
        if decided is not None and decided[1] > 1:
            # one of several same-label controls (repeated toggles are kept): the id alone may now name
            # a sibling, so the decided one is the same position among the same number of peers
            peers = [c for c in fresh.menu.candidates if (c.role, c.label, c.section) == key]
            if len(peers) != decided[1]:
                raise NativeBridgeError(
                    "target_changed",
                    f"[{id}] {cand.label!r} was {decided[0] + 1} of {decided[1]} alike; the window now has "
                    f"{len(peers)}",
                )
            hit = peers[decided[0]]
        elif same is not None and (same.role, same.label, same.section) == key:
            hit = same
        else:
            matches = [c for c in fresh.menu.candidates if (c.role, c.label, c.section) == key]
            if len(matches) != 1:
                raise NativeBridgeError(
                    "target_changed",
                    f"[{id}] {cand.label!r} is {'gone' if not matches else 'no longer unique'} in the window now",
                )
            hit = matches[0]
        if operation in ("type", "append", "enter") and _norm_tail(nm.values.get(id, "")) != _norm_tail(
            fresh.values.get(hit.id, "")
        ):
            raise NativeBridgeError(
                "precondition_changed", f"[{id}] {cand.label!r} holds different text than when decided"
            )
        if (cand.checked is not None and hit.checked != cand.checked) or (
            cand.pressed is not None and hit.pressed != cand.pressed
        ):
            raise NativeBridgeError(
                "precondition_changed", f"[{id}] {cand.label!r} changed state since the decision"
            )
        return fresh, hit.id

    def _not_sent(
        self, operation: str, target: int, label: str, code: str, reason: str, delivery: str
    ) -> NativeEffect:
        return NativeEffect(
            operation,
            target,
            label,
            "refused",
            None,
            (),
            reason[:200],
            code,
            delivery=delivery,
            dispatched=False,
            delivered_count=0,
            delivery_basis="qualified_gate",
        )

    def _effect(self, operation: str, target: int, label: str, outcome: Any, delivery: str) -> NativeEffect:
        if isinstance(outcome, NativeEffect):
            return dataclasses.replace(outcome, delivery=delivery)
        if isinstance(outcome, BaseException):
            code = (
                getattr(outcome, "code", None) or getattr(outcome, "reason", None) or type(outcome).__name__
            )
            from jevdual.ax import AXError

            if (isinstance(outcome, NativeBridgeError) and not outcome.dispatched) or (
                isinstance(outcome, AXError) and code in _MENU_NOT_PRESSED
            ):
                return self._not_sent(operation, target, label, str(code), str(outcome), delivery)
            return NativeEffect(
                operation,
                target,
                label,
                "unverifiable",
                None,
                (),
                str(outcome)[:200],
                str(code),
                delivery=delivery,
            )
        if outcome is _PRESSED:
            return NativeEffect(
                operation,
                target,
                label,
                "unverifiable",
                route="accessibility",
                summary="menu item press acknowledged; application effect not verified",
                delivery=delivery,
                delivered_count=1,
                delivery_basis="ax_menu_press_ack",
            )
        eff = effect_from_action_result(operation, target, label, outcome)
        return dataclasses.replace(eff, delivery=delivery)

    async def _foreground(
        self, operation: str, target: int, label: str, call: Any, *, why: str
    ) -> NativeEffect:
        """One foreground step: asked of the posture first, the front app read before and after."""
        refusal = self.policy.permits("foreground", why=why)
        if refusal is not None:
            return self._not_sent(operation, target, label, refusal.code, refusal.reason, "foreground")
        if sys.platform == "linux":
            # CUA verifies the exact X11 active window and core focus itself.
            # An exclusive desktop has no shared-user restoration contract.
            if self.policy.mode != "exclusive_desktop":
                return self._not_sent(operation, target, label, "platform_posture_unavailable",
                                      "Linux foreground input requires exclusive_desktop", "foreground")
            try:
                outcome = await call()
            except Exception as exc:  # noqa: BLE001 - never retry uncertain input
                outcome = exc
            if _linux_foreground_no_send(outcome):
                return self._not_sent(operation, target, label, "foreground_unavailable",
                                      str(outcome.text), "foreground")
            return self._effect(operation, target, label, outcome, "foreground")
        before = self.policy.before_foreground()
        prior_inputs = self._foreground_inputs
        try:
            outcome = await call()
        except Exception as exc:  # noqa: BLE001 - delivery may be uncertain
            outcome = exc
        # Give the front back when our window still holds it (bring_to_front leaves it there, and
        # invoke_menu re-activated our app 34 ms after the person had moved away, Q15 smoke 2026-09-25).
        # It goes to the person's latest choice during the step, never to where they were before it.
        act = self.policy._activity()
        if act.frontmost_pid() == self.pid:
            restore_target = self.policy.persons_choice(self.pid, before.get("front_before"))
            if restore_target not in (None, self.pid):
                ok = act.activate(int(restore_target))  # type: ignore[arg-type]
                before = {**before, "handed_back": restore_target, "hand_back_ok": ok}
        rec = self.policy.after_foreground(before)
        eff = self._effect(operation, target, label, outcome, "foreground")
        if not eff.dispatched and self._foreground_inputs != prior_inputs:
            # A failed menu/chord gate cannot erase a title-bar click already attempted.
            eff = dataclasses.replace(
                eff,
                effect="unverifiable",
                dispatched=True,
                delivery_basis="unknown",
                delivered_count=None,
            )
        note = "front app restored" if rec.get("restored") else "front app changed"
        return dataclasses.replace(eff, foreground=rec, summary=f"foreground ({note}); {eff.summary}"[:200])

    async def _key_route(
        self, operation: str, target: int, label: str, key: str, mods: list[str], token: str | None
    ) -> NativeEffect:
        """A key posted to the bound process in the background, focusing ``token`` first when given (one
        Driver call, so the element and the key cannot come apart). When the process owns other windows
        the Driver refuses; the step then needs the foreground, which the posture grants or refuses."""
        args: dict[str, Any] = {
            "pid": self.pid,
            "window_id": self.window_id,
            "key": key,
            "delivery_mode": "background",
        }
        if mods:
            args["modifiers"] = list(mods)
        if token is not None:
            args["element_token"] = token
        if self.session:
            args["session"] = self.session
        try:
            outcome = await self.driver.call_tool("press_key", json.dumps(args))
        except Exception as exc:  # noqa: BLE001 - delivery may be uncertain
            outcome = exc
        background = self._effect(operation, target, label, outcome, "background")
        # Only the SDK's structured no-send refusal authorizes another input.
        # Prose, exceptions and contradictory positive delivery stay uncertain.
        if not _keyboard_ambiguity_no_send(outcome, background, self.pid, self.window_id):
            return background
        fg = {**args, "delivery_mode": "foreground"}

        async def foreground_call() -> Any:
            if self.observation_guard is not None:
                await self.observe()
            return await self.driver.call_tool("press_key", json.dumps(fg))

        eff = await self._foreground(
            operation,
            target,
            label,
            foreground_call,
            why=f"{label} (the process owns other windows, so a background key cannot be proven to reach this one; {AMBIGUITY})",
        )
        if not eff.dispatched:
            return dataclasses.replace(eff, evidence=(*eff.evidence, f"background: {AMBIGUITY}"))
        return eff

    async def _append(
        self,
        nm: NativeMenu,
        id: int,
        cand: Candidate,
        text: str,
        precondition: AppendPrecondition | None = None,
    ) -> NativeEffect:
        """Insert at the end of the exact value through AX and require ``after == before + inserted``.
        Nothing is rebuilt from a preview; a value that no longer matches the decision is refused before
        writing."""
        role = nm.ax_roles.get(id, "AXTextArea")
        frame = nm.frames.get(id)
        ax = self.ax
        insertion_started = False
        try:
            if precondition is not None and (role != precondition.role or frame != precondition.frame):
                return self._not_sent(
                    "append",
                    id,
                    cand.label,
                    "target_changed",
                    "the original field role or frame changed; nothing written",
                    "background",
                )
            el = ax.resolve(self.pid, self.window_id, role, ax.Frame(*frame) if frame else None)
            if precondition is not None:
                if ax.frame_of(el) != ax.Frame(*precondition.frame):
                    return self._not_sent(
                        "append",
                        id,
                        cand.label,
                        "target_changed",
                        "the original field frame changed; nothing written",
                        "background",
                    )
                if not ax.can_insert(el):
                    return self._not_sent(
                        "append",
                        id,
                        cand.label,
                        "not_writable",
                        "exact insertion is no longer available; nothing written",
                        "background",
                    )
            exact = ax.value(el)
            changed = (
                exact != precondition.value
                if precondition is not None
                else (exact != nm.values.get(id) if sys.platform == "linux"
                      else _norm_tail(exact) != _norm_tail(nm.values.get(id, "")))
            )
            if changed:
                return self._not_sent(
                    "append",
                    id,
                    cand.label,
                    "precondition_changed",
                    "the field holds different text than when the step was decided; nothing written",
                    "background",
                )
            if precondition is not None:
                # The higher-level adapter supplies a trusted readonly check of
                # process/file identity. It runs after live observation and field reads.
                if precondition.resource_check is not None and not precondition.resource_check():
                    return self._not_sent(
                        "append",
                        id,
                        cand.label,
                        "lost_identity",
                        "the original resource changed; nothing written",
                        "background",
                    )
                document = self.document_path(precondition.document)
                if precondition.document is not None and (
                    not document or Path(document).resolve() != Path(precondition.document).resolve()
                ):
                    return self._not_sent(
                        "append",
                        id,
                        cand.label,
                        "lost_identity",
                        "the original document changed; nothing written",
                        "background",
                    )
                if ax.frame_of(el) != ax.Frame(*precondition.frame) or not ax.can_insert(el):
                    return self._not_sent(
                        "append",
                        id,
                        cand.label,
                        "target_changed",
                        "the original field changed; nothing written",
                        "background",
                    )
            sep = "" if exact == "" or exact.endswith("\n") else "\n"
            insertion_started = True
            before, after = ax.insert_at_end(el, sep + text, expect=exact)
        except ax.AXError as exc:
            # insert_at_end checks this precondition before its first write. Other errors
            # from inside insertion may originate from the readback after a successful write.
            not_sent = not insertion_started or exc.reason == "precondition_changed"
            return NativeEffect(
                "append",
                id,
                cand.label,
                "refused" if not_sent else "unverifiable",
                "accessibility",
                (),
                str(exc)[:200],
                exc.reason,
                delivery="background",
                dispatched=not not_sent,
                delivered_count=0 if not_sent else None,
                delivery_basis="qualified_gate" if not_sent else "unknown",
            )
        inserted = sep + text
        want = before + inserted
        complete = all(len(value) <= 65_536 for value in (before, after, want))
        readback = {
            "schema_version": 1,
            "producer": {"name": "footwork.native", "version": 1},
            "predicate": "field_equals",
            "before_value": before if complete else None,
            "observed_value": after if complete else None,
            "expected_value": want if complete else None,
            "matches": after == want,
            "complete": complete,
            "target_id": id,
            "label": cand.label,
            "role": role,
            "frame": list(frame) if frame is not None else None,
            "snapshot_id": nm.snapshot_id,
        }
        if after == before + inserted:
            return NativeEffect(
                "append",
                id,
                cand.label,
                "confirmed",
                "accessibility",
                (
                    f"value_readback: {len(before)} characters kept exactly, {len(inserted)} inserted at the end",
                ),
                "appended",
                delivery="background",
                driver_delivery="background",
                delivered_count=1,
                delivery_basis="ax_insert_ack",
                field_readback=readback,
            )
        diverge = next((i for i, (a, b) in enumerate(zip(after, want, strict=False)) if a != b), None)
        at = diverge if diverge is not None else min(len(after), len(want))
        return NativeEffect(
            "append",
            id,
            cand.label,
            "partial",
            "accessibility",
            (
                f"value_readback: expected {len(before) + len(inserted)} characters, read {len(after)}; first difference at {at}",
            ),
            "the field does not read back as the old text plus the insertion",
            "content_mismatch",
            delivery="background",
            driver_delivery="background",
            delivered_count=1,
            delivery_basis="ax_insert_ack",
            field_readback=readback,
        )

    def document_path(self, expected: str | None = None) -> str | None:
        """Linux document authority requires an explicitly scoped app contract."""
        if sys.platform != "linux":
            return self.ax.document_path(self.pid, self.window_id)
        from jevdual import linux_documents

        binding = getattr(self, "_linux_document", None)
        if binding is None:
            if expected is None:
                return None
            binding = linux_documents.bind(self.pid, self.window_id, expected)
            self._linux_document = binding
        if expected is not None and binding.path != expected:
            raise self.ax.AXError("lost_identity", "the scoped document changed")
        linux_documents.revalidate(binding)
        return binding.path

    def _type_linux(self, nm: NativeMenu, id: int, cand: Candidate, text: str) -> NativeEffect:
        """Replace through the qualified object once, then compare complete exact text."""
        started = False
        try:
            frame = nm.frames.get(id)
            if frame is None or id not in nm.values:
                return self._not_sent("type", id, cand.label, "value_unavailable",
                                      "exact observed text and geometry are required", "background")
            target = self.ax.resolve(self.pid, self.window_id, nm.ax_roles[id], self.ax.Frame(*frame))
            if self.ax.value(target) != nm.values[id] or not self.ax.can_set_value(target):
                return self._not_sent("type", id, cand.label, "precondition_changed",
                                      "the original editable value changed", "background")
            started = True
            self.ax.set_value_ack(target, text)
            after = self.ax.value(target)
            return NativeEffect(
                "type", id, cand.label, "confirmed" if after == text else "partial", "accessibility",
                ("exact value readback matches" if after == text else "exact value readback differs",),
                "replaced text" if after == text else "text replacement differs",
                delivery="background", driver_delivery="background", delivered_count=1,
                delivery_basis="ax_set_value_ack",
            )
        except self.ax.AXError as exc:
            if not started:
                return self._not_sent("type", id, cand.label, exc.reason, str(exc), "background")
            return self._effect("type", id, cand.label, exc, "background")

    async def _type_web(
        self, nm: NativeMenu, id: int, cand: Candidate, token: str, text: str
    ) -> NativeEffect:
        """Type into a field inside web content. WebKit ignores AXValue writes there (Safari, 2026-09-25:
        the form was submitted empty), so the text is inserted with ``type_text`` (AX insertion, or the
        Driver's character synthesis where the page does not take it); a field that already holds text is
        selected first with Command-A on that element, through the key route and so through the posture.
        The field is read back: ``confirmed`` only when it holds the text."""
        label = cand.label
        selected = False
        if nm.values.get(id, "").strip():
            sel = await self._key_route("type", id, label, "a", ["ctrl" if sys.platform == "linux" else "cmd"], token)
            if not sel.dispatched or sel.effect != "confirmed" or sel.error_code:
                return dataclasses.replace(sel, summary=f"select-all before typing: {sel.summary}"[:200])
            selected = True
            fresh = await self._observe_after_input()
            token = fresh.token(id) or token
        args: dict[str, Any] = {
            "pid": self.pid,
            "window_id": self.window_id,
            "element_token": token,
            "text": text,
            "delivery_mode": "background",
        }
        if self.session:
            args["session"] = self.session
        try:
            outcome: Any = await self.driver.call_tool("type_text", json.dumps(args))
        except Exception as exc:  # noqa: BLE001 - delivery may be uncertain
            outcome = exc
        eff = self._effect("type", id, label, outcome, "background")
        typing_refused = not eff.dispatched
        if selected and not eff.dispatched:
            eff = dataclasses.replace(
                eff,
                effect="unverifiable",
                dispatched=True,
                delivery_basis="unknown",
                delivered_count=None,
            )
        if typing_refused or eff.error_code or getattr(outcome, "is_error", False):
            return eff
        after = await self._observe_after_input()
        self.last = None
        same = after.menu.candidate(id)
        got = after.values.get(id, "") if same is not None and same.label == label else None
        if got is not None and got.strip() == text.strip():
            return dataclasses.replace(
                eff, effect="confirmed", evidence=(*eff.evidence, "value_readback: the field holds the text")
            )
        return dataclasses.replace(
            eff,
            effect="suspected_noop",
            evidence=(
                *eff.evidence,
                f"value_readback: the field holds {len(got or '')} characters, not the text",
            ),
        )

    async def _observe_after_input(self) -> NativeMenu:
        try:
            return await self.observe()
        except NativeBridgeError as exc:
            raise NativeBridgeError(exc.reason, str(exc), dispatched=True) from exc

    async def _click_token(self, token: str) -> Any:
        from jevdual.effectors.cua import background_delivery, click_input, element_position

        return await self.driver.click(
            click_input(
                target=self._target(),
                position=element_position(element_token=token),
                delivery_mode=background_delivery(),
                session=self.session,
                button=None,
                count=None,
            )
        )

    def resolve_file(self, nm: NativeMenu, selector: str) -> tuple[Any, int]:
        """Resolve the exact retained Finder inode in this fresh window."""
        from jevdual.finder_targets import FinderBinding, candidate_id, rebind, resolve

        if not self.finder_scope or nm.app_name != "Finder":
            raise NativeBridgeError("file_scope_missing", "an owned Finder manifest is required")
        binding = FinderBinding.from_record(self.finder_scope["binding"])
        binding = rebind(binding, self.finder_scope["manifest"], selector)
        target = resolve(self.pid, self.window_id, binding, self.finder_scope["manifest"])
        return target, candidate_id(target, nm)

    async def act_file(
        self, nm: NativeMenu, operation: str, selector: str, text: str | None = None
    ) -> NativeEffect:
        """Rename or move the exact owned file through Finder's front/key UI."""
        target, id = self.resolve_file(nm, selector)
        self._require_fresh(nm, id)
        if operation == "move":
            self._move_plan(target.binding, text)

        async def call() -> NativeEffect:
            await self._front_and_key()
            # These routes use fresh strict AX file/inode/frame resolution, not
            # SDK element tokens. Do not interpose another SDK capture after
            # acquiring the key window; it can introduce another focus lifecycle.
            if operation == "move":
                return await self._move_file(nm, selector, text)
            return await self._rename_file(nm, operation, selector, text)

        return await self._foreground(
            operation, id, target.value, call, why="Finder file editing requires its front/key window"
        )

    def _move_plan(self, binding: Any, directory: str | None) -> tuple[dict[str, Any], str, dict[str, Any]]:
        from jevdual.finder_targets import file_identity, move_destination

        if not isinstance(directory, str):
            raise NativeBridgeError("file_destination_invalid", "move requires one absolute owned directory")
        destination = move_destination(self.finder_scope["manifest"], directory)
        path = str(Path(directory) / Path(binding.path).name)
        if path != str(
            Path(self.finder_scope["manifest"]["root"]) / self.finder_scope["manifest"]["paths"]["organized"]
        ):
            raise NativeBridgeError(
                "file_destination_invalid", "move must produce the declared organized path"
            )
        if Path(path).exists() or Path(path).is_symlink() or path == binding.path:
            raise NativeBridgeError("file_destination_exists", "the owned move destination must be empty")
        self._move_destination_window(directory)
        return destination, path, file_identity(self.finder_scope["manifest"], binding)

    def _move_destination_window(self, directory: str) -> dict[str, Any]:
        """Revalidate the pre-bound second window before any move preparation."""
        from jevdual.finder_targets import resolve_marker

        registered = self.finder_scope.get("destination_window")
        if (
            not isinstance(registered, dict)
            or type(registered.get("pid")) is not int
            or registered["pid"] != self.pid
            or type(registered.get("window_id")) is not int
            or registered["window_id"] <= 0
            or registered["window_id"] == self.window_id
        ):
            raise NativeBridgeError(
                "file_destination_window_missing",
                "one separately pre-bound owned destination window is required",
            )
        current = resolve_marker(self.pid, registered["window_id"], self.finder_scope["manifest"], directory)
        if current != registered:
            raise NativeBridgeError(
                "file_destination_window_changed", "the pre-bound destination window identity changed"
            )
        return current

    async def _move_file(self, nm: NativeMenu, selector: str, directory: str | None) -> NativeEffect:
        """Copy the owned source and Move Item Here in its pre-bound destination window."""
        from jevdual.finder_targets import file_identity, move_destination, rebind

        target, id = self.resolve_file(nm, selector)
        self._require_fresh(nm, id)
        destination, path, source = self._move_plan(target.binding, directory)
        assert directory is not None
        registered = self._move_destination_window(directory)
        destination_window_id = registered["window_id"]
        self.last = None
        self.dispatches += 1
        count = 0
        active_window_id = self.window_id
        proof: dict[str, Any] = {
            "schema_version": 1,
            "producer": "footwork.ax.finder",
            "predicate": "finder_move_same_inode",
            "transfer_route": "prebound_destination_window",
            "before": target.to_record(),
            "source_identity": source,
            "destination_directory": destination,
            "destination": path,
            "destination_window_binding": registered,
            "acknowledgements": [],
        }

        def front() -> None:
            context = self.ax.finder_window_context(self.pid)
            proof["last_window_context"] = {**context, "front_pid": self.policy._activity().frontmost_pid()}
            if (
                proof["last_window_context"]["front_pid"] != self.pid
                or context["main_window_id"] != active_window_id
                or context["focused_window_id"] != active_window_id
            ):
                raise self.ax.AXError(
                    "file_move_lost_focus", "the exact owned Finder move window lost foreground"
                )

        def unchanged_source() -> None:
            if file_identity(self.finder_scope["manifest"], target.binding) != source:
                raise self.ax.AXError(
                    "file_source_changed", "the owned source changed during move preparation"
                )
            if move_destination(self.finder_scope["manifest"], directory) != destination:
                raise self.ax.AXError(
                    "file_destination_changed", "the owned destination changed during move preparation"
                )
            if Path(path).exists() or Path(path).is_symlink():
                raise self.ax.AXError(
                    "file_destination_changed", "the destination appeared before Move Item Here"
                )

        def acknowledge(name: str) -> None:
            nonlocal count
            count += 1
            proof["acknowledgements"].append(name)

        async def menu(path_parts: list[str], label: str, verify: Any = None) -> None:
            front()
            enabled = False
            for _ in range(20):
                enabled = self.ax.menu_item_enabled(self.pid, path_parts)
                if enabled:
                    break
                await asyncio.sleep(0.05)
            if not enabled:
                raise self.ax.AXError(
                    "file_move_menu_disabled", "the exact move workflow menu item is disabled"
                )
            front()
            if verify is not None:
                verify()
            self.ax.press_menu(self.pid, path_parts)
            acknowledge(label)

        try:
            front()
            self.ax.select_finder_row_ack(target.element)
            acknowledge("exact_row_selected")
            if not self.ax.finder_selection_state(target.element).get("exact_row_only"):
                raise self.ax.AXError(
                    "file_selection_unverified", "the owned file must be the sole selected row"
                )
            before_clipboard = self.ax.pasteboard_change_count()
            self.ax.press_menu(self.pid, ["Edit"])
            acknowledge("edit_menu_opened_for_copy")
            copy_titles = {"Copy", f"Copy “{target.value}”", f'Copy "{target.value}"'}
            copy_paths = [
                item.split(" > ")
                for item in self.ax.menu_paths(self.pid)
                if item.split(" > ")[:-1] == ["Edit"] and item.split(" > ")[-1] in copy_titles
            ]
            if len(copy_paths) != 1:
                raise self.ax.AXError(
                    "file_copy_menu_ambiguous", "one exact Copy item for the owned filename is required"
                )
            proof["copy_menu_path"] = copy_paths[0]

            def copy_precondition() -> None:
                unchanged_source()
                if not self.ax.finder_selection_state(target.element).get("exact_row_only"):
                    raise self.ax.AXError(
                        "file_selection_changed", "the sole selected source changed before Copy"
                    )

            await menu(copy_paths[0], "copy_menu_pressed", copy_precondition)
            copied_count = before_clipboard
            for _ in range(20):
                copied_count = self.ax.pasteboard_change_count()
                if copied_count != before_clipboard:
                    break
                await asyncio.sleep(0.05)
            if copied_count <= before_clipboard:
                raise self.ax.AXError(
                    "file_clipboard_stale", "Copy did not produce a new clipboard generation"
                )
            if self.ax.pasteboard_file_paths() != [target.binding.path]:
                raise self.ax.AXError(
                    "file_clipboard_mismatch", "Copy did not expose the exact owned file URL"
                )
            proof["clipboard"] = {
                "before_change_count": before_clipboard,
                "after_change_count": copied_count,
                "paths": [target.binding.path],
            }
            unchanged_source()
            self._move_destination_window(directory)
            destination_bridge = NativeBridge(
                self.driver,
                self.pid,
                destination_window_id,
                policy=self.policy,
                ax=self.ax,
                session=self.session + "-destination",
            )
            try:
                await destination_bridge._front_and_key()
            finally:
                self._foreground_inputs += destination_bridge._foreground_inputs
            active_window_id = destination_window_id
            proof["navigation"] = self._move_destination_window(directory)
            front()
            self.ax.press_menu(self.pid, ["Edit"])
            acknowledge("edit_menu_opened_for_move")

            def move_precondition() -> None:
                unchanged_source()
                if self.ax.pasteboard_change_count() != copied_count or self.ax.pasteboard_file_paths() != [
                    target.binding.path
                ]:
                    raise self.ax.AXError(
                        "file_clipboard_changed", "the copied file changed before Move Item Here"
                    )
                self._move_destination_window(directory)
                front()

            await menu(["Edit", "Move Item Here"], "move_item_here_pressed", move_precondition)
            rebound = None
            for _ in range(40):
                try:
                    rebound = rebind(target.binding, self.finder_scope["manifest"], "file:" + path)
                    if not Path(target.binding.path).exists() and not Path(target.binding.path).is_symlink():
                        break
                except self.ax.AXError:
                    rebound = None
                await asyncio.sleep(0.05)
            if (
                rebound is None
                or Path(target.binding.path).exists()
                or Path(target.binding.path).is_symlink()
            ):
                raise self.ax.AXError("file_move_unverified", "the exact same-inode move was not established")
            after = file_identity(self.finder_scope["manifest"], rebound)
            if after["sha256"] != source["sha256"] or after["size"] != source["size"]:
                raise self.ax.AXError("file_move_contents_changed", "the moved file's bytes changed")
            if move_destination(self.finder_scope["manifest"], directory) != destination:
                raise self.ax.AXError(
                    "file_destination_changed", "the destination directory changed during the move"
                )
            proof["after"] = rebound.to_record()
            proof["after_identity"] = after
            return NativeEffect(
                "move",
                id,
                target.value,
                "confirmed",
                route="accessibility",
                summary="owned same-inode move observed after Finder UI input; count is acknowledged-input lower bound",
                delivered_count=count,
                delivery_basis="ax_finder_move_readback",
                native_readback=proof,
            )
        except Exception as exc:  # noqa: BLE001 - acknowledged inputs cannot be erased by missing readback
            return NativeEffect(
                "move",
                id,
                target.value,
                "unverifiable",
                route="accessibility",
                summary=str(exc)[:200],
                error_code=getattr(exc, "reason", type(exc).__name__),
                delivered_count=count or None,
                delivery_basis="ax_finder_move_readback" if count else "unknown",
                native_readback=proof,
            )

    async def _rename_file(
        self, nm: NativeMenu, operation: str, selector: str, text: str | None = None
    ) -> NativeEffect:
        """Source-qualified rename producer; called only after front/key qualification."""
        from jevdual.finder_targets import rebind, resolve

        target, id = self.resolve_file(nm, selector)
        self._require_fresh(nm, id)
        if (
            operation != "type"
            or not text
            or Path(text).name != text
            or text in {".", ".."}
            or "\x00" in text
        ):
            raise NativeBridgeError(
                "file_operation_unsupported", "Finder filename input requires one basename"
            )
        destination = str(Path(target.binding.path).with_name(text))
        if destination == target.binding.path or Path(destination).exists() or Path(destination).is_symlink():
            raise NativeBridgeError("file_destination_exists", "the destination must be a fresh owned path")
        # Check the destination is a declared fixture path before any input.
        from jevdual.app_oracles import OracleError, _asset_path

        try:
            _asset_path(self.finder_scope["manifest"], destination)
        except OracleError as exc:
            raise NativeBridgeError(
                "file_scope_invalid", "destination is outside declared fixture paths"
            ) from exc
        target, id = self.resolve_file(nm, selector)
        self.last = None
        self.dispatches += 1
        count = 0
        proof = {
            "schema_version": 1,
            "producer": "footwork.ax.finder",
            "predicate": "finder_rename_same_inode",
            "before": target.to_record(),
            "destination": destination,
            "acknowledgements": [],
        }

        def context() -> dict[str, Any]:
            try:
                selection = self.ax.finder_selection_state(target.element)
            except self.ax.AXError as exc:
                selection = {"exact_row_only": False, "error": exc.reason}
            return {
                **self.ax.finder_window_context(self.pid),
                "front_pid": self.policy._activity().frontmost_pid(),
                "selection": selection,
            }

        def selection_owned(current: dict[str, Any], *, menu_focus: bool = False) -> bool:
            # Opening our File menu can move AX focus to the application. Only
            # this acknowledged menu stage permits a missing focused window;
            # the exact front/main window and sole owned row remain mandatory.
            focused = current["focused_window_id"] == self.window_id or (
                menu_focus
                and current["focused_window_id"] is None
                and current["focused_role"] == "AXApplication"
            )
            return (
                current["front_pid"] == self.pid
                and current["main_window_id"] == self.window_id
                and focused
                and current["selection"]["exact_row_only"]
            )

        try:
            proof["before_selection"] = context()
            self.ax.select_finder_row_ack(target.element)
            count += 1
            proof["acknowledgements"].append("exact_row_selected")
            proof["before_menu"] = context()
            if not selection_owned(proof["before_menu"]):
                raise self.ax.AXError(
                    "file_selection_unverified",
                    "the exact bound row is not the sole selected row in the front window",
                )
            self.ax.press_menu(self.pid, ["File"])
            count += 1
            proof["acknowledgements"].append("file_menu_opened")
            rename_enabled = False
            for _ in range(20):
                rename_enabled = self.ax.menu_item_enabled(self.pid, ["File", "Rename"])
                if rename_enabled:
                    break
                await asyncio.sleep(0.05)
            proof["rename_enabled"] = rename_enabled
            if not rename_enabled:
                raise self.ax.AXError("file_rename_disabled", "the opened File menu did not enable Rename")
            proof["before_rename"] = context()
            if not selection_owned(proof["before_rename"], menu_focus=True):
                raise self.ax.AXError(
                    "file_selection_unverified",
                    "the bound Finder window or sole selection changed before Rename",
                )
            self.ax.press_menu(self.pid, ["File", "Rename"])
            count += 1
            proof["acknowledgements"].append("rename_menu_pressed")
            proof["after_menu"] = context()
            editor = None
            for _ in range(20):
                try:
                    editor = self.ax.focused_finder_editor(
                        self.pid, self.window_id, target.frame, target.value
                    )
                    if self.ax.value(editor) == target.value:
                        break
                except self.ax.AXError as exc:
                    proof["editor_error"] = {"reason": exc.reason, "detail": str(exc)[:200]}
                    editor = None
                await asyncio.sleep(0.05)
            if editor is None or self.ax.value(editor) != target.value or not self.ax.can_set_value(editor):
                proof["editor_failure_context"] = context()
                raise self.ax.AXError("file_editor_missing", "the actual rename editor was not established")
            proof["editor"] = {
                "pid": self.pid,
                "window_id": self.window_id,
                "role": "AXTextField",
                "before_value": self.ax.value(editor),
            }
            current_editor = self.ax.focused_finder_editor(
                self.pid, self.window_id, target.frame, target.value
            )
            proof["before_editor_write"] = context()
            current = proof["before_editor_write"]
            if (
                current["front_pid"] != self.pid
                or current["main_window_id"] != self.window_id
                or current["focused_window_id"] not in (None, self.window_id)
                or (
                    not current["selection"]["exact_row_only"]
                    and current["selection"].get("error") != "file_row_missing"
                )
                or current_editor != editor
            ):
                raise self.ax.AXError(
                    "file_editor_lost_focus", "the exact owned rename editor changed before its value write"
                )
            # Finder replaces the filename row with this already qualified
            # transient editor. Its absence cannot replace the editor/window
            # checks above or the exact original inode check before writing.
            rebind(target.binding, self.finder_scope["manifest"], selector)
            self.ax.set_value_ack(editor, text)
            count += 1
            proof["acknowledgements"].append("editor_value_set")
            if self.ax.value(editor) != text:
                raise self.ax.AXError(
                    "file_editor_unverified", "the actual editor did not retain the new name"
                )
            rebind(target.binding, self.finder_scope["manifest"], selector)
            current_editor = self.ax.focused_finder_editor(self.pid, self.window_id, target.frame, text)
            if self.policy._activity().frontmost_pid() != self.pid or current_editor != editor:
                raise self.ax.AXError(
                    "file_editor_lost_focus", "the bound rename window lost foreground before commit"
                )
            if Path(destination).exists() or Path(destination).is_symlink():
                raise self.ax.AXError(
                    "file_destination_changed", "the rename destination appeared before commit"
                )
            outcome = await self.driver.call_tool(
                "hotkey",
                json.dumps(
                    {
                        "pid": self.pid,
                        "window_id": self.window_id,
                        "keys": ["Return"],
                        "delivery_mode": "foreground",
                        "session": self.session,
                    }
                ),
            )
            commit = effect_from_action_result("enter", id, target.value, outcome)
            proof["commit"] = {
                "route": "sdk_foreground_return",
                "effect": commit.effect,
                "delivered_count": commit.delivered_count,
            }
            if commit.delivered_count:
                count += commit.delivered_count
            if not commit.dispatched or commit.error_code:
                raise self.ax.AXError(
                    "file_commit_uncertain", "the rename commit did not return a successful acknowledgement"
                )
            rebound = None
            for _ in range(20):
                try:
                    rebound = rebind(target.binding, self.finder_scope["manifest"], "file:" + destination)
                    if not Path(target.binding.path).exists() and not Path(target.binding.path).is_symlink():
                        break
                except self.ax.AXError:
                    rebound = None
                await asyncio.sleep(0.05)
            if (
                rebound is None
                or Path(target.binding.path).exists()
                or Path(target.binding.path).is_symlink()
            ):
                raise self.ax.AXError("rename_unverified", "same-inode rename is not established")

            def completion_owned(*, allow_current_editor: bool = False) -> bool:
                current = self.ax.finder_window_context(self.pid)
                proof["completion_context"] = {
                    **current,
                    "front_pid": self.policy._activity().frontmost_pid(),
                }
                if (
                    proof["completion_context"]["front_pid"] != self.pid
                    or current["main_window_id"] != self.window_id
                ):
                    return False
                if current["focused_window_id"] == self.window_id:
                    return True
                if allow_current_editor and current["focused_window_id"] is None:
                    return self.ax.finder_completion_editor(self.pid, self.window_id, text) is not None
                return False

            if not completion_owned(allow_current_editor=True):
                raise self.ax.AXError(
                    "file_completion_lost_focus", "the owned rename window lost foreground before completion"
                )
            proof["completion_reacquire_context"] = dict(proof["completion_context"])
            await self._front_and_key()
            completion = None
            for _ in range(20):
                if not completion_owned():
                    raise self.ax.AXError(
                        "file_completion_lost_focus",
                        "the owned rename window lost foreground during completion",
                    )
                try:
                    completion = resolve(self.pid, self.window_id, rebound, self.finder_scope["manifest"])
                    if completion_owned():
                        break
                    completion = None
                except self.ax.AXError:
                    completion = None
                await asyncio.sleep(0.05)
            if completion is None:
                raise self.ax.AXError(
                    "file_completion_unverified",
                    "the renamed file's exact filename target did not become ready",
                )
            proof["completion_target"] = completion.to_record()
            proof["after"] = rebound.to_record()
            return NativeEffect(
                operation,
                id,
                target.value,
                "confirmed",
                route="accessibility",
                summary="rename editor input acknowledged; same-inode rename observed; count is acknowledged-input lower bound",
                delivered_count=count,
                delivery_basis="ax_finder_rename_readback",
                native_readback=proof,
            )
        except Exception as exc:  # noqa: BLE001 - a write may have landed
            return NativeEffect(
                operation,
                id,
                target.value,
                "unverifiable",
                route="accessibility",
                summary=str(exc)[:200],
                error_code=getattr(exc, "reason", type(exc).__name__),
                delivered_count=count or None,
                delivery_basis="ax_finder_rename_readback" if count else "unknown",
                native_readback=proof,
            )

    async def act(
        self,
        nm: NativeMenu,
        operation: str,
        id: int,
        text: str | None = None,
        *,
        append_precondition: AppendPrecondition | None = None,
    ) -> NativeEffect:
        """Dispatch exactly one operation. The caller must reobserve afterwards; ``self.last`` is
        cleared so a second act on the same snapshot is refused as stale."""
        if append_precondition is not None and operation != "append":
            raise NativeBridgeError(
                "unknown_operation", "An exact append precondition only applies to append"
            )
        cand, token = self._require_fresh(nm, id)
        if operation not in cand.operations:
            raise NativeBridgeError(
                "unknown_operation", f"{operation!r} is not offered on [{id}] {cand.label!r} ({cand.role})"
            )
        if operation in ("type", "append") and text is None:
            raise NativeBridgeError("text_required", f"{operation} on [{id}] needs a value")
        decision_snapshot, decision_target = nm.snapshot_id, id
        if self.live_check or self.observation_guard is not None:
            decided_values = nm.values
            nm, fresh_id = await self._live(nm, id, operation)
            # the text the decision was based on is what the append compares against
            nm = dataclasses.replace(nm, values={**nm.values, fresh_id: decided_values.get(id, "")})
            id = fresh_id
            cand, token = self._require_fresh(nm, id)
        self.last = None
        self.dispatches += 1
        label = cand.label
        if operation == "append":
            assert text is not None
            result = await self._append(nm, id, cand, text, append_precondition)
            if result.field_readback is not None:
                result = dataclasses.replace(
                    result,
                    field_readback={
                        **result.field_readback,
                        "decision_snapshot_id": decision_snapshot,
                        "decision_target_id": decision_target,
                    },
                )
            return result
        if operation in ("enter",):
            return await self._key_route("enter", id, label, "return", [], token)
        if operation == "hover":
            refusal = self.policy.permits("desktop", why=f"hover on {label!r} (it moves the real pointer)")
            if refusal is not None:
                return self._not_sent("hover", id, label, refusal.code, refusal.reason, "desktop")
            fx, fy, fw, fh = nm.frames.get(id, (0.0, 0.0, 0.0, 0.0))
            try:
                outcome = await self.driver.call_tool(
                    "move_cursor",
                    json.dumps(
                        {"x": fx + fw / 2, "y": fy + fh / 2, "scope": "desktop", "session": self.session}
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                outcome = exc
            return self._effect("hover", id, label, outcome, "desktop")
        try:
            if operation == "click":
                outcome: Any = await self._click_token(token)
            elif operation == "type" and sys.platform == "linux":
                return await asyncio.to_thread(self._type_linux, nm, id, cand, text or "")
            elif operation == "type" and id in nm.web:
                return await self._type_web(nm, id, cand, token, text or "")
            elif operation == "type":
                args = {"element_token": token, "value": text, "pid": self.pid}
                if self.session:
                    args["session"] = self.session
                outcome = await self.driver.call_tool("set_value", json.dumps(args))
            elif operation == "scroll":
                args = {
                    "pid": self.pid,
                    "window_id": self.window_id,
                    "element_token": token,
                    "direction": "down",
                    "by": "page",
                    "amount": 1,
                    "delivery_mode": "background",
                }
                if self.session:
                    args["session"] = self.session
                outcome = await self.driver.call_tool("scroll", json.dumps(args))
                if not effect_from_action_result(operation, id, label, outcome).dispatched:
                    # a wheel the Driver will not aim at this element: Page Down to the element instead,
                    # through the key route and so through the posture (2026-09-25: a Chrome list refused)
                    return await self._key_route("scroll", id, label, "pagedown", [], token)
            else:
                raise NativeBridgeError("unsupported", f"{operation!r} has no native dispatch yet")
        except NativeBridgeError:
            raise
        except Exception as exc:  # noqa: BLE001 - input may have landed before the error
            log.info("native %s on [%s] outcome unknown: %s", operation, id, exc)
            return self._effect(operation, id, label, exc, "background")
        return self._effect(operation, id, label, outcome, "background")

    async def key(self, nm: NativeMenu, key: str, modifiers: list[str] | None = None) -> NativeEffect:
        """Press one key or chord in the window in the background (System 2 only; System 1's menu has no
        key operation). Needs the foreground only when the process owns other windows."""
        mods = [{"command": "cmd", "option": "alt", "control": "ctrl"}.get(m, m) for m in (modifiers or [])]
        if self.last is None or nm.snapshot_id != self.last.snapshot_id:
            raise NativeBridgeError("stale", "key press decided on a stale snapshot; reobserve")
        if self.observation_guard is not None:
            await self.observe()
        self.last = None
        self.dispatches += 1
        return await self._key_route("key", -1, "+".join([*mods, key]), key, mods, None)

    async def _front(self) -> None:
        """Declare exact foreground intent to the SDK, then establish native activation.

        The supported intent boundary ends the SDK's background restoration tails;
        native foreground/key readback remains required before application input.
        Callers obtain posture permission before entering this boundary.
        """
        if self.observation_guard is not None:
            await self.observe()
        try:
            outcome = await self.driver.call_tool(
                "bring_to_front",
                json.dumps({"pid": self.pid, "window_id": self.window_id, "session": self.session}),
            )
        except Exception as exc:
            raise NativeBridgeError(
                "foreground_intent_failed", "the SDK foreground intent failed; application input not sent"
            ) from exc
        effect = effect_from_action_result("foreground_intent", -1, "foreground", outcome)
        record = None
        structured = getattr(outcome, "structured_json", None)
        if structured is not None:
            try:
                record = json.loads(structured) if isinstance(structured, str) else structured
                if not isinstance(record, dict) or any(
                    key in record and (type(record[key]) is not int or record[key] != expected)
                    for key, expected in (("pid", self.pid), ("window_id", self.window_id))
                ):
                    raise ValueError("foreground intent identity differs")
            except (TypeError, ValueError) as exc:
                raise NativeBridgeError(
                    "foreground_intent_target_changed", "the SDK foreground intent identity was not exact"
                ) from exc
        verified_activation = (
            isinstance(record, dict)
            and record.get("code") == "bring_to_front_exact_window_verified"
            and record.get("status") == "activated"
            and record.get("request_accepted") is True
            and record.get("pid") == self.pid
            and record.get("window_id") == self.window_id
            and isinstance(record.get("exact_window_effect"), dict)
            and record["exact_window_effect"].get("verified") is True
            and isinstance(record.get("observed"), dict)
            and record["observed"].get("focused_window_id") == self.window_id
            and record["observed"].get("frontmost_pid") == self.pid
        )
        # ToolResult.error_code also lifts informational structured `code`
        # values. Only this exact success contract can override that field.
        if (
            getattr(outcome, "is_error", False)
            or effect.effect == "refused"
            or getattr(getattr(outcome, "action", None), "error", None) is not None
            or (
                effect.error_code
                and not (verified_activation and effect.error_code == "bring_to_front_exact_window_verified")
            )
        ):
            raise NativeBridgeError(
                "foreground_intent_refused", "the SDK foreground intent refused; application input not sent"
            )
        # activate first, then raise: activating the app re-keys whichever of its windows was key, so a raise
        # made before it is undone (Q19 frozen re-drive: the bound TextEdit document never became key)
        await asyncio.to_thread(self.policy._activity().activate, self.pid)
        self.ax.raise_window(self.pid, self.window_id)

    async def _front_and_key(self) -> None:
        """Front the bound window and wait until it is its app's key window, or refuse: a menu item or a chord
        acts on the key window, so if that is another window nothing is sent (Q19: a Command-S dispatched to
        one TextEdit document saved another)."""
        await self._front()
        act = self.policy._activity()

        async def keyed() -> bool:
            for _ in range(30):
                if act.frontmost_pid() == self.pid and self.ax.focused_window_id(self.pid) == self.window_id:
                    return True
                await asyncio.sleep(0.02)
            return False

        if await keyed():
            return
        # some apps (TextEdit) reorder their windows on a programmatic raise but change the key window only
        # on real input: one click on the bound window's own title bar, where a hit test says it is ours
        # (Q19 U48, R6); this step already has the posture's foreground permission
        point = await asyncio.to_thread(self.ax.title_bar_point, self.pid, self.window_id)
        if point is None:
            raise NativeBridgeError(
                "not_key",
                "the bound window did not become the key window and its title bar is covered; not pressed",
            )
        self._foreground_inputs += 1
        await asyncio.to_thread(self.ax.click_at, *point)
        if await keyed():
            return
        raise NativeBridgeError(
            "not_key",
            "the bound window did not become the key window after a title-bar click; chord not pressed",
            dispatched=True,
        )

    async def hotkey(self, nm: NativeMenu, keys: list[str]) -> NativeEffect:
        """Press a chord with the Driver's explicit foreground delivery (it fronts the window, acts, and
        restores the previous frontmost app): the route for native menu key-equivalents, which ignore a
        background chord. Asked of the posture first; ``key`` is the background route for a chord."""
        if self.last is None or nm.snapshot_id != self.last.snapshot_id:
            raise NativeBridgeError("stale", "hotkey decided on a stale snapshot; reobserve")
        if self.observation_guard is not None:
            await self.observe()
        self.last = None
        self.dispatches += 1
        label = "+".join(keys)
        args: dict[str, Any] = {
            "keys": list(keys),
            "pid": self.pid,
            "window_id": self.window_id,
            "delivery_mode": "foreground",
        }
        if self.session:
            args["session"] = self.session

        async def call() -> Any:
            if sys.platform != "linux":
                await self._front_and_key()
            if self.observation_guard is not None:
                await self.observe()
            return await self.driver.call_tool("hotkey", json.dumps(args))

        eff = await self._foreground("hotkey", -1, label, call, why=f"hotkey {label} (a menu key-equivalent)")
        return await self._after_save(eff, keys=keys)

    async def _after_save(self, eff: NativeEffect, *, keys: Any = (), path: Any = ()) -> NativeEffect:
        if not is_save(keys, path) or not eff.dispatched or eff.effect == "refused":
            return eff
        if sys.platform == "linux":
            return with_save_readback(eff, {
                "ok": None,
                "detail": "Linux automatic saved-document discovery is unavailable; use check-file or "
                          "check-artifact with the explicitly selected path for persistence proof",
            })
        # the app writes the file after the menu action returns; in G5 four of six first Command-S
        # readbacks at 0.5 s read "differs" and the File > Save right after read "saved", so the disk is
        # polled for up to 3 s before a save is called partial
        rb: dict[str, Any] = {}
        for _ in range(6):
            await asyncio.sleep(0.5)
            rb = save_readback(self.ax, self.pid, self.window_id)
            if rb.get("ok") is not False:
                break
        return with_save_readback(eff, rb)

    async def menu(self, nm: NativeMenu, path: list[str]) -> NativeEffect:
        """Invoke an application menu item by path (``["File", "Save"]``). A menu action goes to the app's
        key window and only while the app is active, so this is a foreground step, asked of the posture:
        the bound window is brought to the front, and once it is the app's key window and the person has
        not moved away, the item is pressed through AX, which never re-activates the app (the Driver's
        invoke_menu did, 846 ms after the person had left, Q15 smoke). The front is then handed back.
        invoke_menu remains the route only in exclusive_desktop, for a path AX cannot resolve."""
        if self.last is None or nm.snapshot_id != self.last.snapshot_id:
            raise NativeBridgeError("stale", "menu decided on a stale snapshot; reobserve")
        if self.observation_guard is not None:
            await self.observe()
        self.last = None
        self.dispatches += 1
        label = " > ".join(path)
        if sys.platform == "linux":
            from jevdual.effectors import require_available

            require_available("desktop")
            from jevdual.effectors.cua import invoke_menu_input

            refusal = self.policy.permits("background", why=f"menu {label}")
            if refusal is not None:
                return self._not_sent("menu", -1, label, refusal.code, refusal.reason, "background")
            try:
                outcome = await self.driver.invoke_menu(invoke_menu_input(
                    pid=self.pid, window_id=self.window_id, path=list(path), session=self.session
                ))
            except Exception as exc:  # noqa: BLE001 - delivery may be uncertain
                outcome = exc
            return await self._after_save(self._effect("menu", -1, label, outcome, "background"), path=path)
        ax = self.ax
        preview_path = nm.app_name == "Preview" and path in (
            ["Tools", "Rotate Left"],
            ["Tools", "Rotate Right"],
            ["File", "Save"],
        )

        def preview_owned() -> bool:
            return (
                self.policy._activity().frontmost_pid() == self.pid
                and ax.focused_window_id(self.pid) == self.window_id
            )

        async def call() -> Any:
            preview_before = None
            await self._front_and_key()
            if self.observation_guard is not None:
                await self.observe()
            if preview_path:
                try:
                    if preview_owned():
                        preview_before = ax.preview_document_state(self.pid, self.window_id)
                        if not preview_owned():
                            preview_before = None
                except (ax.AXError, OSError):
                    preview_before = None
            try:
                if preview_path and not preview_owned():
                    raise NativeBridgeError(
                        "not_key", "the exact Preview window lost foreground/key ownership; menu not pressed"
                    )
                ax.press_menu(self.pid, list(path))
            except ax.AXError as exc:
                if exc.reason == "menu_missing" and self.policy.mode == "exclusive_desktop":
                    from jevdual.effectors.cua import invoke_menu_input

                    return await self.driver.invoke_menu(
                        invoke_menu_input(
                            pid=self.pid, window_id=self.window_id, path=list(path), session=self.session
                        )
                    )
                raise
            if preview_before is not None:
                for _ in range(20):
                    try:
                        if not preview_owned():
                            break
                        after = ax.preview_document_state(self.pid, self.window_id)
                        if not preview_owned():
                            break
                        proof = preview_menu_readback(path, preview_before, after)
                    except (ax.AXError, OSError):
                        proof = None
                    if proof is not None:
                        acknowledged = self._effect("menu", -1, label, _PRESSED, "foreground")
                        return dataclasses.replace(
                            acknowledged,
                            effect="confirmed",
                            delivery_basis="ax_menu_effect_readback",
                            native_readback=proof,
                            evidence=(*acknowledged.evidence, "native_ui_readback: " + proof["predicate"]),
                        )
                    await asyncio.sleep(0.05)
            return _PRESSED

        eff = await self._foreground(
            "menu", -1, label, call, why=f"menu {label} (a menu acts on the key window)"
        )
        eff = dataclasses.replace(eff, route=eff.route or ("accessibility" if eff.dispatched else None))
        if eff.delivery_basis == "ax_menu_effect_readback":
            return eff
        return await self._after_save(eff, path=path)

    async def verify(self, predicates: list[Any], *, timeout_ms: int | None = None) -> tuple[str, str]:
        """Run the Driver's ``verify_state`` and return ``(status, text)`` with status one of
        satisfied / unsatisfied / unknown. ``unknown`` never means success."""
        from jevdual.effectors.cua import verify_state_input

        res = await self.driver.verify_state(
            verify_state_input(
                pid=self.pid,
                window_id=self.window_id,
                expect=predicates,
                session=self.session,
                timeout_ms=timeout_ms,
                stable_samples=None,
                include_screenshot=False,
            )
        )
        ver = getattr(res, "verification", None)
        status = _enum_name(getattr(ver, "status", None)) or "unknown"
        return status, str(getattr(res, "text", "") or "")


def is_save(keys: list[str] | tuple[str, ...] = (), path: list[str] | tuple[str, ...] = ()) -> bool:
    """Command-S, or a menu path ending in Save."""
    if keys:
        choices = ({"ctrl", "s"}, {"control", "s"}) if sys.platform == "linux" else ({"cmd", "s"}, {"command", "s"})
        return {k.casefold() for k in keys} in choices
    return bool(path) and path[-1].strip().casefold() == "save"


def save_readback(ax: Any, pid: int, window_id: int) -> dict[str, Any]:
    """After a save: the file the window names (AXDocument) against the window's exact text. A save
    changes nothing a window diff sees, and the Driver reports a chord as ``unverifiable``, so without
    this the verifier cannot tell a saved document from an unsaved one (Q17: every failure on dual and
    guarded was a saved append the verifier would not accept). ``ok`` is True, False or None (no file,
    not one text area, unreadable)."""
    from pathlib import Path

    try:
        path = ax.document_path(pid, window_id)
        values = ax.text_area_values(pid, window_id)
    except Exception as exc:  # noqa: BLE001 - no readback is an honest "unverifiable"
        return {"ok": None, "detail": f"could not read the window: {exc}"[:160]}
    if not path:
        return {"ok": None, "detail": "the window names no file (unsaved document)"}
    if len(values) != 1:
        return {"ok": None, "path": path, "detail": f"the window has {len(values)} text areas"}
    try:
        disk = Path(path).read_text()
    except (OSError, UnicodeDecodeError) as exc:
        return {"ok": None, "path": path, "detail": f"{path} is not readable as text: {exc}"[:160]}
    shown = values[0]
    if disk == shown:
        return {
            "ok": True,
            "path": path,
            "detail": f"{path} holds the window's text exactly ({len(disk)} characters)",
        }
    at = next(
        (i for i, (a, b) in enumerate(zip(disk, shown, strict=False)) if a != b), min(len(disk), len(shown))
    )
    return {"ok": False, "path": path, "detail": f"{path} differs from the window's text at character {at}"}


def with_save_readback(eff: NativeEffect, rb: dict[str, Any]) -> NativeEffect:
    """The save's effect read from the disk: confirmed, partial, or unverifiable, with the reason."""
    word = {True: "confirmed", False: "partial"}.get(rb.get("ok"), "unverifiable")
    prefix = {True: "saved", False: "save not confirmed"}.get(rb.get("ok"), "save unverifiable")
    return dataclasses.replace(
        eff,
        effect=word,
        evidence=(*eff.evidence, f"save_readback: {rb['detail']}"),
        # the foreground report stays first: a save does not erase "front app not restored"
        summary=f"{eff.summary}; {prefix}: {rb['detail']}" if eff.summary else f"{prefix}: {rb['detail']}",
        readback=rb,
    )


async def find_window(driver: Any, app_name: str, *, title_contains: str = "") -> tuple[int, int, str]:
    """``(pid, window_id, title)`` of the largest on-screen titled window of a running app (whose title
    contains ``title_contains`` when given), or raise ``LookupError``."""
    from jevdual.effectors.cua import list_apps_input, list_windows_input

    apps = await driver.list_apps(list_apps_input())
    match = [a for a in apps.apps if a.name == app_name]
    if not match:
        raise LookupError(f"{app_name!r} is not running (Driver list_apps)")
    pid = match[0].pid
    if not pid or pid <= 0 or getattr(match[0], "running", True) is False:
        # the Driver lists installed apps too, with pid 0: say so instead of a window-discovery error
        raise LookupError(f"{app_name!r} is installed but not running; open it first")
    wins = await driver.list_windows(list_windows_input(pid=pid, on_screen_only=True))
    titled = [w for w in wins.windows if w.title]
    if title_contains:
        titled = [w for w in titled if title_contains.casefold() in w.title.casefold()]
    elif not titled:
        titled = list(wins.windows)
    if not titled:
        raise LookupError(
            f"{app_name!r} (pid {pid}) has no on-screen window"
            + (f" titled {title_contains!r}" if title_contains else "")
        )
    w = max(titled, key=lambda w: w.bounds.width * w.bounds.height)
    return pid, w.window_id, w.title


async def find_window_for_pid(driver: Any, pid: int, *, title_contains: str = "") -> tuple[int, str]:
    """``(window_id, title)`` of the largest on-screen titled window of one process (whose title contains
    ``title_contains`` when given), or raise ``LookupError``. Used after ``launch_app`` returned the pid of a
    fresh instance: ``list_apps`` reports one pid per bundle, so a second instance is invisible to it."""
    from jevdual.effectors.cua import list_windows_input

    wins = await driver.list_windows(list_windows_input(pid=pid, on_screen_only=True))
    titled = [w for w in wins.windows if w.title]
    if title_contains:
        titled = [w for w in titled if title_contains.casefold() in w.title.casefold()]
    if not titled:
        raise LookupError(
            f"pid {pid} has no on-screen window" + (f" titled {title_contains!r}" if title_contains else "")
        )
    w = max(titled, key=lambda w: w.bounds.width * w.bounds.height)
    return w.window_id, w.title


BROWSER_APPS = {
    "Google Chrome": "Google Chrome",
    "Safari": "Safari",
    "Chromium": "Chromium",
    "Brave Browser": "Brave Browser",
}


async def open_url(app_name: str, url: str, *, settle_s: float = 3.0) -> str:
    """Open ``url`` in a **new window** of ``app_name`` (AppleScript; Chrome and Safari expose this and
    the Driver has no navigate), wait ``settle_s``, and return the tab's title. A new window lands on
    the current Space in front, so the Driver's on-screen window list gains exactly one id; a new tab
    would go to the app's front window, which can sit on another Space (2026-09-25: the Driver then
    bound the visible window and the run never saw the page)."""
    import asyncio
    import subprocess

    if app_name not in BROWSER_APPS:
        raise ValueError(f"open_url knows Chrome, Safari, Chromium and Brave, not {app_name!r}")
    esc = url.replace("\\", "\\\\").replace('"', '\\"')
    if app_name == "Safari":
        script = (
            f'tell application "Safari"\nactivate\nmake new document with properties {{URL:"{esc}"}}\n'
            f"delay {settle_s}\nget name of current tab of front window\nend tell"
        )
    else:
        script = (
            f'tell application "{app_name}"\nactivate\nset w to make new window\n'
            f'set URL of active tab of w to "{esc}"\ndelay {settle_s}\n'
            f"get title of active tab of w\nend tell"
        )
    proc = await asyncio.create_subprocess_exec(
        "osascript", "-e", script, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"open_url failed: {err.decode(errors='replace').strip()[:200]}")
    return out.decode(errors="replace").strip()


async def app_windows(driver: Any, app_name: str) -> tuple[int, list[tuple[int, str, float]]]:
    """``(pid, [(window_id, title, area)])`` of an app's on-screen windows, as the Driver lists them."""
    from jevdual.effectors.cua import list_apps_input, list_windows_input

    apps = await driver.list_apps(list_apps_input())
    match = [a for a in apps.apps if a.name == app_name]
    if not match:
        raise LookupError(f"{app_name!r} is not running (Driver list_apps)")
    pid = match[0].pid
    wins = await driver.list_windows(list_windows_input(pid=pid, on_screen_only=True))
    return pid, [(w.window_id, w.title or "", float(w.bounds.width * w.bounds.height)) for w in wins.windows]


ADDRESS_BAR_HINTS = ("address", "search or", "url", "location")


def address_bar(nm: NativeMenu) -> Candidate | None:
    """The browser window's address bar on the menu, by label."""
    for c in nm.menu.candidates:
        if c.role in ("textbox", "searchbox") and any(h in c.label.casefold() for h in ADDRESS_BAR_HINTS):
            return c
    return None


async def navigate_in_window(bridge: NativeBridge, url: str, *, settle_s: float = 3.0) -> NativeMenu:
    """Open ``url`` in a new tab of the window the bridge is bound to, through the window itself:
    Command-T, type the URL into the address bar, Return. AppleScript cannot be used for this: with
    two Chrome processes running it addresses one of them and the Driver lists the other
    (2026-09-25, pids 10143 and 18365), and a new tab in the wrong process is a window the Driver
    never sees. Returns the observation after the page had ``settle_s`` to load."""
    import asyncio

    nm = await bridge.observe()
    if address_bar(nm) is None:
        raise LookupError(f"no address bar on {nm.app_name!r}'s window; --url needs a browser window")
    eff = await bridge.hotkey(nm, ["cmd", "t"])
    if not eff.dispatched or eff.effect == "refused":
        # never type the URL into whatever tab is current: that is the person's tab
        raise RuntimeError(f"Command-T not sent ({eff.error_code}): {eff.summary[:120]}")
    await asyncio.sleep(0.8)
    nm = await bridge.observe()
    bar = address_bar(nm)
    if bar is None:
        raise LookupError("no address bar after Command-T")
    await bridge.act(nm, "type", bar.id, text=url)
    nm = await bridge.observe()
    bar = address_bar(nm) or bar
    await bridge.act(nm, "enter", bar.id)
    await asyncio.sleep(settle_s)
    return await bridge.observe()


async def new_window(bridge: NativeBridge, app_name: str, *, settle_s: float = 1.5) -> tuple[int, str]:
    """Open a new window of the bound app through the window itself (Command-N by the foreground route)
    and return ``(window_id, title)`` of the window that appeared in the Driver's on-screen list. A
    session that drives a person's active window fights the person for the tab bar (2026-09-25: the
    active tab changed twice between two commands); its own window keeps the two apart."""
    import asyncio

    _, before = await app_windows(bridge.driver, app_name)
    nm = await bridge.observe()
    eff = await bridge.hotkey(nm, ["cmd", "n"])
    if eff.effect == "refused":
        raise RuntimeError(f"Command-N refused ({eff.error_code}): {eff.summary[:120]}")
    await asyncio.sleep(settle_s)
    _, after = await app_windows(bridge.driver, app_name)
    fresh = [w for w in after if w[0] not in {b[0] for b in before}]
    if not fresh:
        raise LookupError("no new window appeared after Command-N")
    wid, title, _ = fresh[0]
    return wid, title
