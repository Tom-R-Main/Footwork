# Pre-header transport attribution and qualification

## PH1 · prediction · 2026-10-30 00:15
Hypothesis: Chrome transport replays a plain form POST after the fixture closes without response headers; Footwork dispatch itself occurs once.
Test: fresh owned loopback fixtures, direct HTTP and isolated Chrome controls; correlate native action, browser lifecycle, connection and ingress. Repeat normal, truncated and disconnect cells twice each; retain uninstrumented comparison.
Predicts: disconnect duplication can occur without Footwork while a single native activation is retained; supported response modes retain one ingress.
Against: duplication requires repeated native activation, server accounting fabricates rows, or controls cannot attribute the second request.
Refs: docs/experiments/preheader-20261030.md

## PH2 · prediction · 2026-10-30 00:18
Hypothesis: an explicit fetch POST from a single owned submission event may avoid the Chromium form-navigation transaction restart under the identical zero-header fault.
Test: two fresh owned Chrome fetch controls with unchanged TicketFixture disconnect mode, same request fields/body, browser submission-event count and NetLog/independent handler records.
Predicts: each fetch control produces one ingress and retains the failed application response.
Against: fetch also restarts the transaction, duplicates ingress or requires weakening the fault/ledger.
Refs: output/preheader-20261030/controls-initial

## PH3 · prediction · 2026-10-30 00:20
Hypothesis: a fixture-owned fetch submit handler preserves one real native form activation and prevents the navigation retry observed after zero-header loss, without manufacturing v2 response evidence.
Test: add opt-in fetch submission route with unchanged default navigation route, encoded fields and original disconnect fault; regression for generated handler/route validation, then two fresh native disconnect trials. Test v2 still refuses disconnect mode even with one ingress.
Predicts: fetch native trials each have one ingress, preserved unknown custody and no extra ingress on token replay; navigation challenge still duplicates.
Against: native fetch duplicates, the fault is weakened, or evidence falsely finalizes.
Refs: output/preheader-20261030/controls-fetch/results.json

## PH4 · prediction · 2026-10-30 00:24
Hypothesis: a new preadmitted sealed-fixture policy can qualify one committed ingress after pre-header loss using irreversible producer closure, without asserting browser delivery/termination or weakening v2.
Test: stop accepts, positively drain request handlers, prohibit all later ledger writes/reopen via durable terminal state, atomically seal the final snapshot; adversarial active-handler, late request, restart, tamper, duplicate and legacy-enrollment tests. New policy opt-in must bind before dispatch and old unknowns remain ineligible.
Predicts: only a new policy-bound operation with one exact ingress/row and an authentic closed/drained immutable source finalizes; any incomplete closure or contradictory evidence remains unknown.
Against: process exit or a timer alone grants authority, handlers can write after sealing, source reopens, duplicates qualify, or historical operations enroll.
Refs: docs/experiments/preheader-20261030.md

## PHU1 · update · 2026-10-30 00:37
Resolves: PH1 = held
Observed: 26 controls traced four navigation disconnect duplicates to Chromium POST transaction restart (-324), without Footwork. Two native navigation trials also produced two ingresses.
Next: follow the final PR head through review, hosted checks and authorized merge; preserve finite source-epoch support limits.
Refs: results/preheader-20261030/report.md

## PHU2 · update · 2026-10-30 00:37
Resolves: PH2 = held
Observed: Both fresh diagnostic fetch controls produced one ingress without that restart.
Next: follow the final PR head through review, hosted checks and authorized merge; preserve finite source-epoch support limits.
Refs: results/preheader-20261030/report.md

## PHU3 · update · 2026-10-30 00:37
Resolves: PH3 = held
Observed: 984cd86 installed native fetch trials each produced one ingress; v2 custody correctly stayed unknown and token replay added none. Installed fetch nominal/interrupted-truncated chains passed.
Next: follow the final PR head through review, hosted checks and authorized merge; preserve finite source-epoch support limits.
Refs: results/preheader-20261030/report.md

## PHU4 · update · 2026-10-30 00:37
Resolves: PH4 = held
Observed: 6c0f8a0 installed native controller-kill trial and nominal chain finalized from v3 sealed source. Interrupted pre-header chain observed three SIGKILLs and finalized; its legacy header oracle failed, then read-only independent sealed readback completed handoff and replay with no input repeated. Final full suite: 2269 passed, 26 skipped; independent review: 123 passed; Ruff/offline package passed.
Next: follow the final PR head through review, hosted checks and authorized merge; preserve finite source-epoch support limits.
Refs: results/preheader-20261030/report.md

## PHS · summary · 2026-10-30 00:37
Established: causal reproduction, opt-in guarded fetch route, preadmitted sealed-source v3 proof, strict legacy refusal, final local/installed checks and two-context cross-review. All twelve live slots and twenty-six controls are retained, including two setup failures and the read-only oracle repair.
Uncertain: default navigation still duplicates; universal browser delivery, arbitrary origins, hostile SQLite writers and active-user coexistence remain unqualified. Hosted checks and merge are pending separate observation.
Decision: publish the narrow checked source-epoch contract and follow PR through merge.
Refs: results/preheader-20261030/report.md; results/preheader-20261030/trials.json
