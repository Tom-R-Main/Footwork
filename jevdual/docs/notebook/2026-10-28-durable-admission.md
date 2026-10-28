# Durable native operator admission

## OA1 · prediction · 2026-10-28 17:56
Hypothesis: the existing Journal transaction, exclusive ownership and operation rows can provide native CLI admission with additive operator metadata/grant/reservation tables, without changing MCP recovery semantics.
Test: transactional conservation and replay tests, real command cancellation/retry scenarios, two independent session directories sharing one authority DB, and synchronized subprocess SIGKILL tests around prepared/started/effect/finish boundaries with an independent input ledger.
Predicts: intent and any required reservation commit together; no input precedes started; prepared-only recovery releases once; started unknown blocks new domain mutations and replay sends nothing; known-delivered unknown-effect remains blocked with spent authority; existing capability tests remain green.
Against: a crash permits redispatch or authority reuse, a transaction leaves only one of intent/reservation, recovery mistakes unknown input for no-send, or compatibility requires changing existing MCP custody behavior.
Refs: docs/experiments/OA-durable-admission-20261028.md; docs/plans/five-directions-20261028/IMPLEMENTATION-PLAN.md; results/operator-dispatch-20261028/report.md

## OA2 · prediction · 2026-10-28 17:56
Hypothesis: replay before observation/secret resolution and journal-authoritative projection repair can preserve a completed or unresolved operation across a lost response without additional input or double grant charging.
Test: replay after effect and before session projection, altered-token payload, missing carry/secret on replay, stale projection, concurrent command ownership, and changed process identity before a new admission.
Predicts: original token returns retained status with zero additional input; changed arguments conflict; unavailable current dependencies do not prevent exact replay; participating writers serialize before mutable state reload; resource changes invalidate prior grants and binding.
Against: replay needs fresh authorization/binding, duplicates an effect, consumes another use, or session projection can authorize an action absent from the durable record.
Refs: docs/experiments/OA-durable-admission-20261028.md
