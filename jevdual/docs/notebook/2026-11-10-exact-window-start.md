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

## EWS4 · update · 2026-11-10 19:57
Resolves: EWS3 = held
Observed: full default offline regression on frozena64b6f2 passed3256 tests with62 opt-in skips in213.96 seconds, exit0. Before/after hashes of the four production modules match; no live/browser opt-ins were active. Focused validation remains633 passing checks and14 public selector scenarios.
Next: hand off the final evidence record; retain source unchanged and leave actual nested-panel input/file saving with the parent.
Refs: results/exact-window-start-20261110/full-default.json; results/exact-window-start-20261110/report.md

## EWS5 · summary · 2026-11-10 19:57
Established: explicit same-process CGWindow selection includes untitled windows, refuses absent/duplicate identities without fallback, rejects invalid/mixed options before binding/reset and preserves later observation/policy checks. All633 focused and3256 full offline tests pass with62 opt-in skips.
Uncertain: the worker performed no native input or Save. A new modal still needs its own observed identity; project folder and final output remain parent-owned live checks.
Decision: close the selector package with frozena64b6f2 and its separate full-suite JSON/report, no SDK/native-byte changes or installation.
Refs: results/exact-window-start-20261110/report.md; results/exact-window-start-20261110/full-default.json
