import pytest
from jevdual import _native

from tests.equality.conftest import assert_equal


def _native_snapshot_lookup():
    """The R2 port is exposed through an adapter (flat arrays in, dataclasses rebuilt in Python)."""
    if _native.core is None:
        pytest.skip("native not built for snapshot_lookup")
    from jevdual._adapters import snapshot_lookup as adapter

    if not adapter.available():
        pytest.skip("native not built for snapshot_lookup")
    return adapter.snapshot_lookup


def test_pure_snapshot_lookup_is_deterministic(slug, fixture):
    pure = _native.pure("snapshot_lookup")
    a = pure(fixture.snapshot, fixture.device_pixel_ratio)
    b = pure(fixture.snapshot, fixture.device_pixel_ratio)
    assert len(a) > 0
    assert_equal("snapshot_lookup(pure,pure)", slug, a, b)


def test_native_snapshot_lookup_matches_pure(slug, fixture):
    native = _native_snapshot_lookup()
    pure = _native.pure("snapshot_lookup")
    expected = pure(fixture.snapshot, fixture.device_pixel_ratio)
    actual = native(fixture.snapshot, fixture.device_pixel_ratio)
    assert set(actual) == set(expected), f"{slug}: key sets differ"
    assert_equal("snapshot_lookup", slug, expected, actual)


def test_dispatch_resolves_snapshot_lookup_to_native_when_built():
    _native_snapshot_lookup()
    assert _native.backend_report()["snapshot_lookup"] == "native"


def test_native_strips_sensitive_values():
    native = _native_snapshot_lookup()
    from tests.fixtures.loader import load_fixture

    fx = load_fixture("sensitive-fields")
    values = {n.input_value for n in native(fx.snapshot, fx.device_pixel_ratio).values() if n.input_value}
    joined = " ".join(values)
    for secret in ("hunter2", "4111", "123", "SECRET"):
        assert secret not in joined, f"secret fragment {secret!r} leaked: {values}"
