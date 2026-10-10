# Simulated physical and computer workcell

## SIM1 · prediction · 2026-10-10 15:28
Hypothesis: native MuJoCo contact dynamics plus a bounded XY controller can move a simulated block into a task-defined zone, enabling a subsequent computer work-order update only after observed state qualifies.
Test: isolated agent-facing init/observe/act/complete public CLI on pinned MuJoCo 3.15.0, state persistence between processes, explicit tokens/generations/bounds, before/after physical poses, conditional saved result independently checked through Footwork. Freeze source/model before measured run; test counterexamples and no replay.
Predicts: contacts actually move the free block; software result appears once only after the in-zone predicate; false/stale/out-of-envelope/unknown requests cannot become success or replay. Simulator evidence is labeled separately from camera/real hardware.
Against: block teleport or implicit reset, no-op falsely verified, outside-zone computer completion, unbounded/stale dispatch, token replay or simulated evidence claimed as real-world control.
Refs: docs/experiments/SIM1-physical-computer-workcell.md; /Volumes/External SSD/referencerepos/mujoco/; /Volumes/External SSD/referencerepos/lerobot/src/lerobot/robots/robot.py; results/workbench-20261010/report.md
