# Persistent network body adapter

## SIM9-P1 · prediction · 2026-10-11 16:21
Hypothesis: durable transport intent, short-lived admission leases and exact lower receipts preserve one-body authority under delays, disconnects, duplicates and process restart without replaying uncertain effects.
Test: implement a separate HTTP service/client around unchanged Bench and AgentBench; drive the twelve preregistered real-socket cases, then freeze source and run two actual image-guided Codex cycles with a lost dispatch reply.
Predicts: duplicate command results match without extra generation; read-only reconciliation settles proven effects; expired or revoked leases fence late requests; missing lower proof remains unknown and blocks dispatch; model cycles retain native/SQLite/contact evidence on one body.
Against: duplicate native effects, admitted stale/expired/wrong-body commands, automatic uncertain retry, erased unknown intent, body recreation on restart, private pose in model input, or independent cycle scoring failure.
Refs: docs/experiments/SIM9-network-body-adapter.md; tools/physical-workcell/output/sim9-network-body/; results/network-body-adapter-20261011/

## SIM9-U1 · update · 2026-10-11 16:29
Observed: the first server conformance run passed five cases and failed seven because a stray simulation field made retained response envelopes fail their closed schema. The original log is retained. Review also identified that an unbound HTTP error after an effect must preserve client uncertainty, and that leases must be rechecked after potentially slow validation.
Inferred: strict envelope checks exposed a transport serialization bug before qualification. Neither the first conformance run nor the repairs establish complete network recovery.
Next: remove the stray field, retain unknown outcomes for unbound errors, recheck lease admission immediately before intent persistence, and rerun public-boundary checks before freezing the model trial.
Refs: tools/physical-workcell/output/sim9-body-server-tests-first.log; tools/physical-workcell/test_body_network.py; tools/physical-workcell/test_body_client.py

## SIM9-JOURNAL · prediction · 2026-10-11 16:31
Hypothesis: failure while committing the terminal intent pointer leaves the current implementation's cached record inconsistent with its durable unknown intent, even though admission rereads disk and remains fenced. Updating the cache only after successful persistence removes this inconsistency.
Test: inject an intent persistence failure after a real native dispatch and terminal file creation; assert unchanged cached intent pointer, unknown public state and blocked fresh admission. Preserve the first failure, repair mutation order, then restart and prove read-only lower-receipt recovery with no extra motion.
Predicts: the current cached-pointer assertion fails; after repair cache and disk both remain unknown, admission remains blocked, and restart recovers the indexed core result without replay.
Against: no cache inconsistency occurs before repair, the repair admits fresh actions or loses the effect receipt, or restart changes native generation while recovering.
Refs: tools/physical-workcell/body_network.py; tools/physical-workcell/test_body_network.py

## SIM9-U2 · update · 2026-10-11 16:35
Resolves: SIM9-JOURNAL = held
Observed: injected terminal-pointer persistence failure reproduced the cached digest inconsistency while disk-based admission remained blocked. Copying the record and persisting it before updating the cache passes the regression; thirteen server checks pass. The second complete twelve-case matrix passes with unchanged recorded source and all owned processes reaped; ten client checks and twenty-nine unchanged-core checks pass. Static serialization also shows a normal 256-entry client index exceeds the 64 KiB wire JSON decoder bound.
Inferred: transport authority fences hold on these cases, but the client journal needs its own bounded reader before the advertised 256-command capacity is consistent.
Next: retain failures, add a strictly bounded local journal decoder without changing wire limits, rerun affected checks, then freeze measured source for the actual-model trial.
Refs: tools/physical-workcell/output/sim9-terminal-pointer-before-fix.log; tools/physical-workcell/output/sim9-terminal-pointer-after-fix.log; tools/physical-workcell/output/n9-matrix-v2/unittest.log; tools/physical-workcell/output/sim9-client-tests-v3/unittest.log; tools/physical-workcell/output/sim9-core-regression.log

