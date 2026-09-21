"""pytest plugin: run browser-use's own CI tests against this package with the jevdual patches active.

Usage (from scripts/upstream_tests.sh):
    uv run pytest -p jevdual.upstream_pytest -c /dev/null --rootdir=../browser-use ... ../browser-use/tests/ci/test_x.py

The selected upstream modules pin behaviours our agent inherits (multi-action guards, loop detection,
sensitive-data redaction, paint-order serialisation). Running them with the patches installed is the
contract check that the pinned commit's tests still pass on the patched pipeline.
"""

from __future__ import annotations

from jevdual import patch


def pytest_configure(config) -> None:  # type: ignore[no-untyped-def]
    active = patch.install()
    config._jevdual_patches = active  # type: ignore[attr-defined]


def pytest_report_header(config) -> list[str]:  # type: ignore[no-untyped-def]
    return [f"jevdual patches active: {getattr(config, '_jevdual_patches', {})}"]
