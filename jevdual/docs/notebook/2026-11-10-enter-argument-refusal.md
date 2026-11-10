# Native Return argument refusal

## EAR1 · prediction · 2026-11-10 16:49
Question: can the native CLI reject text that its Return-only enter operation currently accepts and misleadingly prints without changing enter's authority or input behavior?
Hypothesis: validating native enter arity after parsing and before secret resolution or driver binding prevents ignored text from appearing to have been typed, while retaining target-only Return and browser behavior.
Test: public CLI simulated-Mac scenarios for a nonempty tail, explicit empty argument, unresolved secret-looking tail, and target-only Return; reproduce the accepted ignored text before repair, then run affected session, CLI and authorizer checks.
Predicts: native enter with any trailing argument returns2 before binding, resolving secrets or dispatching; its error explicitly instructs type, observe/readback, then enter. Existing target-only enter still sends one Return; other routes and browser behavior remain unchanged.
Against: rejected text reaches a driver or history as delivered input, an empty tail is accepted, a secret-looking rejected argument is resolved, target-only enter no longer works, or the fix performs an implicit fill-and-submit.
Refs: docs/notebook/2026-11-10-suno-end-to-end.md; python/jevdual/session.py::parse_do; python/jevdual/native.py::NativeBridge.act

## EARU0 · update · 2026-11-10 17:00
Observed: the EAR1 heading mistakenly used an estimated earlier time; its actual clock read and commit ba8ff28 are17:00. The prediction was committed before its resolving scenarios. Commit ordering remains the timing evidence.
Next: reproduce ignored trailing native enter text through the public CLI, then repair only this argument boundary.

## EARU1 · update · 2026-11-10 17:02
Resolves: EAR1 = held
Observed: the public CLI baseline accepted nonempty and explicit empty native enter tails; secret-looking text was resolved before binding. The first fixture also hit Calculator's existing destructive-button gate, so the scenario explicitly authorized the Return operation before reproducing the argument defect. The corrected baseline has3 failures and2 preserved-behavior passes. After repair the new scenarios pass and the affected session, CLI, discovery, authorizer and native suites pass270 tests. Ruff, notebook validation and diff checks pass.
Changes: native cmd_do refuses any trailing enter argument before secret resolution and driver binding, with explicit type, reobserve/readback, then enter guidance. It performs no compound operation and preserves target-only Return and browser dispatch scope.
Next: parent can use the corrected syntax for live navigation; freeze this local source repair without global activation.
Refs: results/native-enter-arity-20261110/red.txt; results/native-enter-arity-20261110/pytest.txt; results/native-enter-arity-20261110/report.md; prediction ba8ff28

## EARS1 · summary · 2026-11-10 17:02
Established: native enter accepts only its target, rejecting even an explicit empty text argument without binding a driver, resolving secrets or claiming delivered input. Existing target-only Return retains its normal action gates and emits one Return in the simulated native scenario.
Uncertain: no live UI or installed-wheel behavior is established by these offline scenarios. BrowserBridge itself does not implement enter; this patch leaves that existing behavior unchanged. Low-level Python NativeBridge callers are outside this CLI argument validation change.
Decision: deliver the narrow native CLI repair with reproducible evidence; do not broaden other route argument rules or silently fill and submit.
Refs: results/native-enter-arity-20261110/report.md
