# AI visual control of the reusable bench

## SIM7-P1 · prediction · 2026-10-11 14:20
Hypothesis: an external multimodal AI can complete two successive prepare-measure-contact-reset cycles from images and task metadata, without detector/native pose guidance or weakening the existing guards.
Test: freeze a typed agent handoff, use the AI in this Codex session to inspect each RGB frame and author proposals, interrupt a prepared second-job measurement with a diagnostic native force, then independently score state and SQLite results after the attempt.
Predicts: two complete cycles, one measurement per job, one continuous bench identity, stale proposal refusal and fresh-image corrective actions after disturbance, with unchanged native guard source.
Against: native poses or the deterministic coordinate planner guide actions, stale evidence dispatches, either cycle exceeds its motion budget, reset assigns block state or guards need weakening.
Refs: docs/experiments/SIM7-agent-visual-bench.md; tools/physical-workcell/BENCH.md; results/agent-visual-bench-20261011/
