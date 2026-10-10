# Independent simulated controller recovery

## SIM4 · prediction · 2026-10-10 18:05
Hypothesis: a separately running controller with durable acceptance, exact operation identity and lower-layer receipt reconciliation can survive caller loss without duplicate effects and can distinguish a cancellation request from verified stop.
Test: actual private Unix-socket service/client processes and native MuJoCo execution; preregister lifecycle scenarios, develop on private cases, freeze source, then independently drive disconnect, active return, cancellation, restart and conditional artifact completion.
Predicts: host loss does not end controller execution; repeated IDs return history without motion; queued cancellation dispatches nothing; running cancellation retains bounded stop evidence or stays unknown; restart uses exact historical receipts and never current placement as execution history.
Against: caller loss stops the body, duplicate dispatch, cancellation acknowledgement masquerades as stop, source/case reuse, legacy commands race ownership, replay after restart or success manufactured from a satisfied scene.
Refs: docs/experiments/SIM4-independent-controller-recovery.md; results/repeatable-work-orders-20261010/report.md; /Volumes/External SSD/referencerepos/dora/examples/action-example/server/src/main.rs; /Volumes/External SSD/referencerepos/openpnp/src/main/java/org/openpnp/spi/MotionPlanner.java

## SIM4-U1 · update · 2026-10-10 18:12
Observed: independent pre-freeze source review found idle health calling current state load before returning a valid historical goal, so missing current state could suppress history. Startup also depended on current state. Initial accepted-file creation synced file contents but not its parent directory; this limits acceptance durability claims. Development process conformance is underway, with live socket loss/SIGKILL distinguished from simulated retained-write faults.
Inferred: historical status and current integrity need separate failure handling; acceptance needs an owned-directory sync before acknowledgement. These are source findings, not yet observed qualification failures. Native-only terminal receipts with an unfinished image wrapper intentionally remain unknown.
Next: fix the history/current seam, add a current-corruption regression and sync acceptance before acknowledgement; finish development checks, then freeze runtime before independent lifecycle driving.
Refs: tools/physical-workcell/controller.py; tools/physical-workcell/test_controller.py; c78d2a4

## SIM4-U2 · update · 2026-10-10 18:14
Observed: the first development process run stopped with nine startup-only harness failures and exit 130. The driver looked for a fixed socket filename instead of the service's advertised socket_path; no goals were submitted and owned processes were cleaned up. The original test source/hash, failure paths and summary remain private. The driver now reads the declared path; a current-state corruption/history-only restart regression is added while runtime repairs are completed.
Inferred: this attempt supplies no controller lifecycle evidence. The mismatch was in observation setup rather than a demonstrated motion or recovery failure.
Next: rerun the corrected conformance after source stabilization; preserve this attempt separately from later diagnostic outcomes.
Refs: tools/physical-workcell/output/c4-initial-socket-failure/summary.json; tools/physical-workcell/test_controller.py

## SIM4-U3 · update · 2026-10-10 18:17
Resolves: SIM4 = failed
Observed: targeted process scenarios failed before fixes: a saved unknown controller fallback with intact lower terminal receipts did not reconcile on restart, and live health remained ready after retained controller-binding tamper. The corrected startup now attempts exact read-only reconciliation for unknown records, and live validation rereads retained binding. The earlier fifteen-process run had fourteen passes plus a harness enum mismatch: blocked observation after SIGKILL was conservatively correct but excluded by the test's accepted phase set. That assertion now requires no observation authority. All development attempts are retained; the revised seventeen-case conformance is running before freeze.
Inferred: the first implementation did not meet the original recovery/binding prediction. Independent ownership alone was insufficient: exact receipt reconciliation must include durable fallback uncertainty, and cached identity checks must include retained controller binding. The corrected runtime remains to be independently qualified.
Next: freeze the corrected source after regression checks, then independently drive all eight preregistered lifecycle scenarios and retained failure paths.
Refs: tools/physical-workcell/output/c4-unknown-fallback-before-fix/unittest.log; tools/physical-workcell/output/c4-live-binding-before-fix/unittest.log; tools/physical-workcell/output/c4-process-run-v2/unittest.log

## SIM4R · prediction · 2026-10-10 18:17
Revises: SIM4
Hypothesis: with live retained-binding validation, historical/current evidence separation and exact lower-receipt reconciliation for uncertain fallback records, the corrected frozen controller will pass independent lifecycle driving without replay or invented stop/history.
Test: source-frozen independent public CLI/socket trials of all eight preregistered scenarios, including actual reply loss and SIGKILL; distinguish controlled journal faults, retain all failures and compare exact saved native/artifact digests.
Predicts: returning clients retrieve known completed history; actual in-motion cancellation retains a verified stop; controller death remains unknown unless exact terminal evidence supports recovery; stale bindings refuse; normal contact fulfills the conditional saved-byte-checked order.
Against: duplicate motion, queued cancellation dispatch, false stopped/fulfilled claims, lost historical result from unavailable current state, accepted stale binding or incomplete lower evidence promoted to success.
Refs: docs/experiments/SIM4-independent-controller-recovery.md; results/independent-controller-20261010/diagnostic-plan.json
