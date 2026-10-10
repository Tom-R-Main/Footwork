# Combined PR review and remediation

## PR1 · prediction · 2026-10-10 12:52
Hypothesis: completion effects currently treat a field's prior confirmed readback as current after a later edit because only navigation invalidates it; invalidating later mutations to that same field removes stale evidence without discarding unrelated fields or historical submissions.
Test: library/public completion regression scenarios, type27 then28 on the same field, same timestamp ordered receipts, partial/unverifiable edit, unrelated field edit, historical submission retention, downstream claim support and completion floor. Baseline before fix, focused and full checks after.
Predicts: only the latest qualified unchanged field value remains usable; potentially delivered later edits invalidate the old value; no-send/refused and unrelated-field edits do not; historical event evidence remains usable.
Against:27 still supports done after28, uncertain edit leaves old current-state support, or unrelated fields/historical events are erased.
Refs: python/jevdual/completion.py; tests/test_completion.py; independent PR reviewer pr_review (baseafe6d94,targetc9ba496)

## PR2 · prediction · 2026-10-10 12:52
Hypothesis: unicode_escape decoding of already-Unicode repr receipt text corrupts literal non-ASCII values and misinterprets escape syntax; consuming a bounded valid Python string literal without execution preserves exact Unicode and intended escaped literals.
Test: actual receipt producer formats and completion consumer regressions for café, non-Latin/emoji, quote/backslash/newline, invalid/incomplete literal and downstream claim support; baseline then fix.
Predicts: supported values remain byte/codepoint-literal, malformed provenance cannot confer usable evidence; no eval/execution or broad coercion.
Against: mojibake, lost whitespace/quotes/backslashes, malformed literal promoted to authority, or existing actual receipt producers break.
Refs: python/jevdual/completion.py; python/jevdual/browser_driver.py; python/jevdual/native.py; tests/test_completion.py

## PR3 · prediction · 2026-10-10 12:52
Hypothesis: the capability adapter loses its exact validated field value/role/frame at NativeBridge dispatch, whose legacy preview normalization/live remap accepts whitespace or geometry changes. Passing an explicit strict native precondition into that append route can refuse both changes before AX input while preserving legacy preview behavior.
Test: public native capability scenarios and fixed-worker boundary: modify trailing whitespace or original field frame after validation, before actual dispatch; missing/ambiguous role/frame and unchanged literal prefix are controls. Observe failing actual insertion baseline before product changes. Then qualified real owned TextEdit/MCP checks on committed repaired code.
Predicts: changed exact prefix/role/frame refuses before either caret/input setter; unchanged capability append still inserts once; legacy preview callers retain their existing behavior.
Against: any setter after changed preconditions, guessed field retarget, duplicate input, or loss of compatibility in legacy native routes.
Refs: python/jevdual/capability/backend.py; python/jevdual/native.py; tests/test_session_scenarios.py; tests/test_native.py; scripts/capability_restart_trial.py
