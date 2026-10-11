# Browser workbench on the persistent body

## SIM10-P1 · prediction · 2026-10-11 17:15
Hypothesis: a durable pending-stage record around the existing single-send BodyClient lets the browser operator retain queue progress across network loss and restart without inventing completion or replaying effects.
Test: build a separate network operator and retained diagnostic link; check real-socket uncertainty/restart cases, then freeze source and drive two actual Codex jobs through the browser with a lost dispatch reply, disconnect and explicit receipt recovery.
Predicts: the UI preserves identity and cached history, unknown commands block new effects, reconnect is transport-only, read-only receipt lookup applies the exact retained stage once, and explicit resume plans from a fresh TCP image before completing native/SQLite/contact verification.
Against: extra sends or native motion during recovery, silent queue resume, completion without lower proof, private pose used for planning, or independent scoring failure.
Refs: docs/experiments/SIM10-network-workbench.md; tools/physical-workcell/NETWORK_WORKBENCH_CONTRACT.md; results/network-workbench-20261011/
