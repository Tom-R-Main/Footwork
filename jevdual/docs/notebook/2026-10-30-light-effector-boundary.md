# Light effector boundary

## LEB1 · prediction · 2026-10-30 21:03
Hypothesis: a lazy CUA compatibility adapter can own SDK construction, input constructors and browser authorization without changing current driver requests, receipts or awaited cleanup.
Test: run the existing native/session/browser/coexistence/SDK seam scenarios before and after; add a subprocess import/discovery audit with optional packages blocked, missing-package versus transitive-failure controls and an AST SDK-import boundary check. Build the pure capability wheel and exercise installed discovery outside the checkout. Use the existing fixture outcomes and strict dispatch/refusal assertions as the oracle.
Predicts: discovery remains available without optional imports; SDK request/result objects and authorization decisions remain unchanged; existing scenario effects, no-send refusals and unknown outcomes remain unchanged; SDK imports appear only in effectors/cua.py.
Against: any scope/dispatch/refusal/evidence outcome changes, a shutdown await is removed, missing native/transitive imports are mislabeled as absent CUA, or discovery loads an optional backend.
Refs: docs/plans/light-profile-20261030.md; tests/contract/test_cua_driver_seams.py; tests/test_session_scenarios.py; tests/test_browser_launch.py; merged reliability base 5acf3b2. This package does not claim a CDP light runtime or repeat PR12's VM reliability qualification.

## LEBU1 · update · 2026-10-30 21:12
Resolves: LEB1 = held
Observed: compatibility factories return unchanged SDK requests/results and driver objects; exact cleanup2 seam checks and adapter controls pass64. The existing suite passes2487 with100 skips and13 browser tests deselected from the documented jevdual directory. The201-file pure wheel matches source dda70d0, and installed discovery plus all four missing-CUA startup cases pass outside the checkout. Review found a new late-absence regression; four public cases fail before import-only preflight and pass after it, preserving prior session state and preventing Chrome launch.
Inferred: the compatibility boundary preserves the exercised existing contracts without claiming a portable normalized data model or a new browser authority.
Next: final-head hosted CI and landing. L1b/CDP/authority/profiles remain later packages; no metadata split yet. The old-SDK baseline, two probe errors and wrong-working-directory suite invocation are retained and classified in the report. The prediction ID was corrected mechanically from LP1 to LEB1 after notebook validation found a collision; its hypothesis and test were unchanged.
Refs: results/light-effector-boundary-20261030/report.md; results/light-effector-boundary-20261030/missing-sdk-before.txt; source dda70d0; wheel f1a67ce77bff88c0ed3e94940b56d57f5dff2f5a407493cd184bb440856726db

## LEBS · summary · 2026-10-30 21:12
Established: CUA imports and construction are behind a lazy adapter; compatibility entrypoints, original SDK wire objects, strict browser authorization and cleanup awaiting remain. Missing optional implementation refuses before session reset or browser launch. Existing regression and installed-artifact gates pass on the identified source.
Uncertain: live Linux stress qualification was not repeated for this wrapper; the new direct-CDP browser, durable recovery, light dependency closure and resource envelope are unbuilt/unmeasured. No binary-consumer CI or merge result is implied by the local checks.
Decision: ship the bounded L1a implementation separately from the reviewed plan after hosted checks. Continue in dependency order; do not remove required metadata before the light runtime and evidence contract qualify.
Refs: docs/plans/light-profile-20261030.md; results/light-effector-boundary-20261030/report.md

## LEBU2 · update · 2026-10-30 21:35
Observed: final-head PR14 CI passes core/native/Rust checks and all three binary consumer jobs, then fails simulator test_running_cancel_verifies_stop_after_real_native_progress: native_steps_before_cancel is zero. The same unchanged simulator source passes PR13. The test waits for controller dispatch intent and then sleeps0.18 seconds; that intent is persisted before native simulation enters its stepping loop.
Inferred: the test cancels during a pre-step initialization window on this runner; elapsed sleep does not prove the required positive native progress. This inference is narrower than a cancellation-runtime defect.
Next: LEB2 tests the precondition directly without changing simulator cancellation behavior or weakening the positive-step assertion. Preserve the hosted failure log.
Refs: https://github.com/Tom-R-Main/Footwork/actions/runs/41154315197; tools/physical-workcell/test_controller.py:324; tools/physical-workcell/controller.py:294; tools/physical-workcell/workcell.py:416

## LEB2 · prediction · 2026-10-30 21:35
Hypothesis: an actual-process test-only barrier after the first real MuJoCo step can make the cancellation-after-progress case deterministic despite slow pre-step initialization, while leaving production motion and cancellation code unchanged.
Test: use the existing fault-script fixture to observe a real mj_step advancing simulation time, retain a marker and pause the stepping worker; issue the public cancel command, then release the worker and assert the existing verified-stop, positive-step, retained-generation/state and duplicate-cancel invariants. Test a delayed startup and a bounded no-progress/timeout negative control; rerun controller conformance and hosted CI.
Predicts: no cancellation is sent before the observed positive step; all original assertions pass under deliberate pre-step delay; no progress or a failed marker cannot satisfy the precondition or silently pass. Production files remain unchanged.
Against: a marker can precede a real step, no-progress passes, a child remains owned after teardown, or the original stop/state assertions fail after qualified progress.

## LEBU3 · update · 2026-10-30 21:42
Resolves: LEB2 = held
Observed: a test-only2-second pre-motion delay reproduces the hosted zero-step failure under the original sleep. After synchronizing on a bound marker from an actual mj_step, the real controller cancels with1 native step, verified stop/state retention and matching generation/hash; absent/invalid markers fail the precondition. All29 controller tests pass in the parent's independent run, with3 focused checks also passing. Test-only source0d4dba8 preserves production motion/cancellation and every original assertion. Two local full-group attempts exposed missing/hardcoded checkout CLI paths; the independent check now honors the existing executable override and passes against the real installed CLI.
Inferred: replacing elapsed-time inference with observed progress removes this reproduced test race without claiming any production cancellation algorithm change.
Next: retry final-head CI, retain its earlier failure and require all gates before merging PR14. Browser-only contract, headless readiness, exact-value and cross-command custody refinements are now explicit in the plan; no new browser is claimed.
Refs: results/light-effector-boundary-20261030/report.md; results/light-effector-boundary-20261030/ci-simulator-failure.txt; results/light-effector-boundary-20261030/controller-parent-final.txt; source0d4dba8
