from jevdual import _native

from tests.equality.conftest import assert_equal, require_native


def test_pure_snapshot_lookup_is_deterministic(slug, fixture):
    pure = _native.pure("snapshot_lookup")
    a = pure(fixture.snapshot, fixture.device_pixel_ratio)
    b = pure(fixture.snapshot, fixture.device_pixel_ratio)
    assert len(a) > 0
    assert_equal("snapshot_lookup(pure,pure)", slug, a, b)


def test_native_snapshot_lookup_matches_pure(slug, fixture):
    native = require_native("snapshot_lookup")
    pure = _native.pure("snapshot_lookup")
    expected = pure(fixture.snapshot, fixture.device_pixel_ratio)
    actual = native(fixture.snapshot, fixture.device_pixel_ratio)
    assert set(actual) == set(expected), f"{slug}: key sets differ"
    assert_equal("snapshot_lookup", slug, expected, actual)
