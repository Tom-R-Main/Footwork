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

## PRU1 · update · 2026-10-10 13:14
Resolves: PR1 = held
Observed: Later possible same-source inputs now limit prior field evidence, including changed IDs/labels, keyboard/menu/unknown routes; record order replaces timestamp inference. Independent reviewer reproduced the original defects, inspected remediations and reran309 focused tests with no residual blocking findings; root checked all seven reviewed file hashes. Native baseline8fail/4fail and completion baseline42fail/7fail/12fail/18fail remain in ignored logs; corrected focused checks pass.
Next: commit reviewed source, full/browser and actual native checks on new freeze, then one PR with CI/bot remediation before merge.
Refs: output/pr-review-remediation-20261010/independent-review-hashes.json; output/pr-native-preconditions-baseline-v2-20261010.log; output/pr-native-identity-baseline-20261010.log; jevdual/output/pr-review-remediation/completion/; reviewerpr_review

## PRU2 · update · 2026-10-10 13:14
Resolves: PR2 = held
Observed: Canonical bounded repr parsing preserves literal Unicode, quotes and whitespace in actual producer tests; malformed literals do not confer authority. Independent reviewer reproduced the original defects, inspected remediations and reran309 focused tests with no residual blocking findings; root checked all seven reviewed file hashes. Native baseline8fail/4fail and completion baseline42fail/7fail/12fail/18fail remain in ignored logs; corrected focused checks pass.
Next: commit reviewed source, full/browser and actual native checks on new freeze, then one PR with CI/bot remediation before merge.
Refs: output/pr-review-remediation-20261010/independent-review-hashes.json; output/pr-native-preconditions-baseline-v2-20261010.log; output/pr-native-identity-baseline-20261010.log; jevdual/output/pr-review-remediation/completion/; reviewerpr_review

## PRU3 · update · 2026-10-10 13:14
Resolves: PR3 = held
Observed: Twelve public legacy/fixed-worker scenarios refuse whitespace, frame or writability changes after validation before AX setters. Independent reviewer reproduced the original defects, inspected remediations and reran309 focused tests with no residual blocking findings; root checked all seven reviewed file hashes. Native baseline8fail/4fail and completion baseline42fail/7fail/12fail/18fail remain in ignored logs; corrected focused checks pass.
Next: commit reviewed source, full/browser and actual native checks on new freeze, then one PR with CI/bot remediation before merge.
Refs: output/pr-review-remediation-20261010/independent-review-hashes.json; output/pr-native-preconditions-baseline-v2-20261010.log; output/pr-native-identity-baseline-20261010.log; jevdual/output/pr-review-remediation/completion/; reviewerpr_review

## PRU4 · update · 2026-10-10 13:14
Resolves: PR4 = held
Observed: Generic query navigation no longer emits submitted effects or supplied-field provenance. A separate repeat-risk guard remains conservative without historical submission authority. Independent reviewer reproduced the original defects, inspected remediations and reran309 focused tests with no residual blocking findings; root checked all seven reviewed file hashes. Native baseline8fail/4fail and completion baseline42fail/7fail/12fail/18fail remain in ignored logs; corrected focused checks pass.
Next: commit reviewed source, full/browser and actual native checks on new freeze, then one PR with CI/bot remediation before merge.
Refs: output/pr-review-remediation-20261010/independent-review-hashes.json; output/pr-native-preconditions-baseline-v2-20261010.log; output/pr-native-identity-baseline-20261010.log; jevdual/output/pr-review-remediation/completion/; reviewerpr_review

## PRU5 · update · 2026-10-10 13:14
Resolves: PR5 = held
Observed: Save evidence now expires by ordered later same-source possible inputs including cut/menu/hotkey and equal/regressed clocks; known no-send/read-only/other-source controls remain preserved. Independent reviewer reproduced the original defects, inspected remediations and reran309 focused tests with no residual blocking findings; root checked all seven reviewed file hashes. Native baseline8fail/4fail and completion baseline42fail/7fail/12fail/18fail remain in ignored logs; corrected focused checks pass.
Next: commit reviewed source, full/browser and actual native checks on new freeze, then one PR with CI/bot remediation before merge.
Refs: output/pr-review-remediation-20261010/independent-review-hashes.json; output/pr-native-preconditions-baseline-v2-20261010.log; output/pr-native-identity-baseline-20261010.log; jevdual/output/pr-review-remediation/completion/; reviewerpr_review

