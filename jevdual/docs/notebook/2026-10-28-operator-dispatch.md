# Operator dispatch uncertainty

## OD1 · prediction · 2026-10-28 17:38
Hypothesis: a simulated native press followed by a driver error is recorded as refused/no-send, preserving earlier current-state evidence; -25204 can trigger a second press without proof of non-delivery.
Test: real CLI scenarios using the existing simulated Mac and independent press ledger, plus native bridge tests injecting an exception after a press; run the new safety assertions before changing runtime code, then after the fix.
Predicts: the old path fails safety assertions because it records refusal after a press or issues two inputs for one command; repaired returned/caught paths preserve uncertainty and make only one input attempt.
Against: the old path already records uncertainty, limits prior readback and never retries after the injected error, or the fixture fails before reaching a press.
Refs: docs/experiments/OD-dispatch-uncertainty-20261028.md; docs/plans/five-directions-20261028/IMPLEMENTATION-PLAN.md

## OD2 · prediction · 2026-10-28 17:38
Hypothesis: cancellation after a grant-gated press leaves spent authority without a durable do record, and a separately regranted command can press again.
Test: wrap the actual simulated native click to raise cancellation after its effect, inspect existing grant/session files, then restore the driver and regrant/retry.
Predicts: one press and consumed grant exist without a do record; retry after a new grant produces a second press. Package 1 records this diagnosis without claiming durable interruption recovery.
Against: a durable blocking operation already exists, the grant is not consumed, or a second granted command is blocked.
Refs: docs/experiments/OD-dispatch-uncertainty-20261028.md

## ODU1 · update · 2026-10-28 17:46
Resolves: OD1 = held
Observed: before runtime changes, CLI/completion safety tests produced four failures and the native bridge safety tests produced four failures. The independent press ledger recorded two inputs after the injected -25204 error. After the correction, 233 CLI/completion/desktop tests and 74 native/posture tests passed. Independent review identified three additional uncertain-input paths (select-all, foreground title-bar input and append readback loss); their fixes and boundary regressions are included.
Inferred: error/no-send conflation was present in both the native bridge and outer command/receipt handling. Preserving uncertainty requires carrying dispatch metadata across preparation and post-input observation, not just changing the driver's effect word.
Next: complete the frozen full-suite run and retain evidence before committing package 1.
Refs: results/operator-dispatch-20261028/; tests/test_native.py; tests/test_session_scenarios.py; tests/test_posture.py; tests/test_completion.py

## ODU2 · update · 2026-10-28 17:46
Resolves: OD2 = held
Observed: the real-command cancellation characterization passed: one granted press consumed its grant, no do record was retained, and a newly granted retry pressed again. The characterization remains explicit in test_session_scenarios.py until durable admission replaces it.
Inferred: the cancellation/intent gap is distinct from returned-error classification and is still open after package 1. This run did not test SIGKILL or installed application recovery.
Next: package 2 must replace the characterization with safety assertions for committed intent, reservation accounting and blocking/replay before any live diversified qualification.
Refs: results/operator-dispatch-20261028/cli-before.txt; tests/test_session_scenarios.py::test_cancelled_granted_press_characterizes_missing_durable_intent

## ODS1 · summary · 2026-10-28 17:46
Established: package 1 reproduces and corrects misleading returned/caught dispatch errors and removes the unqualified -25204 retry. Full regression validation passed: 1724 tests passed, 26 skipped; repository Ruff and diff checks passed. Independent review's additional error-path findings were corrected and covered. The complete before/after evidence is retained in results/operator-dispatch-20261028/.
Uncertain: cooperative cancellation still lacks durable intent and can admit another separately granted press. No SIGKILL, installed application, provider, first-use or diversified-app qualification ran. Existing journal/MCP custody is not generalized by this package.
Decision: commit package 1 as the bounded error/retry correction. Next implement package 2's durable authority-domain admission, transactional reservations, replay and conservative recovery before live Finder/Preview/browser qualification.
Refs: results/operator-dispatch-20261028/report.md; docs/plans/five-directions-20261028/IMPLEMENTATION-PLAN.md
