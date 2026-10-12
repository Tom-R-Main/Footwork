# Mid-job restart and explicit browser recovery

## SIM11-P1 · prediction · 2026-10-12 13:56
Hypothesis: a pending browser stage and single-send command journal survive independent workbench and body restarts without resending an uncertain action; historical body receipts can settle the same stage after its boot epoch changes.
Test: freeze a fresh owned process harness, interrupt two actual image-guided browser jobs at planning and uncertain-dispatch boundaries, recover through the UI and independently score native/SQLite/contact records after cleanup.
Predicts: all four stops/restarts preserve body/application identity and client send counts, planning interruption cancels and reaps its model process, uncertain commands remain blocked until exact receipt lookup, and explicit Resume uses a fresh TCP image before completing both jobs.
Against: a replay, lost pending command, silently resumed planning, orphan model process, body reset or independent verification failure.
Refs: docs/experiments/SIM11-workbench-restarts.md; tools/physical-workcell/qualify_workbench_restarts.py; tools/physical-workcell/score_workbench_restarts.py; results/workbench-restarts-20261012/

## SIM11-EPOCH · prediction · 2026-10-12 13:58
Hypothesis: a changed body boot epoch can preserve running state when its outage is missed, because health and lease acquisition verify stable identity without invalidating the old decision. Binding epoch changes to Pause before command admission will cancel stale planning without disturbing historical receipt recovery.
Test: reproduce on real sockets by rebooting the same body while a model decision waits, avoiding an outage poll; release the old decision after the new epoch is read. Cover health-first and admission-read-first paths, then rerun with epoch invalidation. Separately retain uncertain historical dispatch recovery across reboot.
Predicts: the original fast-reboot path admits the old decision; the repaired path pauses with no successor command, requires explicit Resume and a fresh observation, and retains exact unknown command identity for read-only recovery.
Against: original code already pauses, repaired code sends the old decision, permanently blocks historical receipt lookup, or silently rotates authority while a command remains uncertain.
Refs: tools/physical-workcell/network_operator_runtime.py; tools/physical-workcell/test_network_operator.py; docs/experiments/SIM11-workbench-restarts.md
