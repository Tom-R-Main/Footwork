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
