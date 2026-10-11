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

## SIM10-ADMISSION · prediction · 2026-10-11 17:27
Hypothesis: persisting a checked host stage is a usable admission boundary for Pause over TCP: an admitted request can settle after Pause while all later commands remain suppressed, without holding browser state reads behind network I/O.
Test: pause before durable stage admission and assert no send; pause after stage admission while delivery waits, then release delivery and assert at most that admitted command settles and no successor is sent. Keep the body guards unchanged.
Predicts: the queue remains paused, known admitted results are applied once, unknown results remain blocked, and state reads remain responsive during the network wait.
Against: a later command sends, Pause silently resumes, an uncertain request is resent, or browser state waits behind the HTTP timeout.
Refs: tools/physical-workcell/NETWORK_WORKBENCH_CONTRACT.md; docs/experiments/SIM10-network-workbench.md; tools/physical-workcell/test_network_operator.py

## SIM10-RESUME · prediction · 2026-10-11 17:25
Hypothesis: Resume's readback gap can overwrite a newer Pause because it clears cancellation after HTTP without rechecking the control epoch. Binding its commit to the unchanged control epoch will preserve the newer control.
Test: delay the real HTTP status response while Resume waits, issue Pause, then release the response; retain the first failing result and rerun after the epoch check.
Predicts: the original Resume returns to running despite the newer Pause; the repaired path stays paused with no command POST and does not clear uncertainty or disconnect state.
Against: the original path already preserves Pause, the repaired path still resumes or sends effects, or the test does not exercise the unlocked readback gap.
Refs: tools/physical-workcell/network_operator_runtime.py; tools/physical-workcell/test_network_operator.py

## SIM10-U2 · update · 2026-10-11 17:30
Observed: the original idle connection path missed a stopped real TCP body endpoint. A delayed real HTTP status read also reproduced Resume overwriting a newer Pause. Both failing logs are retained; neither fixture sent model or physical commands. Nine diagnostic-link checks and six HTTP boundary checks now pass.
Inferred: the two control/status predictions are supported at reproduction, but the repairs still require their resolving checks. Host admission is explicitly defined at the durable stage write so Pause does not promise interruption of an in-flight request.
Next: finish bounded read-only health and epoch-checked Resume, check stage recovery and control boundaries, then freeze the browser/model trial.
Refs: tools/physical-workcell/output/sim10-idle-health-before-fix.log; tools/physical-workcell/output/sim10-resume-before-fix.log; tools/physical-workcell/output/sim10-link-tests-v2/unittest.log; tools/physical-workcell/output/sim10-http-tests-v1/unittest.log

## SIM10-POLL · prediction · 2026-10-11 17:32
Hypothesis: a background health response that overlaps a newly admitted RPC can mistake the body lock wait for an outage; binding the health result to an unchanged transport epoch prevents this stale status from cancelling a healthy action.
Test: overlap a delayed real TCP health read with a completed network command, then deliver the old failed health response; compare queue/connection status and command count before and after the epoch guard.
Predicts: the original stale response can pause the healthy host; the guarded response is discarded, normal command proof remains applied once, and the next idle read establishes current health.
Against: no false pause occurs before repair, the guarded result still changes current health, or discarding it loses an actual idle outage or command receipt.
Refs: tools/physical-workcell/network_operator_runtime.py; tools/physical-workcell/test_network_operator.py

## SIM10-U3 · update · 2026-10-11 17:36
Resolves: SIM10-HEALTH = held
Observed: the final fourteen-case runtime suite passed on real sockets. Idle outage and delayed Resume reproduce their original failures and pass after bounded read-only health and epoch checks. A known native dispatch advanced generation to one before an older health response falsely paused the original host; transport-epoch binding now discards that response. Pause before host admission sends nothing; after admission the exact command settles once without a successor. Two deterministic cycles with disturbance and all four uncertain RPC stages pass. Earlier broad-suite errors were retained fixture mistakes in the local reader and duplicate host initialization, corrected without relaxing product checks.
Inferred: the host control/recovery boundaries hold on these mechanical cases. This does not establish actual-model completion through the browser.
Next: finish unchanged-core/link/HTTP regression, commit measured source, and drive the frozen actual Codex browser trial.
Refs: tools/physical-workcell/output/sim10-network-runtime-final.log; tools/physical-workcell/output/sim10-network-runtime-tests-first.log; tools/physical-workcell/output/sim10-network-runtime-tests-second.log; tools/physical-workcell/output/sim10-stale-health-before-fix.log; tools/physical-workcell/output/sim10-health-resume-after-fix.log

