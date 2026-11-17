# Native row observation trace

## RT1 · prediction · 2026-11-17 15:30
Hypothesis: census002 is undecidable because the existing SDK silently drops row-capture/discovery failures and the public session retains only projected candidates. A bounded opt-in trace carried through the existing typed observation can expose the first failing stage without changing qualification, input, traversal or read budgets.
Test: commit failing offline tests before implementation for typed request/output propagation, capture/read/budget errors, per-key refusal, successful proof attachment, projection loss, missing retention and explicit truncation. Compare trace-on/off qualification results and AX read counts with identical fixtures. Preserve callback module, exact predicates and budget constants; build only the active SDK target. Independently review frozen diff, deliver exact hashes with rollback, then one authorized public start observation under serialized Desktop custody; never a second look or any action.
Predicts: diagnostic fields survive the actual ABI and private retention; generated proofs and refusal decisions agree on/off. One real trace identifies either an observed rejection or the precise missing boundary, retaining actual graph only when already collected and exact demo URL scoped. Collection emits no extra AX reads or input; serialization occurs afterward with bounded bytes and explicit truncation.
Against: tracing changes decision logic or read budgets, broadens scope, leaks pointers or unscoped content, silently truncates, fabricates graph relationships, or a failed trace is claimed as qualification. Any authority/input-semantic expansion stops the tranche. Time overhead remains measurable rather than an atomic timing guarantee.
Refs: /Volumes/External SSD/Footwork-native-row-evidence-20261117/census002-mechanism/DIAGNOSIS.md; /Volumes/External SSD/demoApps/demo/WORK_RECORD.md

## RT2 · update · 2026-11-17 15:49
Observed: typed contract red rejects row_trace_url; contract green69 and initial20 Python trace cases pass. Native production build and trace wheel build pass offline. Generated SDK module matches existing callback-overlay source; only contract bindings change. Source comparison preserves AX primitive call sites, reference admission and the press implementation. Public-start fixture performs one observation with zero input.
Inferred: diagnostics can expose the missing boundary without adding AX calls or changing predicates; fixed wall-time limits still make instrumentation overhead a real uncertainty.
Next: frozen-source affected checks and independent Sol review, rollback delivery, then one authorized live observation. RT1 stays open until actual trace and custody closure.
Refs: /Volumes/External SSD/Footwork-native-row-trace-evidence-20261117/{typed-red.txt,contract-green.txt,trace-cli-tests-rerun.txt,native-build.txt,wheel-build-resumed.txt,SOURCE-INVARIANTS.json}; failed root-directory test invocations and malformed ABI fixture retained separately, not qualification evidence.

## RT3 · prediction · 2026-11-17 16:01
Hypothesis: the SDK prefix check confuses userinfo with authority, while private retention does not bind an embedded trace to its enclosing snapshot. A shared strict numeric-loopback URL grammar at typed/native ingress and exact envelope matching will reject these review cases without changing valid local trace qualification or input.
Test: preserve red controls for loopback-looking remote authority, credentials, query/fragment, invalid port, and wrong/missing snapshot/PID/window; keep valid URL and matching envelope controls. Run actual Rust validation and private retention before and after, then focused ABI/integration checks and one independent correction review.
Predicts: invalid URL is refused before native preflight/collection; inconsistent envelope is invalid and missing snapshot is explicitly unproven. Valid local requests and matching traces retain unchanged discovery/input outcomes.
Against: a remote authority still enters diagnostics, genuine matching records lose classification, or the fix changes census predicates/read budgets/input.
Refs: /Volumes/External SSD/Footwork-native-row-trace-evidence-20261117/sol-review-b6c6163/REVIEW.md F1/F2.

## RT4 · update · 2026-11-17 16:12
Observed: actual typed Rust URL regression failed on the remote-authority example (1failed/1positive passed); retention regression failed6cases and kept1matching positive. Correction passes71contract tests and2macOS tests, including native ingress rejection before target validation/collection. Initial correction trace selection35passes. Source archive941c3b35 and trace2 wheel build pass offline; record ABI and callback module bytes are unchanged. Original reviewed SDK source restored to its checkpoint; correction source kept separately.
Next: final focused packaged checks and independent correction review; no installed/live change. RT3 remains open pending that review and checks; RT1 remains open pending the single real observation.
Refs: /Volumes/External SSD/Footwork-native-row-trace-evidence-20261117/{url-red.txt,envelope-red.txt,url-green.txt,ingress-green.txt,correction-trace-tests.txt,wheel-trace2-build.txt,sdk-correction-source}; sol-review-b6c6163/REVIEW.md.

## RT5 · prediction · 2026-11-17 11:18
Hypothesis: PR37 CI failed because the provenance test retains the row4 count of 15 files after diagnostics deliberately adds row_trace.rs and row_trace_probe.rs; hash-chain checks remain valid.
Test: reproduce the specific failing test on db09d2f, compare old/current manifest membership, update only its exact expected count and run the complete build/provenance test file plus notebook check. Keep the independently reviewed worktree frozen by using a separate CI worktree.
Predicts: the red failure is 17 versus 15; exactly the two diagnostic files explain the difference; all build/provenance tests pass with 17 while still checking every file hash.
Against: any unexpected added file, hash mismatch, or additional test failure means the count correction is insufficient; do not weaken provenance checks.
Refs: /Volumes/External SSD/Footwork-native-row-trace-evidence-20261117/CI-b6c6163-failed.txt; tests/test_cua_driver_build.py::test_local_native_patch_has_inspectable_hash_bound_provenance.

