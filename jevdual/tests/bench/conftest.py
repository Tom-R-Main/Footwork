"""Benchmarks are opt-in: run with JEVDUAL_BENCH=1 (or pass --benchmark-enable yourself).

Default `uv run pytest` skips everything marked ``bench`` so the suite stays fast.
"""

import os

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "bench: performance baselines, opt-in via JEVDUAL_BENCH=1")


def pytest_collection_modifyitems(config, items):
    if os.environ.get("JEVDUAL_BENCH") == "1":
        return
    skip = pytest.mark.skip(reason="benchmarks are opt-in: set JEVDUAL_BENCH=1")
    for item in items:
        if "bench" in item.keywords:
            item.add_marker(skip)
