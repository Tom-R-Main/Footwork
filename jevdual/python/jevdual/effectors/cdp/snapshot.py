"""Compose a semantic page snapshot from Chrome's accessibility tree, DOM and layout.

The output is the ``semantic_v2`` shape ``browser_driver.menu_from_semantic`` already reads (``page``,
``snapshot``, ``refs``, ``content_refs``), so the bridge, menus and receipts do not change with the
effector. The role, action, state, visibility and hiding rules follow CUA's
``cua-driver-core/src/browser/semantic.rs`` at d5373879 (``compose_accessibility_tree``,
``action_kinds``, ``ax_states``, ``classify_visibility``, ``statically_hidden``,
``remove_redundant_static_text``). Not ported, and therefore reported rather than assumed: page
occlusion, DOM-supplemented custom click targets, scroll and pointer actions, query ranking.

Only the main frame is observed. Child-frame content is counted in ``snapshot.omitted.child_frames``
and the snapshot is marked incomplete, never silently absent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: computed styles requested from DOMSnapshot, in this order
STYLES = ("display", "visibility", "opacity", "pointer-events", "cursor")
#: CUA's DEFAULT_SEMANTIC_NODE_BUDGET and MAX_SEMANTIC_TEXT_CHARS
REF_BUDGET = 300
MAX_TEXT = 1000
NEAR_VIEWPORT_MARGIN = 1000.0
#: browser-use 0.13.14 dom/enhanced_snapshot.py _SENSITIVE_INPUT_TYPES/_AUTOCOMPLETE_PREFIXES, the rule
#: jevdual.menu applies today. Chrome reports a password's value as one bullet per character, so the
#: whole value is withheld, length included.
SENSITIVE_INPUT_TYPES = frozenset({"password", "file", "hidden"})
SENSITIVE_AUTOCOMPLETE_PREFIXES = ("cc-", "one-time-code")

_CLICK_ROLES = frozenset({
    "button", "link", "checkbox", "radio", "switch", "tab", "menuitem", "menuitemcheckbox",
    "menuitemradio", "option", "treeitem", "slider", "spinbutton", "combobox", "listbox", "summary",
})
_KEPT_STATES = ("checked", "disabled", "editable", "expanded", "focused", "focusable", "pressed", "required",
                "selected")
_CONTENT_ROLES = frozenset({"statictext", "heading", "link", "listitem", "cell", "paragraph"})
_ZERO_WIDTH = dict.fromkeys(map(ord, "﻿\u200b‌‍⁠   "), " ")


@dataclass
class DomMeta:
    tag: str
    attrs: dict[str, str]
    order: int
    hidden: bool
    transparent: bool


@dataclass
class Layout:
    bounds: tuple[float, float, float, float] | None
    styles: dict[str, str] = field(default_factory=dict)


def _attributes(node: dict[str, Any]) -> dict[str, str]:
    raw = node.get("attributes") or []
    return {str(raw[i]).lower(): str(raw[i + 1]) for i in range(0, len(raw) - 1, 2)}


def _hiding_style(prop: str, value: str) -> bool:
    value = value.strip().removesuffix("!important").strip().lower()
    prop = prop.strip().lower()
    if prop == "display":
        return value == "none"
    if prop == "visibility":
        return value == "hidden"
    if prop == "opacity":
        try:
            return float(value) <= 0
        except ValueError:
            return False
    return False


def _inline(attrs: dict[str, str]) -> list[tuple[str, str]]:
    out = []
    for declaration in attrs.get("style", "").split(";"):
        if ":" in declaration:
            prop, _, value = declaration.partition(":")
            out.append((prop, value))
    return out


def dom_index(document: dict[str, Any]) -> dict[int, DomMeta]:
    """Main-frame elements by backend node id, in document order (semantic.rs build_dom_index)."""
    index: dict[int, DomMeta] = {}
    order = 0

    def walk(node: dict[str, Any], hidden: bool, transparent: bool) -> None:
        nonlocal order
        attrs = _attributes(node)
        hidden = hidden or "hidden" in attrs or attrs.get("aria-hidden") == "true" or any(
            _hiding_style(p, v) for p, v in _inline(attrs)
        )
        transparent = transparent or any(p.strip().lower() == "opacity" and _hiding_style(p, v)
                                         for p, v in _inline(attrs))
        backend = node.get("backendNodeId")
        if isinstance(backend, int):
            index[backend] = DomMeta(str(node.get("nodeName") or "").lower(), attrs, order, hidden, transparent)
            order += 1
        for child in node.get("children") or []:
            walk(child, hidden, transparent)
        for shadow in node.get("shadowRoots") or []:
            if shadow.get("shadowRootType") != "user-agent":
                walk(shadow, hidden, transparent)
        # contentDocument belongs to a child frame: not observed here

    walk(document.get("root") or {}, False, False)
    return index


def layout_index(snapshot: dict[str, Any]) -> dict[int, Layout]:
    strings = snapshot.get("strings") or []
    documents = snapshot.get("documents") or []
    if not documents:
        return {}
    doc = documents[0]  # the main frame's document
    backend_ids = (doc.get("nodes") or {}).get("backendNodeId") or []
    layout = doc.get("layout") or {}
    out: dict[int, Layout] = {}
    for j, node_index in enumerate(layout.get("nodeIndex") or []):
        if not 0 <= node_index < len(backend_ids):
            continue
        bounds = (layout.get("bounds") or [])[j] if j < len(layout.get("bounds") or []) else None
        styles = {}
        row = (layout.get("styles") or [])[j] if j < len(layout.get("styles") or []) else []
        for name, idx in zip(STYLES, row, strict=False):
            if isinstance(idx, int) and 0 <= idx < len(strings):
                styles[name] = strings[idx]
        out[backend_ids[node_index]] = Layout(
            tuple(bounds[:4]) if isinstance(bounds, list) and len(bounds) >= 4 else None, styles
        )
    return out


def _clean(value: Any) -> str | None:
    if isinstance(value, bool):
        value = str(value).lower()
    elif isinstance(value, (int, float)):
        value = str(value)
    if not isinstance(value, str):
        return None
    text = " ".join(value.translate(_ZERO_WIDTH).split())
    text = "".join(" " if "" <= ch <= "" else ch for ch in text)
    return text[:MAX_TEXT] or None


def _ax_value(prop: Any) -> Any:
    return prop.get("value") if isinstance(prop, dict) else None


def _states(node: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for prop in node.get("properties") or []:
        name = prop.get("name")
        if name in _KEPT_STATES:
            out[name] = _ax_value(prop.get("value"))
    return out


def _visibility(dom: DomMeta | None, layout: Layout | None, viewport: tuple[float, float, float, float] | None) -> str:
    rendered = layout is not None and layout.bounds is not None and layout.bounds[2] > 0 and layout.bounds[3] > 0
    if (dom is not None and (dom.transparent or (dom.hidden and not rendered))) or (
        layout is not None and any(_hiding_style(p, v) for p, v in layout.styles.items())
    ):
        return "css_hidden"
    if layout is None:
        return "unknown"
    if not rendered:
        return "no_layout"
    if viewport is None:
        return "unknown"
    x, y, w, h = layout.bounds  # type: ignore[misc]
    vx, vy, vw, vh = viewport

    def meets(m: float) -> bool:
        return x < vx + vw + m and x + w > vx - m and y < vy + vh + m and y + h > vy - m

    if meets(0):
        return "in_viewport"
    return "near_viewport" if meets(NEAR_VIEWPORT_MARGIN) else "offscreen"


def _actions(role: str, dom: DomMeta | None, states: dict[str, Any]) -> list[str]:
    if states.get("disabled") is True:
        return []
    actions = ["click"] if role in _CLICK_ROLES else []
    tag = dom.tag if dom else ""
    editable = states.get("editable")
    editable = editable is True or (isinstance(editable, str) and editable != "false") or (
        dom is not None and dom.attrs.get("contenteditable", "x").lower() in ("", "true")
    )
    if tag == "input" and dom is not None and dom.attrs.get("type", "").lower() == "file":
        actions.append("upload")
    elif role in ("textbox", "searchbox") or tag in ("input", "textarea") or editable:
        actions.append("type")
    return actions


def _sensitive(dom: DomMeta | None) -> bool:
    if dom is None or dom.tag != "input":
        return False
    return dom.attrs.get("type", "").lower() in SENSITIVE_INPUT_TYPES or dom.attrs.get(
        "autocomplete", ""
    ).lower().startswith(SENSITIVE_AUTOCOMPLETE_PREFIXES)


@dataclass(frozen=True)
class Composed:
    semantic: dict[str, Any]
    #: ref -> backend DOM node id, for the caller's identity binding
    backend: dict[str, int]


def compose(
    *, snapshot_id: str, url: str, ax: dict[str, Any], document: dict[str, Any], dom_snapshot: dict[str, Any],
    metrics: dict[str, Any], child_frames: int,
) -> Composed:
    dom = dom_index(document)
    layout = layout_index(dom_snapshot)
    vp = metrics.get("cssVisualViewport") or metrics.get("cssLayoutViewport") or {}
    viewport = (
        (float(vp.get("pageX", 0)), float(vp.get("pageY", 0)), float(vp["clientWidth"]), float(vp["clientHeight"]))
        if "clientWidth" in vp and "clientHeight" in vp else None
    )
    nodes = ax.get("nodes")
    if not isinstance(nodes, list):
        return Composed({"status": "ok", "page": {"url": url},
                         "snapshot": {"id": snapshot_id, "complete": False}, "refs": []}, {})
    names = {n.get("nodeId"): _clean(_ax_value(n.get("name"))) for n in nodes if isinstance(n, dict)}
    title = None
    composed = []
    for fallback, node in enumerate(nodes):
        if not isinstance(node, dict) or node.get("ignored") is True or not node.get("nodeId"):
            continue
        role = (_clean(_ax_value(node.get("role"))) or "unknown").lower()
        if role == "inlinetextbox":
            continue
        name = names.get(node["nodeId"])
        if role in ("rootwebarea", "webarea"):
            title = title or name
        if role in ("statictext", "text") and (name is None or names.get(node.get("parentId")) == name):
            continue  # semantic.rs remove_redundant_static_text
        backend = node.get("backendDOMNodeId")
        if isinstance(backend, int) and backend not in dom:
            # The node lies in a user-agent shadow tree: a control's own internals, such as an input's
            # inner editor and its text. They are part of the host control, never candidates or labels;
            # a password's inner text is one bullet per character. Observed on Chrome 156, 2026-10-31.
            continue
        meta = dom.get(backend) if isinstance(backend, int) else None
        states = _states(node)
        value = None if _sensitive(meta) else _clean(_ax_value(node.get("value")))
        composed.append({
            "order": meta.order if meta else len(dom) + fallback,
            "backend": backend if isinstance(backend, int) else None,
            "role": role, "name": name, "value": value, "states": states,
            "visibility": _visibility(meta, layout.get(backend) if isinstance(backend, int) else None, viewport),
            "actions": _actions(role, meta, states),
        })
    composed.sort(key=lambda n: n["order"])
    visible = [n for n in composed if n["visibility"] != "css_hidden"]
    actionable = [n for n in visible if n["actions"] and n["backend"] is not None]
    refs, backend_of = [], {}
    for i, n in enumerate(actionable[:REF_BUDGET], start=1):
        ref = f"{snapshot_id}:{i}"
        backend_of[ref] = n["backend"]
        entry = {"ref": ref, "role": n["role"], "name": n["name"], "actions": n["actions"],
                 "states": n["states"], "visibility": n["visibility"]}
        if n["value"] is not None:
            entry["value"] = n["value"]
        refs.append(entry)
    content = [{"role": n["role"], "name": n["name"]} for n in visible
               if n["name"] and n["role"] in _CONTENT_ROLES]
    omitted = {
        "css_hidden": sum(1 for n in composed if n["visibility"] == "css_hidden"),
        "offscreen": sum(1 for n in visible if n["visibility"] == "offscreen"),
        "no_layout": sum(1 for n in visible if n["visibility"] == "no_layout"),
        "unknown": sum(1 for n in visible if n["visibility"] == "unknown"),
        "budget": max(0, len(actionable) - REF_BUDGET),
        "child_frames": child_frames,
        "custom_controls_unobserved": 1,  # semantic.rs supplement_dom_actions and occlusion are not ported
    }
    return Composed(
        {
            "status": "ok",
            "page": {"url": url, "title": title or ""},
            "snapshot": {"id": snapshot_id, "complete": child_frames == 0 and not omitted["budget"],
                         "omitted": omitted},
            "refs": refs,
            "content_refs": content,
        },
        backend_of,
    )