## PRU6 · update · 2026-10-10 13:14
Resolves: PR6 = held
Observed: AXDocument, process-start and file identity changes inside awaited live observation now refuse before AX input. Recovery identity is retained in private validated context and checked at the final native boundary; post-input safe-save metadata remains informational. Independent reviewer reproduced the original defects, inspected remediations and reran309 focused tests with no residual blocking findings; root checked all seven reviewed file hashes. Native baseline8fail/4fail and completion baseline42fail/7fail/12fail/18fail remain in ignored logs; corrected focused checks pass.
Next: commit reviewed source, full/browser and actual native checks on new freeze, then one PR with CI/bot remediation before merge.
Refs: output/pr-review-remediation-20261010/independent-review-hashes.json; output/pr-native-preconditions-baseline-v2-20261010.log; output/pr-native-identity-baseline-20261010.log; jevdual/output/pr-review-remediation/completion/; reviewerpr_review
## PR7 · prediction · 2026-10-10 13:23
Hypothesis: the restart harness exposes hook.json through exclusive creation before JSON serialization finishes, letting its independent observer parse an empty record. Atomic exclusive publication after serialization removes this race without changing product execution or allowing receipt overwrite.
Test: deterministic reader during serialization must see no published target, then complete valid JSON; repeat publication must refuse and preserve the first record. Preserve the stopped native attempt and rerun all twelve restart cases on the committed repair, then the three real freshness guards.
Predicts: current writer fails the visibility assertion; repaired writer passes and all native boundaries remain independently readable.
Against: partial JSON remains visible, an existing marker is overwritten, or native failure persists after publication repair.
Refs: output/pr-native-restart-9961eda/delivered/report.json; scripts/capability_restart_trial.py

## PR8 · prediction · 2026-10-10 13:26
Hypothesis: TextEdit acknowledges changed AXPosition before its child AXTextArea geometry updates, so the trial actor's immediate field read invalidates a legitimate delayed geometry change before product dispatch runs. A bounded independent observation wait can qualify the interference without guessing a frame or weakening the no-input assertion.
Test: delayed versus unchanged geometry helper controls, then a fresh full three-case MCP/native guard run. Preserve the first run whose actor failed before original live dispatch.
Predicts: actor reports actual changed field geometry within its fixed deadline; original product refuses before input and exact text remains unchanged across status and repeated token.
Against: no actual field geometry change, any input after a qualified changed frame, or a deadline timeout promoted to success.
Refs: output/pr-native-guards-4fb9a95/window_move/report.json; scripts/capability_dispatch_guard_trial.py

## PRU7 · update · 2026-10-10 13:29
Resolves: PR7 = held
Observed: Deterministic publication baseline failed one visibility assertion, repaired checks pass three tests. Fresh full actual MCP/native restart matrix passed twelve cases on4fb9a95; stopped earlier run retained. The observer reads fully published markers without overwriting immutable records.
Next: include sanitized evidence in the combined PR and check remote CI before authorized merge.
Refs: output/restart-publication-before.log; output/restart-publication-after.log; results/pr-review-remediation-20261010/restart-incomplete-v1.json; results/pr-review-remediation-20261010/restart-v2.json

## PRU8 · update · 2026-10-10 13:29
Resolves: PR8 = held
Observed: Delayed geometry helper baseline failed three controls; final delayed/unchanged/absent/late controls pass four tests. Fresh complete three-case native guard matrix passed on023ec2f, with actual changed geometry observed before original live dispatch, no append and unchanged independent exact readback through status and repeat. First invalid actor run retained. Owned fixture/browser exited and exact TextEdit window is absent.
Next: include sanitized evidence in the combined PR and check remote CI before authorized merge.
Refs: output/dispatch-geometry-before.log; output/dispatch-geometry-after-v2.log; results/pr-review-remediation-20261010/guards-invalid-v1.json; results/pr-review-remediation-20261010/guards-v2.json; results/pr-review-remediation-20261010/fixture-cleanup.json