## SIM10-U4 · update · 2026-10-11 17:37
Resolves: SIM10-RESUME = held
Observed: The delayed actual HTTP status collision now refuses stale Resume and leaves the newer Pause intact, with zero command sends.
Next: frozen source and actual browser/model qualification.
Refs: tools/physical-workcell/output/sim10-resume-before-fix.log; output/sim10-health-resume-after-fix.log

## SIM10-U5 · update · 2026-10-11 17:37
Resolves: SIM10-POLL = held
Observed: The older failed health response no longer pauses a host after a known native dispatch; the transport epoch binds readback to the observed interval.
Next: frozen source and actual browser/model qualification.
Refs: tools/physical-workcell/output/sim10-stale-health-before-fix.log; output/sim10-network-runtime-final.log

## SIM10-U6 · update · 2026-10-11 17:37
Resolves: SIM10-ADMISSION = held
Observed: Both pause boundaries pass: no command before durable admission, and only the admitted command settles after Pause with no successor. Cached state remains responsive.
Next: frozen source and actual browser/model qualification.
Refs: tools/physical-workcell/output/sim10-network-runtime-final.log

## SIM10-U7 · update · 2026-10-11 17:37
Observed: the final eighty unchanged-core, adapter, link and HTTP checks passed; combined with the fourteen runtime checks this is 94 passing checks. Ruff, JavaScript syntax, notebook checks and CLI preflight pass. No existing body/core/local-product source changed. One regression launch used an incorrect relative interpreter path and exited before tests; the corrected launch is retained separately.
Next: commit measured source and run the first actual browser/model trial without source edits.
Refs: tools/physical-workcell/output/sim10-core-link-http-regression.log; tools/physical-workcell/output/sim10-core-link-http-regression-v2.log; tools/physical-workcell/output/sim10-network-runtime-final.log

## SIM10-U8 · update · 2026-10-11 17:44
Resolves: SIM10-P1 = held
Observed: the first frozen actual Codex browser trial passed independent scoring after both owned trial processes exited. Two successive thirteen-call jobs advanced one body from generation zero to twenty with continuous native time, one verified SQLite measurement each and contact resets. The first dispatch reply was lost; the browser blocked the queue. Disconnect, reconnect and exact receipt lookup retained four command records without another send, and recovery remained paused until explicit Resume. Duplicate and 0.8-second delay controls were consumed once. Reload preserved both completed jobs and eighty commands. Every model image, typed proposal and lower receipt was independently bound; no private pose was supplied. The same roots and ports restarted with unchanged identities and history, paused with no active job or pending model request.
Inferred: browser-visible uncertainty and explicit recovery compose with the retained body adapter for this loopback simulation. This does not qualify hardware or authenticated remote deployment.
Next: hand off the running paused product and its runbook; preserve finite budgets and admission semantics.
Refs: results/network-workbench-20261011/report.md; results/network-workbench-20261011/qualification-score.json; results/network-workbench-20261011/ui-ledger.json; results/network-workbench-20261011/fault-observations.json; results/network-workbench-20261011/handoff.json

## SIM10-S1 · summary · 2026-10-11 17:44
Established: the browser workbench now queues actual image-guided jobs through a separate persistent TCP body. Local identity, freshness, lease and effect guards remain authoritative. Disconnect, uncertain replies and exact receipt recovery are visible product states, with explicit Resume and no hidden retry.
Evidence: 94 conformance checks and the first frozen actual-model browser trial passed. Two completed jobs, native/SQLite/contact proof, receipt and image binding, reload and paused restart are retained in the result package. Development failures remain separately recorded.
Uncertain: physical actuation, cross-machine authentication and long-running budget renewal remain outside qualification. An admitted bounded action can settle after Pause or Disconnect.
Decision: adopt the qualified loopback network workbench and hand off the running paused product with completed history retained.
Refs: docs/experiments/SIM10-network-workbench.md; results/network-workbench-20261011/report.md; results/network-workbench-20261011/attempt-ledger.json; tools/physical-workcell/NETWORK_WORKBENCH.md
