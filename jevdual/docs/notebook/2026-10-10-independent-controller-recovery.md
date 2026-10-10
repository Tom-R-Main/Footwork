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

## SIM4-U4 · update · 2026-10-10 18:22
Observed: all 67 scoped regressions passed on the pre-freeze version. A subsequent root review found shutdown releasing both ownership locks if its bounded join timed out while a non-daemon worker remained alive; the lower artifact checker timeout exceeded that join interval. A targeted actual-process slow-checker/short-join fault reproduced both locks becoming available before the writer ended (one failing scenario, 3.400 s). No native stop was claimed by that timing-fault test.
Inferred: a successful ordinary regression suite did not cover ownership during failed graceful shutdown. The controller must abort the whole process on join timeout rather than release locks under a live writer, retaining uncertainty rather than a stopped claim.
Next: fix the abort fallback, run the new ownership regression and full scoped suite, then freeze source before independent diagnostics. SIM4R remains untested by independent source-frozen trials.
Refs: results/independent-controller-20261010/pre-shutdown-fix-checks.json; tools/physical-workcell/output/c4-shutdown-before-fix/unittest.log; tools/physical-workcell/output/c416f26c/conformance.json

## SIM4-U5 · update · 2026-10-10 18:29
Observed: frozen 5713173 passed all 68 scoped tests and Ruff. Independent public service diagnostics report nine passing checks, covering eight required scenarios plus admission negatives. Live cancellation retains 156 advancing native steps plus 500 settle steps and velocity/state stop evidence. The crash trial killed after public running status plus 0.45 seconds; its retained native journal proves dispatch intent but cannot prove native stepping before death. Process cleanup and exact frozen hashes are retained.
Inferred: public response/history checks passed, but the strict during-motion kill requirement needs stronger observation than a timed running status. No runtime defect or source change is established by this evidence gap.
Next: preserve the original trial and run a fresh supplemental case with explicit observation-only tracing around the real native step; do not change controller behavior or reuse the earlier episode.
Refs: tools/physical-workcell/output/s4audit/verification.json; results/independent-controller-20261010/source-freeze.json; checks.json

## SIM4P · prediction · 2026-10-10 18:29
Hypothesis: an observation-only marker written after a real mj_step returns can establish native execution before process death while preserving the controller's frozen source, dynamics and proposal admission.
Test: new owned supplemental episode and real native-step wrapper that calls the original function unchanged, records its first return outside the episode, then signals the exact controller PID; restart uninstrumented and compare native generation/state/receipt history and stale-incarnation admission.
Predicts: native-step marker identifies the killed PID before SIGKILL; restart remains unknown with no extra generation/dispatch, old-incarnation effects refuse and all owned processes exit.
Against: trace cannot identify actual step completion, changes native inputs/outputs, kill occurs before marker, replay or fabricated execution/stop history, changed frozen source or leaked owned resources.
Refs: docs/experiments/SIM4-independent-controller-recovery.md; tools/physical-workcell/output/s4audit/06-running-kill/events.json

## SIM4-U6 · update · 2026-10-10 18:33
Resolves: SIM4R = held
Observed: frozen 5713173 passed 68 scoped tests and Ruff. Nine independent public-service response/history checks passed; the fresh supplemental crash probe closes the native-progress gap for the required during-motion kill. All eight required lifecycle scenarios are supported, including conservative unknown/blocked outcomes. Parent read-only scoring checked retained cancellation state/velocity, real contact fulfillment, saved original artifact bytes and unchanged native generations on replay attempts; run-file hashes were unchanged. Deliberate current-artifact tamper remains a retained negative result. All diagnostic processes exited and automatic sockets were removed.
Inferred: the corrected isolated controller supports caller-independent execution, truthful simulated cancellation and exact-receipt recovery for these selected cases. Small diagnostics, controlled saved-record faults and observation-only timing instrumentation do not establish broad reliability, power-loss/hardware recovery or AI planning value.
Next: close SIM4 with its failed first implementation and complete evidence limits; separately preregister versioned application fulfillment before adding a real software workflow.
Refs: results/independent-controller-20261010/report.md; qualification.json; checks.json; source-freeze.json; development-attempts.json; 5713173

## SIM4-U7 · update · 2026-10-10 18:33
Resolves: SIM4P = held
Observed: a new supplemental episode forwarded the original native mj_step inputs/return unchanged and recorded its first completed call from the motion worker (PID 11039) before SIGKILL. Restart used the uninstrumented frozen source, a new incarnation and unknown history. Same-ID submission returned that unknown without another native generation; stale-incarnation cancellation refused. Marker, commands, source/driver hashes and cleanup are retained.
Inferred: this provides explicit native execution-before-death evidence absent from the original timed running-kill trial, without identifying any unretained final pose. Tracing adds observation overhead and is disclosed.
Next: retain both probes and do not promote the first timed trial into direct native-progress evidence.
Refs: tools/physical-workcell/output/s4parent/supplemental-verification.json; results/independent-controller-20261010/qualification.json; 578d73d

## SIM4-S1 · summary · 2026-10-10 18:33
Established: independent process ownership, exact image-bound operation identity and incarnation admission, reconnectable history without duplicate effects, native held-command cancellation with retained stop evidence, conservative restart and history/current-state separation. All eight selected lifecycle scenarios are supported; 68 scoped tests and Ruff passed. Initial recovery/binding/shutdown defects and observation-driver mistakes are preserved.
Uncertain: hardware/power-loss/realtime guarantees, general perception, every lower-layer interruption window, application identity and fulfillment, production capability-service governance, and measured AI value. Screensaver/sleep behavior was not tested; no visible desktop was required.
Decision: adopt the controller under tools/physical-workcell, retain Python/native MuJoCo and the deterministic RGB movement helper, and make versioned application handoff the next separate experiment.
Refs: results/independent-controller-20261010/report.md; qualification.json; docs/experiments/SIM4-independent-controller-recovery.md; 5713173
