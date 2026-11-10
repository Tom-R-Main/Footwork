# Bounded control appearance observation

## OBU1 · prediction · 2026-11-10 16:31
Question: can a bounded read-only CLI observation wait make delayed native Chrome control appearance explicit without promoting title changes or partial trees into readiness?
Hypothesis: repeating fresh observations until an exact offered candidate label appears can expose delayed controls while retaining ordinary look semantics, partial-coverage warnings and action ambiguity checks.
Test: add public CLI simulated-Mac scenarios for delayed appearance, timeout with no input, title/page-text near matches, duplicate labels and invalid bounds before binding; first reproduce the absent CLI capability, then implement and run the affected session and CLI checks.
Predicts: the old CLI rejects the requested wait; the new command exits zero only on an exact candidate match, reports its narrow scope and count, prints the final available observation, and returns nonzero on timeout without sending input or granting action authority.
Against: title or text substring produces success, invalid bounds create a driver, duplicate controls become uniquely actionable, polling continues beyond the bounded deadline, or ordinary look changes its behavior.
Refs: docs/notebook/2026-11-10-suno-end-to-end.md; output/suno-20261110/create-look.txt; tests/test_session_scenarios.py
