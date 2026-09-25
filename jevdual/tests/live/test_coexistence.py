"""The coexistence promises on this machine's real apps (Q15, docs/experiments/Q15.md).

Opt-in: they take the keyboard. ``FOOTWORK_LIVE=1 uv run pytest tests/live -q`` runs one repetition of
each case; ``scripts/q15_coexistence.py`` runs the pre-registered three and writes the results. A case
that finds someone at the machine is skipped as contaminated, never passed.
"""

from __future__ import annotations

import asyncio
import os

import pytest

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(os.environ.get("FOOTWORK_LIVE") != "1", reason="takes the keyboard: FOOTWORK_LIVE=1"),
]


@pytest.mark.parametrize("case", ["C1", "C2", "C3", "C4", "C5"])
def test_case(case, tmp_path):
    from jevdual.coexist import NotIdle, run_case

    try:
        r = asyncio.run(run_case(case, tmp_path))
    except NotIdle as exc:
        pytest.skip(str(exc))
    if r.contaminated:
        pytest.skip(f"contaminated: {r.contaminated}")
    assert r.error is None, r.error
    failed = {k: r.details.get(k) for k, ok in r.checks.items() if not ok}
    assert not failed, failed
