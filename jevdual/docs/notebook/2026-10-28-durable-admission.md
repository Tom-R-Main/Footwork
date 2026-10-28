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

## OAU1 · update · 2026-10-28 18:09
Observed: the new core and existing journal/recovery slice passed 75 tests, including synchronized real SIGKILL at five boundaries with a separate fsynced input ledger. The initial integrated slice passed 186 tests. Subsequent secrecy qualification exposed a pre-existing FrozenInstanceError in secret snapshot copying before the driver boundary; it was corrected and a real type/cancellation/replay scenario now reaches the intended boundary. Final regression is running on the frozen implementation.
Inferred: attempted input alone cannot settle authority as sent. The implementation now retains the SDK delivery count separately; unknown delivery holds a reservation, and known-sent/unknown-effect spends it while preserving the block. No independent window-birth oracle or general started-unknown reconciliation producer is present, so these remain explicit qualification limits.
Next: finish frozen full-suite, lint and notebook checks, retain result evidence, and commit the bounded native CLI admission implementation.
Refs: results/durable-admission-20261028/; tests/test_session_operations.py; tests/test_session_scenarios.py; docs/durable-native-operator.md

## OAU2 · update · 2026-10-28 18:11
Resolves: OA1 = held; OA2 = held
Observed: frozen full-suite validation passed 1774 tests with 26 skipped, including real command cancellation/blocking/replay and five real subprocess SIGKILL boundaries. Required authority and intent roll back together on injected transaction faults; prepared-only recovery releases once; started unknowns block the shared domain; final projection repair and replay send no additional input. Existing capability/recovery regressions pass without modifying their Journal implementation. Repository Ruff, notebook format and diff checks pass.
Inferred: reuse of the existing journal is sufficient for this bounded native CLI custody protocol. Replay does not depend on current app/secret availability. This does not supply a general reconciliation producer or prove independent window birth, secret-rotation-safe observation, installed app behavior or power-loss safety.
Next: commit the native admission package and proceed to producer-backed evidence/qualified reconciliation before diversified live app qualification.
Refs: results/durable-admission-20261028/report.md; results/durable-admission-20261028/suite-final.txt

## OAS1 · summary · 2026-10-28 18:11
Established: explicitly enrolled native CLI sessions share durable admission, transactional required-grant reservations, stable token replay, conservative recovery and projection repair. Independent implementation review's delivery and secrecy findings were resolved. The resulting custody contract is exercised by simulated command scenarios and real subprocess-death tests.
Uncertain: started unknown operations have no general reconciliation producer and remain blocking; direct AX uncounted routes can remain unknown. No independent window-birth oracle, installed app qualification, secret rotation or other-runtime coordination is established.
Decision: retain explicit opt-in and these qualification limits. The next implementation package must strengthen actual evidence producers and reconciliation, keeping Finder/Preview/browser qualification pending until their own oracles and adapters pass.
Refs: docs/durable-native-operator.md; results/durable-admission-20261028/report.md; docs/plans/five-directions-20261028/IMPLEMENTATION-PLAN.md

## OAU3 · update · 2026-10-28 18:11
Resolves: OA2 = held
Observed: the notebook reader recognizes only the first prediction in OAU2's compound resolution. This entry separately closes OA2 using the same final replay, projection repair, authority-conservation and interruption evidence; no runtime claim or prediction is changed.
Next: producer-backed evidence and qualified reconciliation, retaining the stated native CLI qualification limits.
Refs: results/durable-admission-20261028/report.md; results/durable-admission-20261028/suite-final.txt
