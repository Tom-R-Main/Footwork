# SIM9: Persistent body over a network

Hypothesis: a durable TCP adapter can separate visual planning from the persistent simulated body while preserving local effect authority under transport failures.

Predictions if true: exact duplicate commands retain one result and one effect; lost replies require read-only reconciliation; expired leases fence late commands; restart retains body identity and state without replay; insufficient lower-level evidence remains unknown and blocks new actions.

Predictions if false: network ambiguity permits duplicate motion, stale observations reach effects, restart erases uncertainty or changes body identity, or recovery requires direct native-state manipulation.

Design: one loopback HTTP body service, separate durable client and fault proxy on this Mac. Keep existing Bench and AgentBench guards unchanged. Pin adapter/body/source identities; persist command intent before dispatch; use server-monotonic leases revoked on every boot. Images cross TCP and are hash checked before model input. This qualifies a same-host network boundary, not authentication, WAN operation or hardware.

Primary metric: all 12 required mechanical cases pass: successive cycles; bounded delay; drop before acceptance; drop after effect; exact concurrent duplicate; conflicting duplicate; stale observation; delay past lease expiry; identity/source/exclusive lease fencing; service restart after terminal result; restart after lower receipt before transport receipt; unresolved accepted intent plus client restart remains blocked.

Secondary qualification: two successive actual Codex image-guided jobs on one network body, with at least one lost dispatch reply reconciled without resending. Independently inspect retained native states, measurement SQLite and contact reset receipts after stopping run-owned processes. Conformance planners do not count as AI evidence.

Guardrails: no direct move endpoint, no teleport, no native pose supplied to the model, no automatic uncertain-command retry, no source edits during frozen qualification. Admission leases do not promise interruption of an already accepted bounded action. Preserve all failures and attempts; paid/model runs start only at committed measured source.

Decision rule: adopt the adapter as a loopback simulated prototype only if the mechanical matrix and independent model qualification pass. Report partial or inconclusive evidence explicitly; lower-receipt absence remains unknown.

References: tools/physical-workcell/agent_bench.py; tools/physical-workcell/bench.py; SIM8-bench-operator.md. Local LeRobot reference b9cb121cb7d4e3e26ec5c906d08dda68d151ba52, src/lerobot/async_inference/policy_server.py and robot_client.py, informs remote observation/planning separation. Its observation queue is not used as an effect receipt protocol.

## Result

2026-10-11: final-source mechanical matrix passed 12/12; 13 server, 11 client and 29 existing core checks passed. The first frozen actual-model attempt at e8c7e9b passed 2/2 successive jobs with 27 image decisions, 21 movements and 83 bound transport commands. Native/SQLite scoring verified placements, measurements, contact resets and one-body continuity. A lost dispatch reply was reconciled with one GET and no repeat POST; exact concurrent duplication and delayed reply also completed. Accepted intent without lower proof remains blocked after service/client restart. All owned trial processes exited; source remained unchanged. Retained failures and scope limits are documented in results/network-body-adapter-20261011/report.md. Adopt as a loopback simulated adapter.
