# Simulated physical and computer workcell

## SIM1 · prediction · 2026-10-10 15:28
Hypothesis: native MuJoCo contact dynamics plus a bounded XY controller can move a simulated block into a task-defined zone, enabling a subsequent computer work-order update only after observed state qualifies.
Test: isolated agent-facing init/observe/act/complete public CLI on pinned MuJoCo 3.15.0, state persistence between processes, explicit tokens/generations/bounds, before/after physical poses, conditional saved result independently checked through Footwork. Freeze source/model before measured run; test counterexamples and no replay.
Predicts: contacts actually move the free block; software result appears once only after the in-zone predicate; false/stale/out-of-envelope/unknown requests cannot become success or replay. Simulator evidence is labeled separately from camera/real hardware.
Against: block teleport or implicit reset, no-op falsely verified, outside-zone computer completion, unbounded/stale dispatch, token replay or simulated evidence claimed as real-world control.
Refs: docs/experiments/SIM1-physical-computer-workcell.md; /Volumes/External SSD/referencerepos/mujoco/; /Volumes/External SSD/referencerepos/lerobot/src/lerobot/robots/robot.py; results/workbench-20261010/report.md

## SIM1-U1 · update · 2026-10-10 15:37
Resolves: SIM1 = held
Observed: frozen source/model ece54ae moved the free block by native contact into the bound zone, refused premature software completion, retained physics across public CLI processes, refused stale/out-of-envelope requests and did not redispatch repeated tokens. The conditional local order passed a separate public Footwork byte check. Actual native before/after render images were inspected.
Inferred: this bounded simulator/controller interface can couple observed physical fulfillment to a subsequent local computer effect. It does not qualify a visual policy or real hardware.
Next: close SIM1; camera-grounded observation is the next proposed physical-body experiment.
Refs: results/physical-workcell-20261010/independent-demo.json; results/physical-workcell-20261010/report.md; tools/physical-workcell/test_workcell.py

## SIM1-S1 · summary · 2026-10-10 15:37
Established: bounded contact action, persisted observation generations, conditional local work-order completion and no replay demonstrated on pinned native MuJoCo. The independent public run passed; scoped actual-engine conformance covers local refusal/failure paths.
Uncertain: learned planning, camera grounding, general manipulation/navigation, hardware transfer, controller timing and external software integration remain unqualified.
Decision: retain the prototype inside tools/physical-workcell and the project-linked notes as supporting evidence. Build camera-grounded observation before expanding to additional bodies; preserve separation between model intent, controller execution and physical/computer readback.
Refs: docs/experiments/SIM1-physical-computer-workcell.md; results/physical-workcell-20261010/report.md; results/workbench-20261010/route-profile.json
