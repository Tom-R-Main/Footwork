# Versioned browser work-order fulfillment

## SIM5 · prediction · 2026-10-10 19:17
Hypothesis: an immutable leased order snapshot plus a current-revision compare-and-swap and exact controller evidence can connect simulated fulfillment to saved browser application state without stale or duplicate completion.
Test: local Python/SQLite app and public controller adapter, actual browser read/bind/complete, native RGB contact, changed/cancelled order during motion, lost reply and restart/conflicting identity/current artifact faults; freeze source before independent trials.
Predicts: only the same open app/order revision with supported current staged evidence commits fulfillment; changed/cancelled orders stay unfulfilled, exact repeated operation creates no second effect, and current/history remain distinct across restarts.
Against: client success flags or arbitrary paths authorize completion, wrong/stale order changes, duplicate update after lost reply, physical cancellation becomes rollback, missing current evidence becomes success, or restart loses identity and redispatches.
Refs: docs/experiments/SIM5-versioned-application-fulfillment.md; results/independent-controller-20261010/report.md; tools/physical-workcell/CONTROLLER.md

## SIM5-ID · prediction · 2026-10-10 19:33
Question: can a cached browser page mutate a replacement app at the same loopback origin before checking its reply identity?
Hypothesis: reply-only app identity checks leave bind/edit/cancel vulnerable to a same-origin replacement with matching order ID and revision.
Test: wrong or absent expected application identity on a real mutation; check unchanged SQLite order and lease rows, then require the immutable app identity before dispatch and rerun.
Predicts: the current server accepts a mutation carrying no or foreign app identity; an exact expected-app header gate refuses before any effect while valid writes remain supported.
Against: current mutation authority already includes the cached immutable application ID and refuses the request before changing state.
Refs: tools/physical-workcell/order_app.py Handler.gate; tools/physical-workcell/order_app.html api; tools/physical-workcell/test_order_app.py

## SIM5-ID-U1 · update · 2026-10-10 19:34
Resolves: SIM5-ID = held
Observed: test_order_app identity regression failed in both subcases before the fix: missing identity edited the order and a valid foreign application identity cancelled it. The retained before/after rows show the effects; the parent conformance result is failed.
Inferred: reply-only identity checking is too late for mutation authority. The prediction heading has a one-minute transcription error; commit 46aa8f4 settles its ordering before this test.
Changes: require a single exact expected application identity header before mutation, and send the cached immutable app identity from the browser.
Next: rerun this regression and the affected app/adapter conformance; freeze corrected source before independent qualification.
Refs: tools/physical-workcell/output/a56bb315a/conformance.json; 46aa8f4; tools/physical-workcell/test_order_app.py

## SIM5-U1 · update · 2026-10-10 19:38
Resolves: SIM5 = failed
Observed: the first implementation permitted mutations with missing or foreign expected application identity; SIM5-ID's failed conformance preserved the affected order rows. Corrected app conformance passed after adding a pre-effect identity gate.
Inferred: the initial implementation did not satisfy the wrong-app refusal prediction. Backend conformance does not yet establish the complete browser/physical handoff.
Next: freeze the corrected runtime and run the independent browser and integration trials under SIM5-R.
Refs: tools/physical-workcell/output/a56bb315a/conformance.json; SIM5-ID-U1; tools/physical-workcell/test_order_app.py

## SIM5-R · prediction · 2026-10-10 19:38
Revises: SIM5
Hypothesis: the corrected pre-effect app identity gate, immutable revision lease, guarded public controller handoff and transactional receipt can complete a real browser/physical loop without stale or duplicate application fulfillment.
Test: freeze corrected source; root drives actual isolated-browser read/bind/fulfill with image-guided contact, and independent public-API trials cover all seven preregistered integration scenarios with separate persisted scoring and retained failures.
Predicts: the exact still-open leased app/order commits one fulfilled revision only with supported staged/current evidence; edits/cancellation interrupt further work, wrong identities refuse before mutation, and lost replies/restarts recover history without replay.
Against: any independent scenario accepts a wrong/stale mutation, creates a duplicate fulfillment, invents native stop/completion or fails the normal supported browser loop.
Refs: docs/experiments/SIM5-versioned-application-fulfillment.md; tools/physical-workcell/ORDER_APP.md; results/versioned-application-fulfillment-20261010/

