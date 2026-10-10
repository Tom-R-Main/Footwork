# Independent simulated controller recovery

## SIM4 · prediction · 2026-10-10 18:05
Hypothesis: a separately running controller with durable acceptance, exact operation identity and lower-layer receipt reconciliation can survive caller loss without duplicate effects and can distinguish a cancellation request from verified stop.
Test: actual private Unix-socket service/client processes and native MuJoCo execution; preregister lifecycle scenarios, develop on private cases, freeze source, then independently drive disconnect, active return, cancellation, restart and conditional artifact completion.
Predicts: host loss does not end controller execution; repeated IDs return history without motion; queued cancellation dispatches nothing; running cancellation retains bounded stop evidence or stays unknown; restart uses exact historical receipts and never current placement as execution history.
Against: caller loss stops the body, duplicate dispatch, cancellation acknowledgement masquerades as stop, source/case reuse, legacy commands race ownership, replay after restart or success manufactured from a satisfied scene.
Refs: docs/experiments/SIM4-independent-controller-recovery.md; results/repeatable-work-orders-20261010/report.md; /Volumes/External SSD/referencerepos/dora/examples/action-example/server/src/main.rs; /Volumes/External SSD/referencerepos/openpnp/src/main/java/org/openpnp/spi/MotionPlanner.java
