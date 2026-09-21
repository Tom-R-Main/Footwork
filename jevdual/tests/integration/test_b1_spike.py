"""Opt-in browser integration test: replays the B1 spike.

Set JEVDUAL_BROWSER_TESTS=1 to run; it launches headless Chrome.
"""

import asyncio
import os
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("JEVDUAL_BROWSER_TESTS") != "1", reason="set JEVDUAL_BROWSER_TESTS=1 to run browser tests"
)


def test_spike_b1_probes():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    import spike_b1

    async def collect():
        base, stop = spike_b1.serve()
        try:
            out = Path(os.environ.get("JEVDUAL_SPIKE_OUT", "/tmp/jevdual_spike"))
            out.mkdir(parents=True, exist_ok=True)
            r1 = await spike_b1.run_task(base, "t1", "Open About", [("click", "About"), ("done", "ok")], out, 4)
            r4 = await spike_b1.run_task(base, "t4", "Escalate", [("escalate",)], out, 1)
            return r1, r4
        finally:
            stop()

    r1, r4 = asyncio.run(collect())
    assert r1["is_done"] and r1["s1_steps"] == 2 and r1["s2_steps"] == 0
    assert r1["s2_context_has_s1_memory"]
    assert r4["s2_steps"] == 1 and any("System 2 was invoked" in e for e in r4["errors"])
