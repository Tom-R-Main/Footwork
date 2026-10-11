# Reusable simulated bench

## SIM6-P1 · prediction · 2026-10-11 13:57
Hypothesis: a persistent integration state and image-bound job transitions can support two prepare-measure-contact-reset cycles, including recovery after a bounded external-force disturbance, without recreating the block.
Test: implement an isolated bench and RGB host; run focused development checks, then freeze and independently exercise two successive jobs, stale evidence after disturbance, measurement readback and native reset scoring.
Predicts: one bench identity and increasing generations/native time span both cycles; each job has one measurement, physical contact reset, and the disturbed job rejects stale evidence before fresh observation guides recovery.
Against: stale evidence dispatches an effect, reset assigns body pose, job two begins before reset verification, the body is recreated, or disturbance recovery fails within the declared budget.
Refs: docs/experiments/SIM6-reusable-bench.md; tools/physical-workcell/; results/reusable-bench-20261011/

## SIM6-DEV-U1 · update · 2026-10-11 14:05
Observed: the first source-stable development sequence completed two cycles on bench df2c545a1cee4405b9ce2bd3eedfc149. Generations advanced from 0 to 29 to 70. A native external-force intervention displaced the RGB block center by 0.1333 m; stale motion and measurement refused before fresh observations guided recovery. Both resets retained native contact evidence and both measurement results were independently persisted by separate processes.
Inferred: the axial RGB routing and contact reset mechanism work in this development fixture. This is not the frozen independent qualification and does not yet resolve SIM6-P1.
Next: complete retained measurement-integrity and reset evidence guards, run focused conformance, freeze source, then qualify a fresh two-job sequence with separate native/SQLite scoring.
Refs: tools/physical-workcell/output/sim6-root-dev1/ordinary-journal/; tools/physical-workcell/output/sim6-root-dev1/disturbed-journal/; tools/physical-workcell/output/sim6-root-dev1/ordinary.stdout.json; tools/physical-workcell/output/sim6-root-dev1/disturbed.stdout.json
