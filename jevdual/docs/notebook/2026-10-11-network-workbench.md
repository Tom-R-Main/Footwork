# Browser workbench on the persistent body

## SIM10-P1 · prediction · 2026-10-11 17:15
Hypothesis: a durable pending-stage record around the existing single-send BodyClient lets the browser operator retain queue progress across network loss and restart without inventing completion or replaying effects.
Test: build a separate network operator and retained diagnostic link; check real-socket uncertainty/restart cases, then freeze source and drive two actual Codex jobs through the browser with a lost dispatch reply, disconnect and explicit receipt recovery.
Predicts: the UI preserves identity and cached history, unknown commands block new effects, reconnect is transport-only, read-only receipt lookup applies the exact retained stage once, and explicit resume plans from a fresh TCP image before completing native/SQLite/contact verification.
Against: extra sends or native motion during recovery, silent queue resume, completion without lower proof, private pose used for planning, or independent scoring failure.
Refs: docs/experiments/SIM10-network-workbench.md; tools/physical-workcell/NETWORK_WORKBENCH_CONTRACT.md; results/network-workbench-20261011/

## SIM10-U1 · update · 2026-10-11 17:21
Observed: the first diagnostic-link run passed eight checks; the duplicate-receipt check selected an observation command by lexical journal order instead of the exact dispatch command. Its mismatched result was a test-selector failure, with the original log retained. Read-only review also found the draft scorer treated missing dispatch evidence as a withheld decision without explicit cancellation; it now requires a cancelled model outcome and no associated dispatch.
Inferred: the link's first run does not establish the complete browser workflow. Exact command identity is required in both conformance and independent scoring.
Next: bind the conformance selector to its proposal, finish runtime integration, rerun affected checks and freeze all measured source before browser/model qualification.
Refs: tools/physical-workcell/output/sim10-link-tests-v1/unittest.log; tools/physical-workcell/test_workbench_link.py; tools/physical-workcell/score_network_workbench.py

## SIM10-HEALTH · prediction · 2026-10-11 17:24
Hypothesis: cached connection state alone leaves an idle upstream outage invisible; a bounded read-only health poll can detect it without delaying browser state reads, changing completed history or sending commands.
Test: stop the real body endpoint while the host is idle, check that the UI-facing connection becomes unavailable and state reads stay responsive, then restore the same endpoint and prove reconnect remains paused with unchanged command count.
Predicts: the original cached-state path misses the outage; after repair the health check changes only connection/admission state, preserves body identity and historical results, and cannot dispatch during recovery.
Against: the original path already detects an idle outage, the poll blocks browser reads for a body timeout, sends commands, clears uncertainty, or resumes the queue automatically.
Refs: tools/physical-workcell/network_operator_runtime.py; tools/physical-workcell/test_network_operator.py

## SIM10-RESUME · prediction · 2026-10-11 17:25
Hypothesis: Resume's readback gap can overwrite a newer Pause because it clears cancellation after HTTP without rechecking the control epoch. Binding its commit to the unchanged control epoch will preserve the newer control.
Test: delay the real HTTP status response while Resume waits, issue Pause, then release the response; retain the first failing result and rerun after the epoch check.
Predicts: the original Resume returns to running despite the newer Pause; the repaired path stays paused with no command POST and does not clear uncertainty or disconnect state.
Against: the original path already preserves Pause, the repaired path still resumes or sends effects, or the test does not exercise the unlocked readback gap.
Refs: tools/physical-workcell/network_operator_runtime.py; tools/physical-workcell/test_network_operator.py
