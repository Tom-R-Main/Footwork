# Control state and advisory blockers

## CTL1 · prediction · 2026-10-28 20:36
Hypothesis: state normalization, session persistence and duplicate indexing lose observable control transitions or manufacture progress when state becomes available.
Test: deterministic adapter and saved-session round trips, duplicate and unknown-state effect comparisons, real command scenarios, and a disposable browser fixture where available.
Predicts: mixed state and expanded baselines fail before repair; repairs preserve known transitions without confirming unknown or ambiguous comparisons.
Against: existing paths preserve these states and comparisons already distinguish missing evidence.

## CTL2 · prediction · 2026-10-28 20:36
Hypothesis: an opt-in bounded diagnostic at existing blocked/stalled handbacks can explain page conditions without changing the selected operation or authorizing another dispatch.
Test: fake-provider boundary tests for eight categories, invalid/empty/timeout responses, observation binding, and disabled-path regression checks.
Predicts: failures return unavailable and retain the original stop; diagnostics never dispatch actions.
Against: a diagnostic changes routing, retries a mutation, or treats unavailable evidence as a negative finding.
