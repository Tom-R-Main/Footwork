from jevdual import _native

from tests.equality.conftest import assert_equal, require_native, simplified_tree


def test_pure_paint_order_is_deterministic(slug):
    tree, _root = simplified_tree(slug)
    pure = _native.pure("paint_order")
    a = pure(tree)
    b = pure(tree)
    assert a == b


def test_native_paint_order_matches_pure(slug):
    native = require_native("paint_order")
    tree, _root = simplified_tree(slug)
    pure = _native.pure("paint_order")
    expected = pure(tree)
    actual = frozenset(native(tree))
    assert_equal("paint_order", slug, sorted(expected), sorted(actual))
