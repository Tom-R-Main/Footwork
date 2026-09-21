"""Native adapter for R1: paint-order occlusion.

Same signature and return type as the pure twin
``jevdual._pure.paint_order.paint_order(root) -> frozenset[int]``. The tree is
walked once here in pre-order (upstream's ``collect_paint_order`` order), the
CSS transparency rule is evaluated here so its Python float-parsing semantics
are kept, and ``_core.paint_order_flat`` does the rectangle work. Like the twin,
``ignored_by_paint_order`` flags on the tree are reset and then set for the
removed nodes, so this is a drop-in for upstream's ``PaintOrderRemover``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from jevdual import _native

if TYPE_CHECKING:
    from browser_use.dom.views import SimplifiedNode

_FRAME_TAGS = frozenset({"iframe", "frame"})
_TRANSPARENT = "rgba(0, 0, 0, 0)"
_available: bool | None = None


def available() -> bool:
    """True once the real R1 export is built (the placeholder takes no arguments)."""
    global _available
    if _available is None:
        core = _native.core
        try:
            _available = core is not None and core.paint_order_flat([], [], [], [], []) == []
        except (TypeError, NotImplementedError):
            _available = False
    return _available


def _document_context(original_node) -> tuple[str, str | None]:
    parent = original_node.parent_node
    while parent is not None:
        if parent.tag_name in _FRAME_TAGS:
            return str(original_node.session_id), parent.frame_id
        parent = parent.parent_node
    return str(original_node.session_id), None


def _add_to_union(styles) -> bool:
    # Upstream: transparent background or opacity < 0.8 is tested but never added.
    if not styles:
        return True
    if styles.get("background-color", _TRANSPARENT) == _TRANSPARENT:
        return False
    return float(styles.get("opacity", "1")) >= 0.8


def paint_order(root: SimplifiedNode) -> frozenset[int]:
    """Return the backend_node_ids that paint-order filtering hides. Mutates ``root`` flags."""
    # Nodes are handed to the core by position, not by backend_node_id: ids collide across
    # iframe documents (and in upstream's unit tests), and keying by id flagged the wrong node.
    ids: list[int] = []
    rects: list[float] = []
    paint_orders: list[int] = []
    contexts: list[int] = []
    add_flags: list[bool] = []
    context_index: dict[tuple[str, str | None], int] = {}
    with_snapshot: list[SimplifiedNode] = []

    stack = [root]
    while stack:
        node = stack.pop()
        node.ignored_by_paint_order = False
        stack.extend(reversed(node.children))
        snap = node.original_node.snapshot_node
        if not snap or snap.paint_order is None or snap.bounds is None:
            continue
        b = snap.bounds
        ids.append(len(with_snapshot))
        with_snapshot.append(node)
        rects.extend((b.x, b.y, b.x + b.width, b.y + b.height))
        paint_orders.append(snap.paint_order)
        ctx = _document_context(node.original_node)
        contexts.append(context_index.setdefault(ctx, len(context_index)))
        add_flags.append(_add_to_union(snap.computed_styles))

    removed_positions = _native.core.paint_order_flat(ids, rects, paint_orders, contexts, add_flags)
    removed_ids: set[int] = set()
    for pos in removed_positions:
        node = with_snapshot[pos]
        node.ignored_by_paint_order = True
        removed_ids.add(node.original_node.backend_node_id)
    return frozenset(removed_ids)
