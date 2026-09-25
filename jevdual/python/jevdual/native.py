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
  was decided from, refusing a stale menu. Every dispatch returns a :class:`NativeEffect` that
  carries the Driver's own ``effect``/``route``/``evidence`` verbatim; ``confirmed`` is the
  Driver's word, never ours.

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
import re
from dataclasses import dataclass, field
from typing import Any

from jevdual.menu import Candidate, Menu, MenuBudget, Operation, estimate_tokens

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

    def token(self, id: int) -> str | None:
        return self.tokens.get(id)


def _checked(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in ("1", "true", "on", "checked"):
        return True
    if s in ("0", "false", "off", "unchecked"):
        return False
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


def _prune(
    candidates: list[Candidate],
    tokens: dict[int, str],
    frames: dict[int, tuple[float, float, float, float]],
    omitted: dict[str, int],
    budget: MenuBudget,
) -> tuple[list[Candidate], dict[int, str], dict[int, tuple[float, float, float, float]]]:
    """Drop what System 1 cannot choose between: a control whose label is only its role (``button
    'button'``) unless it is a text field, and repeats of the same (role, label, value, section) beyond
    the first (a page with 27 identical "More actions" buttons offers one). Then cap the count."""
    kept: list[Candidate] = []
    seen: set[tuple[str, str, str | None, str | None]] = set()
    for c in candidates:
        if c.label == c.role and c.role not in _TEXT_ROLES:
            omitted["unnamed"] = omitted.get("unnamed", 0) + 1
            continue
        key = (c.role, c.label, c.value, c.section)
        if key in seen:
            omitted["duplicate"] = omitted.get("duplicate", 0) + 1
            continue
        seen.add(key)
        kept.append(c)
    if len(kept) > NATIVE_MENU_CAP:
        omitted["cap"] = len(kept) - NATIVE_MENU_CAP
        kept = kept[:NATIVE_MENU_CAP]
    ids = {c.id for c in kept}
    return kept, {i: t for i, t in tokens.items() if i in ids}, {i: f for i, f in frames.items() if i in ids}


def menu_from_snapshot(
    snapshot: Any,
    *,
    budget: MenuBudget | None = None,
    include_menu_bar: bool = False,
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
    candidates: list[Candidate] = []
    tokens: dict[int, str] = {}
    frames: dict[int, tuple[float, float, float, float]] = {}
    values: dict[int, str] = {}
    ax_roles: dict[int, str] = {}
    omitted: dict[str, int] = {}
    for el in elements:
        token = _get(el, "element_token")
        idx = _get(el, "element_index")
        if not token or idx is None:
            continue
        ax_role = str(_get(el, "role") or "")
        if ax_role == "AXWindow":
            continue
        if not include_menu_bar and _in_menu_bar(el, by_index):
            omitted["menu_bar"] = omitted.get("menu_bar", 0) + 1
            continue
        actions = {str(a) for a in (_get(el, "actions") or ())}
        mapped = ROLE_MAP.get(ax_role)
        if mapped is None and ax_role == "AXImage" and "AXOpen" in actions:
            # a Finder icon-view item: an image that opens (P0 breadth, 2026-09-25); clicking selects it
            mapped = ("file", ("click",))
        if mapped is None:
            if "AXPress" not in actions:
                omitted["unmapped_role"] = omitted.get("unmapped_role", 0) + 1
                continue
            mapped = (ax_role.removeprefix("AX").lower() or "element", ("click",))
        role, ops = mapped
        if role == "menuitem" and "AXPress" not in actions and "AXPick" not in actions:
            omitted["inert_menu_item"] = omitted.get("inert_menu_item", 0) + 1
            continue
        if _get(el, "enabled") is False:
            omitted["disabled"] = omitted.get("disabled", 0) + 1
            continue
        raw_value = _get(el, "value")
        label = _clean(_get(el, "label"), _LABEL_CAP)
        if not label:
            label = _clean(_get(el, "value_description"), _LABEL_CAP)
        if not label and role not in _TEXT_ROLES:
            label = _clean(raw_value, _LABEL_CAP)
        if not label:
            label = role
        sensitive = ax_role == "AXSecureTextField"
        multiline = ax_role == "AXTextArea"
        if role in _TEXT_ROLES and raw_value not in (None, "") and label == _clean(raw_value, _LABEL_CAP):
            label = "text area" if multiline else role  # the Driver echoed the content as the label
        value: str | None = None
        if role in _TEXT_ROLES and not sensitive and raw_value not in (None, ""):
            value = (
                _clean_multiline(raw_value, _VALUE_CAP * 4) if multiline else _clean(raw_value, _VALUE_CAP)
            )
        checked = _checked(raw_value) if role in ("checkbox", "radio", "switch") else None
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
        if role in _TEXT_ROLES and not sensitive and raw_value is not None:
            values[cand.id] = str(raw_value)
        if frame is not None:
            fx, fy, fw, fh = (_get(frame, k) for k in ("x", "y", "w", "h"))
            if None not in (fx, fy, fw, fh):
                frames[cand.id] = (float(fx), float(fy), float(fw), float(fh))

    candidates, tokens, frames = _prune(candidates, tokens, frames, omitted, b)
    kept = {c.id for c in candidates}
    values = {i: v for i, v in values.items() if i in kept}
    ax_roles = {i: r for i, r in ax_roles.items() if i in kept}
    app_name = str(_get(snapshot, "app_name") or "")
    title = _clean(_get(snapshot, "window_title"), 120)
    page_text = _page_text(_get(snapshot, "tree_markdown"), elements, b.max_page_text_chars)
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
    )


# ---------------------------------------------------------------------------
# Execution through the Driver
# ---------------------------------------------------------------------------


class NativeBridgeError(Exception):
    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason


@dataclass(frozen=True)
class NativeEffect:
    """The Driver's account of one dispatched action, verbatim. ``effect`` is one of the Driver's
    words (confirmed, partial, unverifiable, suspected_noop, refused); ``ok`` is our reading of it.

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
        }
        if self.foreground is not None:
            rec["foreground"] = dict(self.foreground)
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
    code = getattr(result, "error_code", None)
    delivered = _enum_name(getattr(getattr(action, "delivery", None), "mode", None))
    if getattr(result, "is_error", False) and effect not in ("refused",):
        effect = "refused"
    return NativeEffect(
        operation, target, label, effect, route, evidence, summary, code, driver_delivery=delivered
    )


#: the Driver's refusal when a process owns several eligible windows and a process-scoped key event
#: cannot be proven to reach the bound one (measured 2026-09-25: an element token does not lift it)
AMBIGUITY = "same_pid_keyboard_ambiguity"
_TEXT_EDIT_ROLES = frozenset({"AXTextArea", "AXTextField", "AXComboBox", "AXSearchField"})


def _refusal_text(outcome: Any) -> str:
    if isinstance(outcome, BaseException):
        return str(outcome)
    if getattr(outcome, "is_error", False):
        return str(getattr(outcome, "text", "") or "")
    return ""


def _norm_tail(s: str) -> str:
    """The comparison the Driver's value supports: it strips trailing whitespace."""
    return s.rstrip()


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
    ):
        from jevdual.posture import ExecutionPolicy

        self.driver = driver
        self.pid = pid
        self.window_id = window_id
        self.session = session
        self.policy = policy if policy is not None else ExecutionPolicy("background_only")
        self.live_check = live_check
        self._ax = ax
        self.last: NativeMenu | None = None
        self.dispatches = 0

    @property
    def ax(self) -> Any:
        if self._ax is None:
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
        from cua_driver import GetWindowStateInput

        snap = await self.driver.get_window_state(
            GetWindowStateInput(
                pid=self.pid,
                window_id=self.window_id,
                session=self.session,
                query=query,
                include_accessibility_tree=True,
                include_screenshot=screenshot_path is not None,
                screenshot_out_file=screenshot_path,
                max_elements=max_elements,
                max_depth=None,
                max_dimension=None,
            )
        )
        self.last = menu_from_snapshot(snap, budget=budget, include_menu_bar=include_menu_bar)
        return self.last

    def _target(self) -> Any:
        from cua_driver import ActionTarget

        return ActionTarget.WINDOW(pid=self.pid, window_id=self.window_id)

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
        if same is not None and (same.role, same.label, same.section) == key:
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
        if cand.checked is not None and hit.checked != cand.checked:
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
        )

    def _effect(self, operation: str, target: int, label: str, outcome: Any, delivery: str) -> NativeEffect:
        if isinstance(outcome, BaseException):
            code = getattr(outcome, "code", None) or type(outcome).__name__
            return NativeEffect(
                operation,
                target,
                label,
                "refused",
                None,
                (),
                str(outcome)[:200],
                str(code),
                delivery=delivery,
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
        before = self.policy.before_foreground()
        try:
            outcome = await call()
        except Exception as exc:  # noqa: BLE001 - refusal is evidence
            outcome = exc
        # Give the front back when our window still holds it (bring_to_front leaves it there). When the
        # person has moved to a third app meanwhile, that is their choice: never fight it.
        front_before = before.get("front_before")
        now = self.policy._activity().frontmost_pid()
        if now == self.pid and front_before not in (None, self.pid):
            try:
                await self.driver.call_tool("bring_to_front", json.dumps({"pid": front_before}))
                before = {**before, "handed_back": front_before}
            except Exception as exc:  # noqa: BLE001 - reported on the receipt, never retried
                before = {**before, "hand_back_failed": str(exc)[:80]}
        rec = self.policy.after_foreground(before)
        eff = self._effect(operation, target, label, outcome, "foreground")
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
        except Exception as exc:  # noqa: BLE001 - refusal is evidence
            outcome = exc
        if AMBIGUITY not in _refusal_text(outcome):
            return self._effect(operation, target, label, outcome, "background")
        fg = {**args, "delivery_mode": "foreground"}
        eff = await self._foreground(
            operation,
            target,
            label,
            lambda: self.driver.call_tool("press_key", json.dumps(fg)),
            why=f"{label} (the process owns other windows, so a background key cannot be proven to reach this one; {AMBIGUITY})",
        )
        if not eff.dispatched:
            return dataclasses.replace(eff, evidence=(*eff.evidence, f"background: {AMBIGUITY}"))
        return eff

    async def _append(self, nm: NativeMenu, id: int, cand: Candidate, text: str) -> NativeEffect:
        """Insert at the end of the exact value through AX and require ``after == before + inserted``.
        Nothing is rebuilt from a preview; a value that no longer matches the decision is refused before
        writing."""
        role = nm.ax_roles.get(id, "AXTextArea")
        frame = nm.frames.get(id)
        ax = self.ax
        try:
            el = ax.resolve(self.pid, self.window_id, role, ax.Frame(*frame) if frame else None)
            exact = ax.value(el)
            if _norm_tail(exact) != _norm_tail(nm.values.get(id, "")):
                return self._not_sent(
                    "append",
                    id,
                    cand.label,
                    "precondition_changed",
                    "the field holds different text than when the step was decided; nothing written",
                    "background",
                )
            sep = "" if exact == "" or exact.endswith("\n") else "\n"
            before, after = ax.insert_at_end(el, sep + text, expect=exact)
        except ax.AXError as exc:
            return NativeEffect(
                "append",
                id,
                cand.label,
                "refused",
                "accessibility",
                (),
                str(exc)[:200],
                exc.reason,
                delivery="background",
                dispatched=exc.reason
                not in (
                    "precondition_changed",
                    "element_missing",
                    "element_ambiguous",
                    "window_missing",
                    "no_value",
                ),
            )
        inserted = sep + text
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
            )
        want = before + inserted
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
        )

    async def _click_token(self, token: str) -> Any:
        from cua_driver import ClickInput, ClickPosition, InputDeliveryMode

        return await self.driver.click(
            ClickInput(
                target=self._target(),
                position=ClickPosition.ELEMENT(element_token=token),
                delivery_mode=InputDeliveryMode.BACKGROUND,
                session=self.session,
                button=None,
                count=None,
            )
        )

    async def act(self, nm: NativeMenu, operation: str, id: int, text: str | None = None) -> NativeEffect:
        """Dispatch exactly one operation. The caller must reobserve afterwards; ``self.last`` is
        cleared so a second act on the same snapshot is refused as stale."""
        cand, token = self._require_fresh(nm, id)
        if operation not in cand.operations:
            raise NativeBridgeError(
                "unknown_operation", f"{operation!r} is not offered on [{id}] {cand.label!r} ({cand.role})"
            )
        if operation in ("type", "append") and text is None:
            raise NativeBridgeError("text_required", f"{operation} on [{id}] needs a value")
        if self.live_check:
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
            return await self._append(nm, id, cand, text)
        if operation in ("enter",):
            return await self._key_route("enter", id, label, "return", [], token)
        if operation == "hover":
            refusal = self.policy.permits("desktop", why=f"hover on {label!r} (it moves the real pointer)")
            if refusal is not None:
                return self._not_sent("hover", id, label, refusal.code, refusal.reason, "desktop")
            fx, fy, fw, fh = nm.frames.get(id, (0.0, 0.0, 0.0, 0.0))
            try:
                outcome = await self.driver.call_tool(
                    "move_cursor", json.dumps({"x": fx + fw / 2, "y": fy + fh / 2, "scope": "desktop"})
                )
            except Exception as exc:  # noqa: BLE001
                outcome = exc
            return self._effect("hover", id, label, outcome, "desktop")
        try:
            if operation == "click":
                outcome: Any = await self._click_token(token)
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
                if _refusal_text(outcome):
                    # a wheel the Driver will not aim at this element: Page Down to the element instead,
                    # through the key route and so through the posture (2026-09-25: a Chrome list refused)
                    return await self._key_route("scroll", id, label, "pagedown", [], token)
            else:
                raise NativeBridgeError("unsupported", f"{operation!r} has no native dispatch yet")
        except NativeBridgeError:
            raise
        except Exception as exc:  # noqa: BLE001 - DriverError.Tool carries the refusal; keep it as evidence
            log.info("native %s on [%s] refused: %s", operation, id, exc)
            if self.dispatches == 1 and "-25204" in str(exc) and operation == "click":
                # The first AX press of a fresh runtime fails with kAXErrorCannotComplete on every
                # launch seen so far (Calculator, 2026-09-24); a refusal carries no delivery, so one
                # retry on a fresh snapshot is not a blind replay. Recorded in the effect summary.
                fresh = await self.observe()
                again = fresh.menu.candidate(id)
                if again is not None and fresh.token(id) is not None:
                    eff = await self.act(fresh, operation, id, text)
                    return dataclasses.replace(
                        eff, summary=f"retried after first-press -25204; {eff.summary}"[:200]
                    )
            return self._effect(operation, id, label, exc, "background")
        return self._effect(operation, id, label, outcome, "background")

    async def key(self, nm: NativeMenu, key: str, modifiers: list[str] | None = None) -> NativeEffect:
        """Press one key or chord in the window in the background (System 2 only; System 1's menu has no
        key operation). Needs the foreground only when the process owns other windows."""
        mods = [{"command": "cmd", "option": "alt", "control": "ctrl"}.get(m, m) for m in (modifiers or [])]
        if self.last is None or nm.snapshot_id != self.last.snapshot_id:
            raise NativeBridgeError("stale", "key press decided on a stale snapshot; reobserve")
        self.last = None
        self.dispatches += 1
        return await self._key_route("key", -1, "+".join([*mods, key]), key, mods, None)

    async def _front(self) -> None:
        """Explicit foreground escalation: bring the bound window to the front (recorded by the caller)."""
        await self.driver.call_tool(
            "bring_to_front", json.dumps({"pid": self.pid, "window_id": self.window_id})
        )

    async def hotkey(self, nm: NativeMenu, keys: list[str]) -> NativeEffect:
        """Press a chord with the Driver's explicit foreground delivery (it fronts the window, acts, and
        restores the previous frontmost app): the route for native menu key-equivalents, which ignore a
        background chord. Asked of the posture first; ``key`` is the background route for a chord."""
        if self.last is None or nm.snapshot_id != self.last.snapshot_id:
            raise NativeBridgeError("stale", "hotkey decided on a stale snapshot; reobserve")
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
        return await self._foreground(
            "hotkey",
            -1,
            label,
            lambda: self.driver.call_tool("hotkey", json.dumps(args)),
            why=f"hotkey {label} (a menu key-equivalent)",
        )

    async def menu(self, nm: NativeMenu, path: list[str]) -> NativeEffect:
        """Invoke an application menu item by path (``["File", "Save"]``) through ``invoke_menu``, which
        needs the window key and frontmost, so the window is brought to the front first. Asked of the
        posture first."""
        from cua_driver import InvokeMenuInput

        if self.last is None or nm.snapshot_id != self.last.snapshot_id:
            raise NativeBridgeError("stale", "menu decided on a stale snapshot; reobserve")
        self.last = None
        self.dispatches += 1
        label = " > ".join(path)

        async def call() -> Any:
            await self._front()
            await asyncio.sleep(0.4)  # activation settles before invoke_menu checks key/frontmost
            return await self.driver.invoke_menu(
                InvokeMenuInput(pid=self.pid, window_id=self.window_id, path=list(path), session=self.session)
            )

        eff = await self._foreground(
            "menu", -1, label, call, why=f"menu {label} (invoke_menu needs the window key)"
        )
        return dataclasses.replace(eff, route=eff.route or ("foreground" if eff.dispatched else None))

    async def verify(self, predicates: list[Any], *, timeout_ms: int | None = None) -> tuple[str, str]:
        """Run the Driver's ``verify_state`` and return ``(status, text)`` with status one of
        satisfied / unsatisfied / unknown. ``unknown`` never means success."""
        from cua_driver import VerifyStateInput

        res = await self.driver.verify_state(
            VerifyStateInput(
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


async def find_window(driver: Any, app_name: str, *, title_contains: str = "") -> tuple[int, int, str]:
    """``(pid, window_id, title)`` of the largest on-screen titled window of a running app (whose title
    contains ``title_contains`` when given), or raise ``LookupError``."""
    from cua_driver import ListAppsInput, ListWindowsInput

    apps = await driver.list_apps(ListAppsInput())
    match = [a for a in apps.apps if a.name == app_name]
    if not match:
        raise LookupError(f"{app_name!r} is not running (Driver list_apps)")
    pid = match[0].pid
    if not pid or pid <= 0 or getattr(match[0], "running", True) is False:
        # the Driver lists installed apps too, with pid 0: say so instead of a window-discovery error
        raise LookupError(f"{app_name!r} is installed but not running; open it first")
    wins = await driver.list_windows(ListWindowsInput(pid=pid, on_screen_only=True))
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
    from cua_driver import ListWindowsInput

    wins = await driver.list_windows(ListWindowsInput(pid=pid, on_screen_only=True))
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
    from cua_driver import ListAppsInput, ListWindowsInput

    apps = await driver.list_apps(ListAppsInput())
    match = [a for a in apps.apps if a.name == app_name]
    if not match:
        raise LookupError(f"{app_name!r} is not running (Driver list_apps)")
    pid = match[0].pid
    wins = await driver.list_windows(ListWindowsInput(pid=pid, on_screen_only=True))
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
