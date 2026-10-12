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
