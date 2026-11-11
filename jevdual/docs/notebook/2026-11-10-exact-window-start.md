# Explicit native CGWindow start binding

## EWS1 · prediction · 2026-11-10 19:48
Hypothesis: explicit positive CGWindow binding with a required process ID can bind an observed untitled native modal without title guessing or parent/child routing, while preserving all later exact target and policy checks.
Test: public CLI simulated-Mac start --pid77 --window-id60066 where the SDK lists an untitled panel beside a larger titled parent; stale/duplicate IDs and wrong process refuse without fallback. Invalid/mixed options refuse before driver creation or session reset. Check discovery and existing title selection.
Predicts: the exact observed process/window is the only binding, untitled windows remain eligible, absent/ambiguous identity fails, and ordinary title-based starts remain unchanged.
Against: the largest parent replaces the requested modal, an untitled modal cannot bind, a stale/wrong-process ID falls back, or invalid options bind/reset history.
Refs: output/suno-20261110/go-to-bindability.json; output/suno-20261110/go-to-controls.json

## EWS2 · update · 2026-11-10 19:52
Resolves: EWS1 = held
Observed: five public CLI selector cases failed before the option existed; fourteen public boundary cases now pass, including untitled binding, stale/wrong-PID/duplicate/observed-identity drift and invalid options preserving history without driver creation. 633 affected source/contract tests and Ruff pass. Exact selection never falls back to a larger/title-matched parent, and --url is rejected because it otherwise opens a new window.
Next: freeze source immediately for the parent live binding, then run the full default offline regression concurrently and finish reports.
Refs: results/exact-window-start-20261110/baseline.txt; results/exact-window-start-20261110/scenarios.txt; results/exact-window-start-20261110/focused.txt

## EWS3 · prediction · 2026-11-10 19:52
Hypothesis: the optional exact-CGWindow selector leaves all existing default title/process selection and other public commands unchanged.
Test: complete default offline pytest suite on the frozen source using the existing focus1 overlay, with no live/browser opt-ins.
Predicts: full default suite passes with normal opt-in skips and no native UI execution.
Against: a previously passing default/title-based or unrelated route fails due to the selector addition.
Refs: results/exact-window-start-20261110/focused.txt
