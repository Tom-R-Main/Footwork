# Persistent network body: qualified in simulation

The adapter passed its twelve-case TCP fault matrix and the first frozen actual-model attempt: two successive camera-guided jobs on one retained MuJoCo body. Each job placed the block, saved a separately computed measurement in SQLite and reset through physical contact.

Measured source: `e8c7e9b502f852639a89932aa30884a40a432ca9`. Preregistration: `c976508`. The exact measured files remain unchanged. Existing native guards and the local browser product were not edited.

| Evidence | Result |
| --- | --- |
| Public TCP fault matrix | 12/12 cases passed on final source |
| Focused server/client checks | 13 + 11 passed |
| Existing bench/agent guard checks | 29 passed |
| Actual Codex image decisions | 27; all dispatched outcomes executed |
| Native movements | 21; maximum recorded axis actuator force 1.452 N, below the existing 4 N limit |
| Independently scored cycles | 2/2; measurement placement, SQLite receipt identity and contact resets passed |
| Transport commands | 83; bound to immutable requests and lower receipts |
| Process cleanup | All 27 model processes and the trial service exited; proxy closed |

Body `ab384557b47e442891620c90252a52ca` retained generation 0 → 11 → 21, with completed native times 22.946 → 43.760 seconds. Separate native-state reconstruction verified each measured placement and home reset; read-only SQLite scoring verified exactly one measurement per job. Model input contained the exact SHA-verified PNG fetched through TCP, task geometry and bounded history. No native pose or detector locations were supplied to the model.

The actual-model trial discarded the first movement's reply after the body had acted. The client retained uncertainty and issued one GET for that exact command's receipt, with one original POST and no resubmission. Another movement was forwarded twice concurrently with identical payloads and identical historical replies. A third reply was delayed by 0.2 seconds. All three fault events bind to retained command evidence.

The mechanical matrix separately covered delays before and after forwarding, dropped requests, dropped replies, concurrent duplicates, conflicting duplicates, stale image proposals, lease expiry during delay, wrong identities/source/epochs, exclusive leases, process restart, crash after lower receipt before transport receipt, and accepted intent without lower proof. Proven receipt recovery reads lower records without dispatch. Missing proof remains unknown and blocks new commands, including after a separate client process restarts.

The first server suite failed seven cases because an extra envelope field violated its closed schema. Two targeted regressions also reproduced a premature cache update and an undersized local journal reader. Repairs preserve the failures; the complete matrix was rerun on final source. The 256-record capacity fixture tests local journal reload and refusal before send 257; it is not evidence of 256 native effects. All development attempts remain in the ledger and private run directories.

This qualifies same-host loopback TCP simulation and these two model jobs. Authentication, operation across machines, real hardware, power-loss recovery and broad model repeatability remain unqualified. Leases fence new admissions; an accepted bounded movement can finish after a disconnect. The browser product at port 64370 remains local, open and idle with its two earlier completed jobs. The new adapter is available through its service/client API and qualification CLI.

Evidence: [independent score](qualification-score.json), [fault matrix](fault-matrix.json), [conformance](conformance-summary.json), [cleanup and actual fault binding](final-checks.json), [source freeze](source-freeze.json), [actual-model attempts](attempt-ledger.json), [development attempts](retained-development-attempts.json). Private raw trial: `tools/physical-workcell/output/sim9-network-ai-v1/`.

Usage and verification: [network body runbook](../../../tools/physical-workcell/NETWORK_BODY.md). The service owns the persistent body; the client owns image transport and command uncertainty; the existing Bench and AgentBench own local effect guards. No new dependency or language runtime was added.
