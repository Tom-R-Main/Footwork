"""Pure-Python baselines for the planned Rust ports (R1, R2), recorded before any port lands."""

import pytest
from jevdual import _native

from tests.fixtures.loader import load_fixture

pytestmark = pytest.mark.bench

BASELINE_SLUGS = ["wikipedia-python", "amazon-usb-c-hub"]


@pytest.mark.parametrize("slug", BASELINE_SLUGS)
def test_bench_pure_snapshot_lookup(benchmark, slug):
    fx = load_fixture(slug)
    fn = _native.pure("snapshot_lookup")
    out = benchmark(fn, fx.snapshot, fx.device_pixel_ratio)
    assert len(out) > 0


@pytest.mark.parametrize("slug", BASELINE_SLUGS)
def test_bench_pure_paint_order(benchmark, slug):
    from tests.equality.conftest import simplified_tree

    tree, _root = simplified_tree(slug)
    fn = _native.pure("paint_order")
    benchmark(fn, tree)
