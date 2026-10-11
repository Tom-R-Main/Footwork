# AI visual control of the reusable bench

## SIM7-P1 · prediction · 2026-10-11 14:20
Hypothesis: an external multimodal AI can complete two successive prepare-measure-contact-reset cycles from images and task metadata, without detector/native pose guidance or weakening the existing guards.
Test: freeze a typed agent handoff, use the AI in this Codex session to inspect each RGB frame and author proposals, interrupt a prepared second-job measurement with a diagnostic native force, then independently score state and SQLite results after the attempt.
Predicts: two complete cycles, one measurement per job, one continuous bench identity, stale proposal refusal and fresh-image corrective actions after disturbance, with unchanged native guard source.
Against: native poses or the deterministic coordinate planner guide actions, stale evidence dispatches, either cycle exceeds its motion budget, reset assigns block state or guards need weakening.
Refs: docs/experiments/SIM7-agent-visual-bench.md; tools/physical-workcell/BENCH.md; results/agent-visual-bench-20261011/

## SIM7-DEV-U1 · update · 2026-10-11 14:27
Observed: source review required stored unknown host results to block future proposals even when the underlying bench was ready. A new native-move/lost-host-reply check exercised that gap and passed after the host guard was implemented. Public CLI responses now filter detector coordinates from saved measurement/status receipts while retaining full evidence privately. Fifteen final interface conformance checks passed. Four initial test errors reflected exception classes from separately loaded helper modules; their fixture evidence is retained and assertions were corrected without changing native guard behavior.
Inferred: effect readiness alone is insufficient to resolve a host's uncertain dispatch, and measurement output can accidentally become numeric perception guidance unless the model-input boundary filters it.
Next: freeze measured source, initialize a fresh bench/session, and run actual AI-authored image-based actions before independent scoring.
Refs: tools/physical-workcell/output/a7-suite-b8f88806f5/suite.log; tools/physical-workcell/test_agent_bench.py; tools/physical-workcell/agent_bench.py
