# Browser inspection transport buffer

## IT1 · prediction · 2026-10-01 14:50
Question: can a bounded push-to-pull event buffer provide the current recorder's CDP bridge contract without silently hiding drops or mixing events from another target?
Hypothesis: a session-scoped in-memory ring with monotonic recorder cursors, explicit truncation, byte/event caps and terminal disconnect state can turn pushed CDP events into paginated `readEvents` results while preserving observable loss.
Alternatives: method filtering advances cursors past unseen events, reconnects create ambiguous identities, or eviction and oversized events can disappear without a gap signal.
Test: implement the standalone buffer with synthetic multi-session, redirect, method-filter, pagination, eviction, oversized payload, disconnect and baseline fixtures; use no real Chrome attachment.
Predicts: only selected-session events emerge, every loss after the caller's cursor sets `truncated`, filtered polling advances monotonically, pending buffered events drain after disconnect, and later reads refuse disconnected transport.
Against: a foreign-session event appears, a cursor repeats/stalls, a dropped event produces no truncation indication, or a disconnected adapter reports new empty success batches indefinitely.
Refs: tools/inspection-transport/event-ring.mjs; tools/browser-inspection/capture.mjs; devtools-protocol pdl/domains/Target.pdl

## ITU1 · update · 2026-10-01 14:52
Resolves: IT1 = held
Observed: five offline tests passed. Foreign-session messages were refused, filtered pagination advanced through unselected events, eviction and oversize loss set truncation, disconnect allowed one final drain then refused more reads, and a mocked integration with the existing capture harness produced a sealed two-event failed-load packet without the synthetic query sentinel.
Inferred: the ring can supply the recorder's `readEvents` contract under mocked push delivery without hiding tested loss. This does not establish a persistent WebSocket connection, target attachment, worker coverage or cross-call capture in real Chrome.
Next: specify and test a separately scoped CDP session adapter and its process lifetime before any live use; do not attach alongside the original audit.
Refs: tools/inspection-transport/event-ring.test.mjs; tools/inspection-transport/README.md

## ITS1 · summary · 2026-10-01 14:52
Established: a bounded, session-scoped push buffer with explicit truncation and disconnect semantics integrates with the existing recorder in a synthetic run.
Uncertain: real CDP attachment, browser target replacement, worker/OOPIF discovery, origin fencing and unattended process continuity remain unverified.
Decision: retain the ring as an opt-in transport building block only; keep the original Chrome plugin as the sole live driver/recorder for the current shared-tab audit.
Refs: tools/inspection-transport/event-ring.mjs; tools/inspection-experiments/REFERENCE_FINDINGS.md
