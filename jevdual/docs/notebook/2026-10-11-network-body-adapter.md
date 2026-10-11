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
