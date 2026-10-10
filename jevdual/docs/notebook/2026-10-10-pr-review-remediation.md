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

## PR4 · prediction · 2026-10-10 12:55
Hypothesis: completion's query-navigation heuristic confers submitted event identity on ordinary links, allowing a nonexistent submission to clear its deterministic floor. Without a trusted form/submission acknowledgement in the receipt, treating this as unsupported can remove that false authority.
Test: actual completion consumer and floor with a confirmed View report click leading to /report?quantity=27, unrelated query navigation and actual current receipt metadata; historical/fixture source assertions must not become model-invented identity. Baseline before fix; conformance and caller checks after.
Predicts: generic query navigation contributes neither usable submission evidence nor claimed submitted fields; submit tasks without qualified event evidence remain blocked. Historical frozen runs remain unchanged and their previously supported heuristic is documented as unqualified by the corrected current code.
Against: querynavigationalone clearsmissing-submission floor, label-only guesses regain authority, or a new unverified receipt field is accepted as causal proof.
Refs: python/jevdual/completion.py; python/jevdual/session.py; tests/test_completion.py; independent reviewerpr_review finding atc9ba496

## PR5 · prediction · 2026-10-10 13:03
Hypothesis: saved current-state effects have the same supersession defect because their branch still relies on wall-clock time and omits potentially delivered paste hotkeys. Session record order plus conservative same-surface possible-edit detection invalidates stale save evidence without changing the historical record. Differing presentation labels/IDs are also insufficient to prove different field incarnations.
Test: completion/floor scenarios save then edit at equal or regressed timestamps, save then uncertain paste hotkey, no-send/refused/other-source controls; field edit that changes both ID and presentation label in the same source. Baseline then bounded helper reuse.
Predicts: later possible edits limit save/current-field support by ordered records; known other-source and no-send actions preserve; changed ID+label does not keep stale same-source value usable.
Against: stale save clears saved floor, old same-source fieldvalue remains authority after remapped edit, or any query/label guess is promoted to causal event evidence.
Refs: python/jevdual/completion.py; tests/test_completion.py; same-reviewer delta feedback pr_review

## PR6 · prediction · 2026-10-10 13:07
Hypothesis: a scope/recovery identity check before awaited NativeBridge live observation can be invalidated before the exact field guard; carrying the original readonly identity validation to the final insertion boundary refuses document/process/file replacement without confusing post-input autosave with pre-input authorization.
Test: actual public capability and fixed-worker scenarios replace AXDocument while live observation awaits; remap kernel-process or disk identity while the role/frame/content stay identical. Before fix retain failing no-input assertions. Normal append and restart matrix remain controls; exact precondition/geometry tests also remain.
Predicts: final append guard checks canonical AXDocument and the worker's qualified original identity before any setter, with missing/changed/unsupported facts producing known no-send; existing after-input safe-save treatment remains informational.
Against: replacement field receives any input, a live-remapped resource is guessed, readonly status replays an attempt, or legitimate unchanged resource fails.
Refs: python/jevdual/native.py; python/jevdual/capability/backend.py; python/jevdual/capability/execution_worker.py; tests/test_session_scenarios.py; same-reviewer pr_review delta reproducer