## PRS · summary · 2026-10-10 13:29
Established: Nine independent review findings are remediated in content-bound source; full1408pass26skip, browser12pass, independent309pass, Node78pass, Rust19pass and final real restart12/12 and nativeguard3/3 qualification. Two harness failures preserved and repaired with predictions committed before resolving tests. No provider default changes or new paid evaluations. Local source is checked; remoteCI/merge remain pending.
Uncertain: Broad arbitrary-app capability and general installation readiness; disk persistence, power loss and exactly-once GUI effects; exhaustive validation of the large historical research corpus. These remain outside the qualified slice.
Decision: Land one combined PR after remote CI and review threads clear, using merge commit to preserve preregistration chronology and source hashes; preserve unrelated sealed authoring worktrees.
Refs: results/pr-review-remediation-20261010/report.md; results/pr-review-remediation-20261010/review.md; docs/plans/reference-restart-reconciliation-20261010.md
## PR9 · prediction · 2026-10-10 13:36
Hypothesis: browser inspection's URL opacity filter misses short UUID/hex credentials and secret-bearing route tails, while frontend inventory summary bypasses allowlists. Positive counter allowlists and broader credential-route redaction close both persisted-artifact leaks.
Test: synthetic request URLs and inventory adapters must expose current leaks before repair; persisted metadata/frontend artifact must omit them afterwards, preserve safe structure/counts and refuse unknown summary fields.
Predicts: bot reproducers fail current tests and pass corrected redaction with no raw synthetic credential in serialized artifacts.
Against: retained credential path/summary strings or loss of expected aggregate counts.
Refs: PR1 review threads PRRT_kwDOUjL4E86rGQ-v and PRRT_kwDOUjL4E86rGQ-x; tools/browser-inspection/redaction.mjs; tools/browser-inspection/frontend.mjs

## PR10 · prediction · 2026-10-10 13:36
Hypothesis: Linux CI failures come from regenerating frozen visual PNG/manifest bytes in a different renderer environment and from unconditional macOS probes in evaluation helpers/tests. Verifying the immutable authored corpus against pinned manifest and PNG hashes, while isolating OS-specific probes, preserves evidence integrity across platforms.
Test: retain first CI14failure log; simulate a renderer environment mismatch without editing frozen artifacts, plus manifest/image tamper rejection; platform-specific absent-command/import controls and focused Mac checks, then fresh full Linux CI.
Predicts: authentic frozen cases load without runtime regeneration and altered manifest/pixels remain rejected; redaction still works when macOS hardware probing is unavailable; real Mac-only checks remain available on Mac and explicitly skipped elsewhere.
Against: mutated corpus passes, supported-platform probes silently disappear, or Linux failures persist.
Refs: output/pr-ci-failure-38072093984.log; evals/d2_visual.py; scripts/redact_results.py; tests/test_capability_fixture.py; tests/test_q19.py

## PRU9 · update · 2026-10-10 13:45
Resolves: PR9 = held
Observed: Synthetic leak baseline failed fifteen tests, with three additional failures for unnamed lowercase32-character tokens before the broader rule. Corrected metadata and actual persisted JSON/JSONL omit the tested credential paths and raw inventory summaries; root and the same independent reviewer each passed97Nodechecks. Local PageAssets schema supplied the six-kind counter allowlist. Source fixes are committed95be91f; dependency-free Node checks now run in activeCI.
Next: push consolidated fixes, resolve addressed bot threads, and check fresh remoteCI before merge.
Refs: results/pr-review-remediation-20261010/ci-remediation.json; results/pr-review-remediation-20261010/ci-review.md; PR1 bot threads PRRT_kwDOUjL4E86rGQ-v and PRRT_kwDOUjL4E86rGQ-x

