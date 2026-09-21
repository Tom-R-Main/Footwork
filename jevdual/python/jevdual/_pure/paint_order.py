"""Pure twin of the R1 port: paint-order occlusion.

Upstream marks removal by setting ``SimplifiedNode.ignored_by_paint_order`` on
the pre-optimization simplified tree (``DOMTreeSerializer._create_simplified_tree``
output); ``_optimize_tree`` then drops those nodes. This twin runs the upstream
remover and returns the removed set as backend_node_ids so equality can compare
plain values. The remover is not idempotent-safe on a mutated tree, so flags are
reset first.
"""

from __future__ import annotations

from browser_use.dom.serializer.paint_order import PaintOrderRemover
from browser_use.dom.views import SimplifiedNode


def _walk(node: SimplifiedNode):
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(n.children)


def paint_order(root: SimplifiedNode) -> frozenset[int]:
    """Return the backend_node_ids that paint-order filtering hides. Mutates ``root`` flags."""
    for n in _walk(root):
        n.ignored_by_paint_order = False
    PaintOrderRemover(root).calculate_paint_order()
    return frozenset(n.original_node.backend_node_id for n in _walk(root) if n.ignored_by_paint_order)
