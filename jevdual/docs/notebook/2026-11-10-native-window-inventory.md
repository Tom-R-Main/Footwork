# PID-scoped native window inventory

## W1 · prediction · 2026-11-10 20:32
Hypothesis: a bounded read-only public SDK window inventory scoped to one explicit PID removes the handwritten discovery step for untitled exact-window session binding without introducing implicit routing.
Test: public CLI simulated-Mac windows --pid lists titled and untitled IDs, then start --pid/--window-id binds only the observed untitled panel. Wrong-PID SDK rows, duplicate/invalid/unreadable inventory and timeout refuse without leaking titles or input. Invalid PID refuses before driver creation; discovery/schema include the command.
Predicts: current CLI refuses the missing command; the repair returns genuine titles and explicit read-only/no-association proof metadata, exact request PID only, while existing start binding guards stay unchanged.
Against: current CLI already supports this inventory, discovery activates/captures/inputs or mutates sessions, unrelated titles leak, or listing silently selects/reroutes a window.
Refs: results/native-window-inventory-20261110/
