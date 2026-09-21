from jevdual import _native

from tests.equality.conftest import assert_equal, enhanced_nodes, require_native, simplified_tree


def test_pure_element_hashes_are_deterministic(slug):
    _tree, root = simplified_tree(slug)
    nodes = enhanced_nodes(root)
    pure = _native.pure("element_hashes")
    assert pure(nodes) == pure(nodes)
    assert len(nodes) > 0


def test_native_element_hashes_match_pure(slug):
    native = require_native("element_hashes")
    _tree, root = simplified_tree(slug)
    nodes = enhanced_nodes(root)
    pure = _native.pure("element_hashes")
    assert_equal("element_hashes", slug, pure(nodes), [tuple(t) for t in native(nodes)])
