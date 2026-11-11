# PID-scoped native window inventory

## W1 · prediction · 2026-11-10 20:32
Hypothesis: a bounded read-only public SDK window inventory scoped to one explicit PID removes the handwritten discovery step for untitled exact-window session binding without introducing implicit routing.
Test: public CLI simulated-Mac windows --pid lists titled and untitled IDs, then start --pid/--window-id binds only the observed untitled panel. Wrong-PID SDK rows, duplicate/invalid/unreadable inventory and timeout refuse without leaking titles or input. Invalid PID refuses before driver creation; discovery/schema include the command.
Predicts: current CLI refuses the missing command; the repair returns genuine titles and explicit read-only/no-association proof metadata, exact request PID only, while existing start binding guards stay unchanged.
Against: current CLI already supports this inventory, discovery activates/captures/inputs or mutates sessions, unrelated titles leak, or listing silently selects/reroutes a window.
Refs: results/native-window-inventory-20261110/

## W2 · update · 2026-11-10 20:35
Resolves: W1 = held
Observed: the public baseline refused the missing windows command. The new read-only command lists genuine titled/null/empty titles for the explicit PID and the public scenario uses the listed untitled ID to start an exact session. Nineteen targeted scenarios pass, including actual deadline cancellation/cleanup, foreign-owner privacy, duplicate/unreadable inventory, invalid pre-driver PID and unchanged session files. All 407 affected session/CLI/discovery tests pass; Ruff and notebook checks pass.
Next: freeze this command for parent-owned live inventory. Existing native binding/action guards are unchanged, so no additional full-suite repeat is required for this read-only CLI package.
Refs: results/native-window-inventory-20261110/baseline.txt; results/native-window-inventory-20261110/scenarios.txt; results/native-window-inventory-20261110/focused.txt

## W3 · summary · 2026-11-10 20:35
Established: public PID-scoped window inventory includes untitled numeric IDs, validates ownership and IDs before emitting rows, bounds SDK read/census/cleanup, preserves sessions and never activates/captures/inputs or chooses a window. Desktop routing and schema expose the required PID argument; browser routing refuses.
Uncertain: inventory proves neither current key-window status nor modal/parent association, and the worker performed no live native observation. A listed window can disappear; start and action preflight retain their existing checks.
Decision: close the package with 19 targeted and 407 affected passing tests, no binding-guard changes, SDK build, installation or UI action. Parent owns live inventory and exact session binding.
Refs: results/native-window-inventory-20261110/report.md; docs/native-window-inventory.md
