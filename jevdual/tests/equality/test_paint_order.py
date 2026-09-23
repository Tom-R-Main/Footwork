import pytest
from jevdual import _native

from tests.equality.conftest import assert_equal, simplified_tree


def _require_native_paint_order():
    # R1 ships as an adapter (jevdual._adapters.paint_order) over _core.paint_order_flat,
    # so resolution goes through _resolve rather than conftest.require_native, which
    # only looks for a same-signature _core export.
    kind, fn = _native._resolve("paint_order")
    if kind != "native":
        pytest.skip("native not built for paint_order")
    return fn


def test_pure_paint_order_is_deterministic(slug):
    tree, _root = simplified_tree(slug)
    pure = _native.pure("paint_order")
    a = pure(tree)
    b = pure(tree)
    assert a == b


def test_native_paint_order_matches_pure(slug):
    native = _require_native_paint_order()
    tree, _root = simplified_tree(slug)
    pure = _native.pure("paint_order")
    expected = pure(tree)
    actual = frozenset(native(tree))
    assert_equal("paint_order", slug, sorted(expected), sorted(actual))
    # The adapter is a drop-in for upstream's remover: flags on the tree must match too.
    flagged = frozenset(n.original_node.backend_node_id for n in _walk(tree) if n.ignored_by_paint_order)
    assert flagged == expected


def _walk(node):
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(n.children)


def test_native_flags_the_covered_node_when_backend_ids_collide():
    """Upstream's own test (tests/ci/test_dom_paint_order_serialization.py) builds two text nodes at the
    same bounds with the same backend_node_id; the lower paint order must be the one flagged. Ids also
    collide across iframe documents on real pages, so the adapter must key nodes by position."""
    import pytest
    from browser_use.dom.views import (
        DOMRect,
        EnhancedDOMTreeNode,
        EnhancedSnapshotNode,
        NodeType,
        SimplifiedNode,
    )
    from jevdual import _native

    native = _native.native("paint_order")
    if native is None:
        pytest.skip("native paint_order not built")

    def snap(order: int) -> EnhancedSnapshotNode:
        return EnhancedSnapshotNode(
            is_clickable=None,
            cursor_style=None,
            bounds=DOMRect(x=0, y=0, width=100, height=20),
            clientRects=None,
            scrollRects=None,
            computed_styles={"background-color": "rgb(255, 255, 255)", "opacity": "1"},
            paint_order=order,
            stacking_contexts=None,
        )

    def node(order: int, text: str) -> EnhancedDOMTreeNode:
        return EnhancedDOMTreeNode(
            node_id=1,
            backend_node_id=1,
            node_type=NodeType.TEXT_NODE,
            node_name="#text",
            node_value=text,
            attributes={},
            is_scrollable=None,
            is_visible=True,
            absolute_position=None,
            target_id="t",
            frame_id=None,
            session_id="s",
            content_document=None,
            shadow_root_type=None,
            shadow_roots=None,
            parent_node=None,
            children_nodes=None,
            ax_node=None,
            snapshot_node=snap(order),
        )

    hidden = SimplifiedNode(original_node=node(1, "HIDDEN"), children=[])
    top = SimplifiedNode(original_node=node(2, "TOP"), children=[])
    wrapper = SimplifiedNode(original_node=node(0, ""), children=[hidden, top], should_display=False)
    wrapper.original_node.snapshot_node = None
    native(wrapper)
    assert hidden.ignored_by_paint_order is True
    assert top.ignored_by_paint_order is False
