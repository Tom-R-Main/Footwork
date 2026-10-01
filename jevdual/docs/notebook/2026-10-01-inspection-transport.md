# Browser inspection transport buffer

## IT1 · prediction · 2026-10-01 14:50
Question: can a bounded push-to-pull event buffer provide the current recorder's CDP bridge contract without silently hiding drops or mixing events from another target?
Hypothesis: a session-scoped in-memory ring with monotonic recorder cursors, explicit truncation, byte/event caps and terminal disconnect state can turn pushed CDP events into paginated `readEvents` results while preserving observable loss.
Alternatives: method filtering advances cursors past unseen events, reconnects create ambiguous identities, or eviction and oversized events can disappear without a gap signal.
Test: implement the standalone buffer with synthetic multi-session, redirect, method-filter, pagination, eviction, oversized payload, disconnect and baseline fixtures; use no real Chrome attachment.
Predicts: only selected-session events emerge, every loss after the caller's cursor sets `truncated`, filtered polling advances monotonically, pending buffered events drain after disconnect, and later reads refuse disconnected transport.
Against: a foreign-session event appears, a cursor repeats/stalls, a dropped event produces no truncation indication, or a disconnected adapter reports new empty success batches indefinitely.
Refs: tools/inspection-transport/event-ring.mjs; tools/browser-inspection/capture.mjs; devtools-protocol pdl/domains/Target.pdl
