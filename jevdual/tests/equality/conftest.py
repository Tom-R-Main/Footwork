"""Equality harness: every native hot path must agree with its pure twin on every fixture.

Tests SKIP (never silently pass) when the native export is not built yet, and when
the replay helper (task C1) is not available for the tree-based ports.
"""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest
from jevdual import _native

from tests.fixtures.loader import fixture_slugs, load_fixture


def pytest_generate_tests(metafunc):
    if "slug" in metafunc.fixturenames:
        metafunc.parametrize("slug", fixture_slugs())


@pytest.fixture
def fixture(slug):
    return load_fixture(slug)


def require_native(name: str):
    fn = _native.native(name)
    if fn is None:
        pytest.skip(f"native not built for {name}")
    return fn


def simplified_tree(slug: str):
    """Pre-paint-order simplified tree for a fixture, or skip if C1's replay helper is absent."""
    try:
        from tests.fixtures.replay import replay_serialized
    except ImportError:
        pytest.skip("replay helper not available")
    from browser_use.dom.serializer.serializer import DOMTreeSerializer

    try:
        _state, root, _timing = replay_serialized(slug)
    except NotImplementedError:
        pytest.skip("replay helper not implemented yet")
    serializer = DOMTreeSerializer(root, None, paint_order_filtering=False)
    tree = serializer._create_simplified_tree(root)
    if tree is None:
        pytest.skip(f"{slug}: empty simplified tree")
    return tree, root


def enhanced_nodes(root) -> list:
    out = []
    stack = [root]
    while stack:
        n = stack.pop()
        out.append(n)
        stack.extend(n.children_and_shadow_roots)
    return out


def _to_plain(v: Any) -> Any:
    if dataclasses.is_dataclass(v) and not isinstance(v, type):
        return {f.name: _to_plain(getattr(v, f.name)) for f in dataclasses.fields(v)}
    if isinstance(v, dict):
        return {k: _to_plain(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_to_plain(x) for x in v]
    if isinstance(v, (set, frozenset)):
        return sorted(v)
    return v


def diff_report(expected: Any, actual: Any, limit: int = 10) -> list[str]:
    """Field-level differences between two plain values, at most ``limit`` lines."""
    diffs: list[str] = []

    def walk(path: str, a: Any, b: Any) -> None:
        if len(diffs) >= limit:
            return
        a, b = _to_plain(a), _to_plain(b)
        if isinstance(a, dict) and isinstance(b, dict):
            for k in sorted(set(a) | set(b), key=str):
                if k not in a:
                    diffs.append(f"{path}.{k}: missing in pure, native={b[k]!r}")
                elif k not in b:
                    diffs.append(f"{path}.{k}: missing in native, pure={a[k]!r}")
                else:
                    walk(f"{path}.{k}", a[k], b[k])
                if len(diffs) >= limit:
                    return
        elif isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                diffs.append(f"{path}: length pure={len(a)} native={len(b)}")
            for i, (x, y) in enumerate(zip(a, b)):
                walk(f"{path}[{i}]", x, y)
                if len(diffs) >= limit:
                    return
        elif a != b:
            if isinstance(a, float) and isinstance(b, float) and abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b)):
                return
            diffs.append(f"{path}: pure={a!r} native={b!r}")

    walk("$", expected, actual)
    return diffs


def assert_equal(name: str, slug: str, pure_out: Any, native_out: Any) -> None:
    diffs = diff_report(pure_out, native_out)
    assert not diffs, f"{name} on {slug}: {len(diffs)}+ differences\n" + "\n".join(diffs)
