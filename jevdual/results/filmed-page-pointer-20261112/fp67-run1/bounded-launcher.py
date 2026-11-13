"""Run the pinned probe unchanged, with its idle gate limited to a deadline so it cannot start late."""
import runpy
import sys
import time

sys.path.insert(0, "scripts")
import probe_browser_holder as holder  # noqa: E402

deadline, out = float(sys.argv[1]), sys.argv[2]
_gate = holder._wait_idle
holder._wait_idle = lambda: _gate(limit_s=max(deadline - time.time(), 0.0))
sys.argv = ["scripts/probe_filmed_page_pointer.py", "--out", out]
runpy.run_path("scripts/probe_filmed_page_pointer.py", run_name="__main__")
