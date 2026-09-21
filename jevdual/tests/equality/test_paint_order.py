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
