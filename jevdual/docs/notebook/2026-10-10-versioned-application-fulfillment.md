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
