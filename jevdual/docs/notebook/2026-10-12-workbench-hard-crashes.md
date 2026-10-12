# Workbench hard-crash boundaries

## SIM13-E1 · exploratory · 2026-10-12 15:22
Question: which durable body/workbench and child-process boundaries can survive abrupt process death, and which require an unresolved outcome to stay blocked?
Test: source inspection of actual persistence, request association and process ownership; compare with qualified graceful restarts. Choose deterministic crash boundaries before implementing or running tests.
Refs: docs/experiments/SIM13-workbench-hard-crashes.md; tools/physical-workcell/body_network.py; tools/physical-workcell/network_operator_runtime.py; tools/physical-workcell/qualify_workbench_restarts.py

## SIM13-P1 · prediction · 2026-10-12 15:22
Hypothesis: exact durable receipts permit read-only recovery after a hard crash, while incomplete effect evidence remains blocked; neither case needs action replay.
Test: causal socket/native SIGKILL regressions followed by frozen actual-model browser trials at in-flight and uncertain body/workbench boundaries; independently inspect sends, receipts, native state, boot/control changes and owned children after cleanup.
Predicts: known receipts recover the original single-send command and leave the agent paused; Resume precedes fresh work. Missing or inconsistent proof stays visibly blocked with zero new effect admissions. No owned child writes across restarted root ownership.
Against: a command is resent, incomplete evidence grants success, old decisions gain new-boot authority, a stage loses its original identity or an owned child survives the restart boundary with write access.
Refs: docs/experiments/SIM13-workbench-hard-crashes.md; results/workbench-hard-crashes-20261012/

## SIM13-NATIVE · prediction · 2026-10-12 15:26
Hypothesis: killing the body after native state persistence but before the Bench terminal receipt leaves an unresolved effect that ordinary restart cannot safely complete from pose alone; killing after an indexed Agent receipt permits exact read-only recovery.
Test: an external diagnostic launcher stops immediately before Bench._finish on the first native move, binds its marker to the accepted dispatch, persisted next state and owned PID, then the harness issues SIGKILL. Compare with existing after_dispatch SIGSTOP followed by SIGKILL. Use public TCP readback and independent stopped native evidence.
Predicts: the native-gap case retains accepted server/agent intents, a busy Bench manifest and next-state bytes but no indexed lower result. Restart retains identities, advances boot, stays unknown and blocks successors without replay. The indexed-result case recovers its exact historical receipt with unchanged state and one send.
Against: pose is promoted to completion, restart/reconciliation repeats motion, identities or state diverge, owned native writers cross restart ownership or indexed proof cannot recover.
Refs: tools/physical-workcell/crash_body.py; tools/physical-workcell/test_crash_body.py; tools/physical-workcell/body_network.py; tools/physical-workcell/bench.py

## SIM13-HOST · prediction · 2026-10-12 15:26
Hypothesis: once the host has durable stage and client send identity and the body has a completed receipt, SIGKILL before reply delivery or while uncertain permits recovery of that exact command without replay.
Test: hold an actual completed dispatch response externally, kill the owned host, restart its retained root/port, then read its original receipt and explicitly Resume. Pair with already-uncertain body/host kills and stale control/source checks.
Predicts: the original command ID and immutable request persist, one actual body acceptance remains, no POST or model replay occurs during restart/receipt lookup, and explicit Resume precedes fresh observation. Abrupt host death at this gate has no active planner or native child.
Against: the stage loses command association, a decision or command is replayed, automatic continuation occurs or a live owned child writes across restart.
Refs: tools/physical-workcell/test_workbench_crash_runtime.py; tools/physical-workcell/qualify_workbench_crashes.py; tools/physical-workcell/score_workbench_crashes.py

## SIM13-U1 · update · 2026-10-12 15:26
Observed: source inspection identifies indexed lower receipts as the body's recovery proof. Existing before/after_dispatch barriers bracket lower dispatch; an external launcher can expose the deeper native-state-before-receipt gap. Host restart preserves sent command association at acknowledged boundaries, but arbitrary event-publication and pre-client-ID instruction windows have separate limitations. Independent Codex sessions can survive a host kill during active planning; selected command gates occur after planner completion and must prove no active planner.
Next: exercise owned hard-kill regressions and freeze four actual browser cases: host in-flight with known receipt, body after native motion without receipt, and each role with an already-uncertain known command.
Refs: tools/physical-workcell/body_network.py; tools/physical-workcell/network_operator_runtime.py; docs/experiments/SIM13-workbench-hard-crashes.md
