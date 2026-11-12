# Bounded control appearance observation

## OBU1 · prediction · 2026-11-10 16:31
Question: can a bounded read-only CLI observation wait make delayed native Chrome control appearance explicit without promoting title changes or partial trees into readiness?
Hypothesis: repeating fresh observations until an exact offered candidate label appears can expose delayed controls while retaining ordinary look semantics, partial-coverage warnings and action ambiguity checks.
Test: add public CLI simulated-Mac scenarios for delayed appearance, timeout with no input, title/page-text near matches, duplicate labels and invalid bounds before binding; first reproduce the absent CLI capability, then implement and run the affected session and CLI checks.
Predicts: the old CLI rejects the requested wait; the new command exits zero only on an exact candidate match, reports its narrow scope and count, prints the final available observation, and returns nonzero on timeout without sending input or granting action authority.
Against: title or text substring produces success, invalid bounds create a driver, duplicate controls become uniquely actionable, polling continues beyond the bounded deadline, or ordinary look changes its behavior.
Refs: docs/notebook/2026-11-10-suno-end-to-end.md; output/suno-20261110/create-look.txt; tests/test_session_scenarios.py

## OBUU1 · update · 2026-11-10 16:35
Resolves: OBU1 = held
Observed: the baseline public CLI scenarios failed because the parser rejected the wait flags. The implemented bounded native wait passes delayed exact appearance, partial observation timeout, title/text decoys, duplicate appearance without click authorization, invalid bounds before binding, cooperative slow-observation cancellation and cleanup, driver TimeoutError preservation, and browser refusal. Poll captures use distinct paths; ordinary look keeps its existing capture naming and one-observation behavior. Combined affected regressions pass293 tests, with changed-file Ruff and notebook validation passing.
Inferred: explicit control-appearance evidence removes blind repeated look commands but cannot repair or detect a lying external AX tree on its own.
Changes: add native look --until with an exact candidate label and bounded timeout; retain the final completed menu and coverage warnings; return6 on appearance timeout. No action, permission, model call or business-readiness assertion is added.
Next: parent freezes the patch and exercises the checkout CLI read-only against the live bound Suno window when desktop access permits.
Refs: prediction e9d3a8f; results/observation-until-20261110/red.txt; results/observation-until-20261110/pytest.txt; results/observation-until-20261110/report.md

## OBUS1 · summary · 2026-11-10 16:35
Established: the native public CLI can wait for exact offered control appearance without sending input, promoting title/text matches, or relaxing duplicate-target checks. Its deadline cancels cooperative observations; driver shutdown retains its existing completion contract.
Uncertain: live Suno behavior, noncooperative native RPC cancellation latency and installed-wheel behavior are not established by these simulated-Mac scenarios. Driver binding and shutdown can add time outside the observation deadline. The command cannot establish full-page coverage, unique action identity, persistence or musical quality.
Decision: hand off the bounded local source improvement for live read-only verification. Do not replace the installed runtime or claim end-to-end Suno completion from these checks.
Refs: results/observation-until-20261110/report.md; docs/unified-cli.md