## PRU10-local · update · 2026-10-10 13:45
Observed: First LinuxCI failed14tests. D2 runtime-regeneration control failed before pinned authored-corpus validation; altered labels/context/PNG still refuse and focused34pass after repair. Missing-hardware-probe baseline failed2tests; corrected focused36pass1skip. Rootfull1428pass26skip and Ruffpass; same reviewer found no actionable delta findings and all twelve reviewed hashes match. Frozen research artifacts and qualified native product source unchanged.
Inferred: Different host rendering changes the generated manifest despite equal Pillow12.3.0 versions. The immutable authored manifest and exact PNG hashes provide the stable corpus authority; fresh LinuxCI remains the integration gate.
Next: do not merge until fresh LinuxCI confirms the corrected path; append its observed outcome to resolvePR10.
Refs: commits33fdf1f and14fb64f; results/pr-review-remediation-20261010/ci-remediation.json; results/pr-review-remediation-20261010/ci-review.md; output/pr-ci-failure-38072093984.log
## PR11 · prediction · 2026-10-10 13:49
Hypothesis: the deadline subprocess test starts a250ms timer before the intended after-input blocking read; slower CI can expire after admission but before AX delivery, correctly yielding unknown without an effect and defeating the test's intended boundary. Synchronizing the test timer to the independently observed blocked boundary preserves the production callback and admission fence while removing host-speed assumptions.
Test: retain secondCI's one-failure log; before-input and after-delivery child scenarios must reach their declared boundary, invoke the original deadline callback in a real watchdog thread, preserve exact effect/no-effect assertions and require process exit plus immutable uncertainty receipt. Fresh LinuxCI decides remaining qualification.
Predicts: no250ms race determines the phase; missing boundary fails via bounded child timeout; product deadline constants and execution code remain unchanged.
Against: effect assertions weakened, a fake result replaces the actual worker callback, a missing boundary succeeds, or LinuxCI remains flaky at this boundary.
Refs: output/pr-ci-failure-38073038841.log; tests/test_capability_recovery.py::test_fixed_worker_deadline_fences_admission_and_preserves_uncertainty

## PRU10 · update · 2026-10-10 13:54
Resolves: PR10 = held
Observed: SecondLinuxCI resolved all fourteen original environment/corpus failures, passing1413Pythonchecks with28skip12deselected. It passed97Nodechecks plus Rust and lint. Its sole failure was a separate timing assumption in the fixed-worker deadline test, now trackedPR11. No frozen corpus bytes were changed.
Next: qualify the corrected deadline test in fresh finalLinuxCI before merge.
Refs: GitHubActions38073038841; results/pr-review-remediation-20261010/deadline-remediation.json; output/pr-ci-failure-38073038841.log

## PRU11 · update · 2026-10-10 13:54
Resolves: PR11 = held
Observed: Controlled400ms delay defeated the old250ms timer in two cases; after boundary synchronization, root35recoverychecks and independent35checks pass. The unchanged production callback runs in a real watchdog thread only after the exact before/after observation; missing boundary exits3 rather than expected2 and cannot manufacture a receipt. Original effect, uncertainty, admission and custody assertions are retained. An earlier child-scope SyntaxError was corrected before the causal baseline and remains labeled invalid evidence.
Next: fresh finalLinuxCI is the remaining merge gate; do not change production worker deadlines or replay policy.
Refs: results/pr-review-remediation-20261010/deadline-review.md; results/pr-review-remediation-20261010/deadline-remediation.json; output/deadline-boundary-before-v2.log; output/pr-deadline-root.log

## PR-CI-HANDOFF · summary · 2026-10-10 13:54
Established: Both bot findings fixed and threads resolved; independent review cleared product, redaction, portable corpus/probes and test-boundary deltas. Local full1428pass26skip, finalNode97pass, finalRecovery35pass; actual native restart12/12 and guards3/3 remain bound to unchanged product content. SecondCI proves all fourteen original Linux failures corrected, with the remaining test-speed race repaired by controlled-boundary evidence.
Uncertain: Final remoteCI is pending. Broad app/installation readiness, power loss, persistence and exactly-once GUI effects remain unqualified; archived research was sampled rather than exhaustively validated.
Decision: Hand this final source/evidence snapshot to LinuxCI; merge only after green checks and no unresolved actionable review threads. Preserve unrelated sealed authoring worktrees and source-history chronology.
Refs: results/pr-review-remediation-20261010/ci-review.md; results/pr-review-remediation-20261010/deadline-review.md; results/pr-review-remediation-20261010/report.md; PR1
