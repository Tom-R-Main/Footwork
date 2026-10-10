# Image-guided physical and computer workcell

## SIM2 · prediction · 2026-10-10 15:41
Hypothesis: an AI agent using rendered RGB views and known camera calibration can locate the simulated block, move it, observe residual placement error and correct it before a visually gated local computer action.
Test: unchanged SIM1 dynamics with an isolated image wrapper, fresh generation/digest-bound proposals, actual RGB box/pixel checks, bounded native contact moves, at least one image-informed correction, final image placement and separate native oracle, exact saved result readback. Freeze implementation before parent-run public trial; exercise visual/stale/tamper/no-replay counterexamples.
Predicts: the planner needs no native block coordinates; final visual placement agrees with oracle; only fresh visual plus native physical evidence allows the computer result. Bad/ambiguous/stale evidence and unknown effects remain refused or unresolved.
Against: hidden-state-driven planning, prerecorded moves reported as AI visual decisions, wrong/blank image accepted, completion without fresh visual evidence, repeated effect or no corrective movement demonstrated.
Refs: docs/experiments/SIM2-image-guided-workcell.md; results/physical-workcell-20261010/report.md; /Volumes/External SSD/referencerepos/mujoco/doc/XMLreference.rst