## SIM9-CAPACITY · prediction · 2026-10-11 16:35
Hypothesis: a separate 128 KiB strict decoder for the local client journal can retain the declared 256-command index while preserving the existing 64 KiB network-message bound and pending-command integrity.
Test: load an exact hash-bound full-capacity journal, reject duplicate keys and oversized local journals, refuse a fresh command at capacity without sending, and rerun client and network fault checks.
Predicts: the full journal reloads without effects, capacity refuses the next send, malformed journals refuse, and unchanged wire decoding still rejects oversized messages.
Against: 256 entries still cannot reload, malformed data or oversized wire messages are admitted, unresolved commands disappear, or network recovery changes.
Refs: tools/physical-workcell/body_client.py; tools/physical-workcell/test_body_client.py

## SIM9-U3 · update · 2026-10-11 16:40
Resolves: SIM9-CAPACITY = held
Observed: the full-capacity reload failed before repair at the 64 KiB reader. The separate strict 128 KiB journal reader passes full-capacity reload, refusal before send 257, duplicate/nonfinite/oversized journal rejection and unchanged oversized-wire refusal. Eleven client checks pass. The third twelve-case matrix passes on the final source, with all owned processes reaped and all recorded source hashes unchanged. Thirteen server checks and twenty-nine core checks also pass.
Inferred: the 65 conformance checks support the bounded same-host network adapter and its retained authority under these faults; they do not establish actual-model network completion.
Next: commit measured source, freeze its exact bytes, and run two actual Codex image-guided network cycles with lost-reply reconciliation, duplicate and delayed dispatches. Score native states, SQLite and exact model/transport receipts separately after process cleanup.
Refs: tools/physical-workcell/output/sim9-client-capacity-before/unittest.log; tools/physical-workcell/output/sim9-client-tests-v4/unittest.log; tools/physical-workcell/output/n9-matrix-v3/aggregate.json; tools/physical-workcell/output/sim9-core-regression.log

## SIM9-U4 · update · 2026-10-11 16:44
Resolves: SIM9-P1 = held
Observed: the first frozen actual-model attempt completed two network jobs on one body with 27 exact-image decisions, 21 movements and 83 bound commands. Separate native/SQLite scoring passed placement, measurement, contact reset and generation/time continuity. Proxy evidence binds one lost dispatch reply to one POST and one read-only GET, one concurrent duplicate to equal payloads/replies, and one delayed reply. All model/service processes exited and the proxy closed; source stayed unchanged. The final mechanical matrix and focused checks remain 65/65 passed, with earlier failures retained.
Inferred: the persistent adapter supports this simulated network camera/action/computer loop and preserves uncertainty under the recorded faults; the evidence does not qualify hardware or secure remote deployment.
Next: preserve derived scores and attempt ledgers, keep the previous browser product available, and use the adapter contract as the boundary for a future device-specific local controller.
Refs: e8c7e9b; results/network-body-adapter-20261011/qualification-score.json; results/network-body-adapter-20261011/final-checks.json; results/network-body-adapter-20261011/attempt-ledger.json

## SIM9-S · summary · 2026-10-11 16:44
Established: committed persistent body identity, server-owned admission leases, immutable command IDs and receipts, image transport, durable single-send client uncertainty, read-only recovery, diagnostic fault proxy and independently scored actual AI network cycles. Native/core guards are unchanged. All run-owned processes are stopped; the earlier local browser server remains idle.
Uncertain: authentication across machines, physical devices, emergency stopping of accepted motion, power-loss durability, general manipulation and broader model performance.
Decision: adopt the service/client API and qualification CLI inside the existing Footwork workcell package as a loopback simulated prototype. Keep raw/private evidence and failed development attempts; do not infer hardware readiness from this result.
Refs: results/network-body-adapter-20261011/report.md; tools/physical-workcell/NETWORK_BODY.md; docs/experiments/SIM9-network-body-adapter.md