## SIM5-DEV-U2 · update · 2026-10-10 19:39
Observed: the first malformed-retained-receipt conformance attempt was refused before staging because an overlapping final HTML caption/cache change altered the bound app source. Its log is retained; it does not resolve the malformed-receipt check.
Inferred: runtime source identity invalidation behaved conservatively, but this attempt is not evidence for the intended receipt predicate.
Next: hold all app source stable, rerun the new check in fresh owned fixtures and the affected final-source suites, then freeze before independent browser/integration trials.
Refs: tools/physical-workcell/output/h5-receipt-before-type-fix/unittest.log; tools/physical-workcell/test_app_handoff.py

## SIM5-DEV-U3 · update · 2026-10-10 19:40
Observed: on a fresh stable-source fixture, controlled corruption of a retained application receipt/current-order row exposed three false-positive reconciliation subcases: boolean leased revision, cancelled current terminal state, and current revision preceding the fulfillment receipt. The actual HTTP responses were retained and the native history was not changed.
Changes: the adapter now requires an integer leased revision, exact fulfilled receipt identity/version, a fulfilled current order at or after its recorded revision, and the same canonical work-order digest.
Inferred: assigned IDs alone are insufficient for typed historical application-effect claims. This is a conformance fault on owned persisted data, not a hardware/security qualification.
Next: finish final-source adapter/backend suites, freeze all measured source, then run independent SIM5-R trials.
Refs: tools/physical-workcell/output/h5-receipt-before-type-fix-v2/unittest.log; tools/physical-workcell/test_app_handoff.py

## SIM5-R-U1 · update · 2026-10-10 19:46
Resolves: SIM5-R = held
Observed: frozen bd896e1 completed the isolated-browser order binding, four image-guided native-contact moves, staged artifact verification and browser fulfillment. Separate HTTP/SQLite scoring found exactly one receipt at fulfilled revision 2; browser reload preserved it. Independent public-API trials passed all seven first attempts with unchanged source, including native-step-confirmed edit/cancel stops, lost-reply reconciliation, identity/conflict refusals, restart history and current artifact tampering.
Inferred: the corrected bounded local handoff connects physical evidence to saved application state while preserving explicit stale/current/history boundaries. It does not establish general visual-policy performance or hardware transfer.
Next: close this package with retained failures, evidence and owned-process cleanup; consider persistent body identity across successive work orders separately.
Refs: bd896e1; results/versioned-application-fulfillment-20261010/report.md; results/versioned-application-fulfillment-20261010/summary.json; results/versioned-application-fulfillment-20261010/browser-result.json

## SIM5-S · summary · 2026-10-10 19:46
Established: Python/SQLite application revision leases and a public controller adapter completed a real browser/native-image/software loop, with 95 affected checks and seven independent diagnostic scenarios supporting the corrected implementation. Wrong-app mutation and malformed reconciliation development failures are preserved; all trial-owned processes/sockets and the temporary browser tab were cleaned up.
Uncertain: physical/application proof is not atomic; the host must invoke guard to interrupt stale jobs; each lease currently owns a separate simulated episode. General robotics, a physical shared-body scheduler, camera/hardware calibration, operator demand and production capability governance are unqualified.
Decision: keep the bounded local app/handoff as an experimental Footwork tool, with deterministic authority and host planning. A subsequent package should separate persistent body/resource ownership from changing task identity.
Refs: results/versioned-application-fulfillment-20261010/; docs/experiments/SIM5-versioned-application-fulfillment.md; tools/physical-workcell/ORDER_APP.md
