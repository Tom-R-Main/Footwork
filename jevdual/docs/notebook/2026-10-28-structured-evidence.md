# Structured operator evidence and qualified reconciliation

## SE1 · prediction · 2026-10-28 18:42
Hypothesis: a retained immutable runtime execution receipt, bound to the admitted attempt and captured after the bridge returns but before journal finalization, can reconcile loss of finalization without redispatch or authority recharging.
Test: simulate a real native command whose bridge returns but finish fails; reopen and explicitly reconcile from its retained receipt. Exercise qualified no-send, known sent/confirmed, sent/unknown, missing receipt, tampered identity/version/interval, repeated reconciliation and process death at receipt/finish boundaries.
Predicts: qualified terminal receipts resolve only their own attempt, settle reservation once and preserve unknown history; missing, ambiguous or mismatched receipts retain blocking. Reconciliation needs no app, secrets, current matching text or supplied claim file, and never dispatches input.
Against: a current readback or arbitrary caller assertion resolves a historical attempt, malformed receipts release custody, reconciliation sends input, or crash/replay double-charges authority.
Refs: docs/experiments/SE-structured-evidence-20261028.md; docs/plans/five-directions-20261028/IMPLEMENTATION-PLAN.md

## SE2 · prediction · 2026-10-28 18:42
Hypothesis: producer-bound typed observation/readback records can preserve exact field values and accurate coverage without promoting current agreement or persistence into historical execution/task proof.
Test: command and completion tests with values longer than the old 80-character prose cap, producer clipping at browser text boundaries, missing identity, malformed typed payloads, later edits, secret values and separate persistence predicates. Keep legacy readers compatible and qualify direct AX delivery only at actual acknowledgement boundaries.
Predicts: typed full values replace truncated prose as evidence only within their declared coverage and identity limits; malformed typed evidence never falls back into stronger prose claims; clipping is marked at its producer; current state, disk/window agreement and task fulfillment remain distinct.
Against: partial values are certified as exact, a malformed typed payload gains legacy proof, the wrong resource is certified, or secret values enter durable evidence.
Refs: docs/experiments/SE-structured-evidence-20261028.md

## SEU1 · update · 2026-10-28 19:09
Resolves: SE1 = held
Observed: frozen full-suite validation passed 1857 tests with 26 skipped. Real command scenarios retained a completed press before injected finish failure, then reconciled and replayed with no additional press or charge. Missing-return cancellation and known-sent/unknown-effect cases remain blocked. Three real SIGKILL receipt boundaries use an independent fsynced input ledger. Tampered, mismatched and unsupported receipts do not resolve custody; repeated reconciliation preserves history and settlement.
Inferred: retained producer evidence can close the receipt-to-finalization gap without turning current agreement or a supplied assertion into historical execution proof. Interruption before receipt retention remains unknown.
Next: commit scoped evidence/reconciliation; keep app-specific qualification pending.
Refs: results/structured-evidence-20261028/report.md; results/structured-evidence-20261028/suite.txt

## SEU2 · update · 2026-10-28 19:09
Resolves: SE2 = held
Observed: baseline producer/projection code lost the browser clipping flag at 6001 characters; the retained reproduction fails its coverage assertion and six corrected cases pass. A real CLI live-check append retains the complete bounded AX-read value. Malformed typed evidence does not fall back to prose, contradicted state is limited, redacted values withhold exactness, and persistence does not become task proof. Review's admitted/live target linkage and redacted-placeholder findings were corrected.
Inferred: exact facts require complete producer readback and qualified linkage, not a typed schema alone. Coverage describes the normalized projection rather than original webpage bytes. TextEdit here is an existing simulated regression fixture, not an additional qualified application.
Next: use these contracts in app-specific qualification and preserve the documented runtime/identity limits.
Refs: results/structured-evidence-20261028/browser-before.txt; results/structured-evidence-20261028/browser-coverage.txt; results/structured-evidence-20261028/report.md

## SES1 · summary · 2026-10-28 19:09
Established: enrolled native CLI sessions retain validated execution receipts before finalization and reconcile only from those receipts. Structured observations/current-state/persistence facts expose provenance, coverage and limits with legacy compatibility. Final regression: 1857 passed, 26 skipped; Ruff clean; independent review found no remaining blocking findings.
Uncertain: missing or ambiguous receipts still block; older unknowns cannot acquire new execution proof from current state. Independent window birth, secret rotation, power-loss durability, app-specific task effects and installed app diversity remain unqualified.
Decision: commit this bounded implementation and evidence. Next qualify Finder/Preview operations with independent oracles before browser submission and interrupted cross-app handoff qualification.
Refs: docs/durable-native-operator.md; results/structured-evidence-20261028/report.md; docs/plans/five-directions-20261028/IMPLEMENTATION-PLAN.md
