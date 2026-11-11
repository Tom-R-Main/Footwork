# Explicit native CGWindow start binding

## EWS1 · prediction · 2026-11-10 19:48
Hypothesis: explicit positive CGWindow binding with a required process ID can bind an observed untitled native modal without title guessing or parent/child routing, while preserving all later exact target and policy checks.
Test: public CLI simulated-Mac start --pid77 --window-id60066 where the SDK lists an untitled panel beside a larger titled parent; stale/duplicate IDs and wrong process refuse without fallback. Invalid/mixed options refuse before driver creation or session reset. Check discovery and existing title selection.
Predicts: the exact observed process/window is the only binding, untitled windows remain eligible, absent/ambiguous identity fails, and ordinary title-based starts remain unchanged.
Against: the largest parent replaces the requested modal, an untitled modal cannot bind, a stale/wrong-process ID falls back, or invalid options bind/reset history.
Refs: output/suno-20261110/go-to-bindability.json; output/suno-20261110/go-to-controls.json
