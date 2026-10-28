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