## RT6 · update · 2026-11-17 11:18
Resolves: RT5 = held
Observed: db09d2f reproduces the exact provenance count failure. The two added manifest members are row_trace.rs and row_trace_probe.rs. Updating only the expected count preserves all per-file/hash-chain assertions; the complete build/provenance file and notebook tests pass (see retained green log for count). Production and packaged artifact bytes remain identical to frozen db09d2f; its review worktree is untouched.
Next: await independent diagnostic correction review and fresh CI; no installation or live observation yet.
Refs: /Volumes/External SSD/Footwork-native-row-trace-evidence-20261117/ci-provenance-red.txt; /Volumes/External SSD/Footwork-native-row-trace-evidence-20261117/ci-provenance-green.txt.

## RT7 · prediction · 2026-11-17 11:22
Hypothesis: the snapshot-unproven branch loses only the producer truncation marker; carrying its strict boolean value preserves explicit diagnostic limits without retaining unbound content.
Test: reproduce the exact native sdk_trace_oversize fallback without inner snapshot ID, plus false/missing/nonboolean marker controls. Assert snapshot_unproven and no graph/proof/candidate data in every case, and strict true propagation only. Run trace, ABI, source-chain and packaging controls after the one-line correction.
Predicts: only the true-marker regression fails before correction; all cases pass afterward with unchanged binding refusals and input decisions.
Against: any unbound content becomes retained, malformed truthy values imply truncation, or other classification changes.
Refs: /Volumes/External SSD/Footwork-native-row-trace-evidence-20261117/sol-review-db09d2f/REVIEW.md F3.

## RT8 · update · 2026-11-17 11:23
Resolves: RT7 = held
Observed: actual native fallback shape fails only the true truncation case before correction (1 failed, 4 passed). One-line strict boolean propagation passes the eight-file packaged selection (199 passed); ruff and diff checks pass. Missing snapshot still withholds all graph/proof/candidate data. The initial red command used a wrong relative test path and collected no matching case; it is retained separately and is not red evidence.
Next: independent db09d2f review closes F1/F2 with no safety/input blocker. Its F3 recommendation is applied exactly here; F4 count correction is already checked. CI and rollback-preserving delivery remain, followed by one authorized observation; no input or live qualification is claimed.
Refs: /Volumes/External SSD/Footwork-native-row-trace-evidence-20261117/sol-review-db09d2f/REVIEW.md; /Volumes/External SSD/Footwork-native-row-trace-evidence-20261117/{truncation-red-valid.txt,truncation-green.txt,ci-provenance-green.txt}.

## RT9 · prediction · 2026-11-17 11:45
Hypothesis: the unrelated Linux mapping test over-specifies the final readiness reason. Session.await_probe may retain a genuine wm_not_servicing reply, then start a final probe with little shared deadline remaining and report probe_timeout. This still correctly forbids editor launch. CI observed only the final timeout; intermediate records were not uploaded, so their contents are not claimed.
Test: retain CI failure; inspect the unchanged probe loop and update only the test to require an actual retained false/wm_not_servicing reply, allow the two valid final reasons, and preserve no-editor/no-started/no-survivor assertions. Run static/notebook checks locally; Linux process-ownership execution remains CI-only on this Mac. No timeout or production behavior changes.
Predicts: Linux CI passes while still failing if every attempt times out, a ready reply is substituted, an editor starts, or children survive. The prior assertion is already disproved by the retained CI run; no aggregate Mac skip is counted as Linux verification.
Against: no retained explicit refusal exists in the failing scenario or corrected Linux CI fails again; then this hypothesis is insufficient and further probe diagnosis is required, not another permissive assertion.
Refs: /Volumes/External SSD/Footwork-native-row-trace-evidence-20261117/CI-186eb4c-failed.txt; python/jevdual/linux_session.py Session.await_probe and Session.run; tests/test_linux_session.py::test_editor_waits_for_window_manager_mapping_acknowledgement.

## RT10 · update · 2026-11-17 11:46
Observed: unchanged Linux probe source retains each attempt then reports the final reason at shared-deadline expiry. Corrected assertion requires a recorded false/wm_not_servicing reply and keeps no-editor/no-started/no-survivor checks. Ruff/diff checks pass; local notebook tests pass and the Linux case is explicitly skipped on macOS. No claim of executed Linux validation; RT9 remains open until CI.
Next: push test-only correction for actual Linux CI; no runtime/source archive/wheel change, deadline tuning or live input.
Refs: /Volumes/External SSD/Footwork-native-row-trace-evidence-20261117/linux-readiness-check.txt; CI-186eb4c-failed.txt in the same evidence directory.
