import os

from jevdual import _native


def test_backend_report_covers_every_function():
    report = _native.backend_report()
    assert set(report) == set(_native.FUNCTIONS)
    assert set(report.values()) <= {"native", "pure"}
    if os.environ.get(_native.PURE_PY_ENV) == "1":
        assert set(report.values()) == {"pure"}


def test_native_or_pure_resolves_and_caches():
    fn = _native.native_or_pure("snapshot_lookup")
    assert callable(fn) and fn is _native.native_or_pure("snapshot_lookup")
    try:
        _native.native_or_pure("nope")
    except KeyError as exc:
        assert "nope" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("unknown name must raise KeyError")
