# Mid-job restart and explicit browser recovery

## SIM11-P1 · prediction · 2026-10-12 13:56
Hypothesis: a pending browser stage and single-send command journal survive independent workbench and body restarts without resending an uncertain action; historical body receipts can settle the same stage after its boot epoch changes.
Test: freeze a fresh owned process harness, interrupt two actual image-guided browser jobs at planning and uncertain-dispatch boundaries, recover through the UI and independently score native/SQLite/contact records after cleanup.
Predicts: all four stops/restarts preserve body/application identity and client send counts, planning interruption cancels and reaps its model process, uncertain commands remain blocked until exact receipt lookup, and explicit Resume uses a fresh TCP image before completing both jobs.
Against: a replay, lost pending command, silently resumed planning, orphan model process, body reset or independent verification failure.
Refs: docs/experiments/SIM11-workbench-restarts.md; tools/physical-workcell/qualify_workbench_restarts.py; tools/physical-workcell/score_workbench_restarts.py; results/workbench-restarts-20261012/
