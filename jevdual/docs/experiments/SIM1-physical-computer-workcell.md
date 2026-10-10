# SIM1: Simulated physical action coupled to a computer work order

Mode: bounded MuJoCo control/verification feasibility, not real-robot or learned-vision qualification.

## Hypothesis

An agent-facing observe/act/complete interface can use native MuJoCo physics and a bounded controller to move one simulated block into a work-order inspection zone. A computer work-order update is emitted only after observed simulator state satisfies the explicit physical predicate, and Footwork independently verifies the saved software result.

## Predictions

A small planar pusher uses actuator commands and real simulated contacts (no teleporting or externally setting the block pose). State persists between CLI processes; observations identify generation, body frame, block/pusher pose and whether the target-zone predicate holds. Admitted movement advances physics under fixed controller bounds. Completion before the block is in-zone refuses a successful computer result; completion after a verified move creates one digest-bound work-order result checked by public Footwork check-artifact. Repeated tokens do not reapply movement or duplicate results. Stale-generation/out-of-envelope requests refuse before dispatch; interrupted/unreceipted action blocks replay.

Against: setting the block pose directly instead of using physics; empty motion reported as fulfilled without state readback; software order marked completed while physical predicate fails; stale/unsafe motion admitted; repeated or unknown movement replayed; simulator ground truth passed off as real camera/robot evidence.

## Design

Keep prototype in tools/physical-workcell. Install pinned mujoco==3.15.0 in its own ignored virtual environment under the user's download authorization. Use an included small XML model: tabletop plane, free block and XY pusher with native position actuators. Use a smooth bounded target trajectory and fixed simulation stepping/settling; retain model/controller hashes and work-order digest. Only a known block/task and contained workspace are supported.

Provide init/observe/act/complete with private owned run state, process lock, explicit generation and operation token/argument binding. Serialize MuJoCo integration state without pickle; do not silently reset physics on lookup. Keep observation/frame source_kind=mujoco_simulation and outcomes of physical predicate versus software artifact separate. Optional native simulator rendering is helpful evidence but not image-recognition qualification. Proposed robot hardware/ROS/LeRobot adapters remain unimplemented.

Primary metric: the observed simulated block reaches its explicit zone and exactly one corresponding local work-order result is independently checked (binary). Negative criterion: before motion/outside zone the same completion cannot succeed.

Checks: actual native engine public CLI across fresh processes; before/after observed poses and moved block under contacts; constrained motion bounds; stale token/generation and repeated actions; unknown/lost receipts no replay; conditional digital result and tamper/missing result; optional render/readback. No new camera acquisition, provider call, external project write or physical actuator effect.

Decision rule: qualify only demonstrated simulation/native-controller/local-computer coupling. This supplies a usable bounded body interface for an agent, not general locomotion/manipulation, visual grounding, real-time OS guarantees or transfer to hardware. If contact dynamics or rendering fails, preserve evidence and distinguish the failing mechanism before changing source/model settings.

## Result

Pending.
