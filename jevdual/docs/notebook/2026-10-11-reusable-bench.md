# Reusable simulated bench

## SIM6-P1 · prediction · 2026-10-11 13:57
Hypothesis: a persistent integration state and image-bound job transitions can support two prepare-measure-contact-reset cycles, including recovery after a bounded external-force disturbance, without recreating the block.
Test: implement an isolated bench and RGB host; run focused development checks, then freeze and independently exercise two successive jobs, stale evidence after disturbance, measurement readback and native reset scoring.
Predicts: one bench identity and increasing generations/native time span both cycles; each job has one measurement, physical contact reset, and the disturbed job rejects stale evidence before fresh observation guides recovery.
Against: stale evidence dispatches an effect, reset assigns body pose, job two begins before reset verification, the body is recreated, or disturbance recovery fails within the declared budget.
Refs: docs/experiments/SIM6-reusable-bench.md; tools/physical-workcell/; results/reusable-bench-20261011/
