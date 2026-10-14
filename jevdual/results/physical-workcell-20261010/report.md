# SIM1: Physical and computer workcell

The independent public CLI run passed on frozen source/model commit `ece54ae`, after prediction commit `49904e3`. Native MuJoCo contact moved the block into the bound work-order zone; only then did the conditional computer action create a local staged order. A separate public Footwork check verified the saved bytes.

## Evidence

`independent-demo.json` retains public command arguments, exit codes, source/model hashes, observations, controller evidence, artifact checks and assertions. `environment.json` records the isolated pinned runtime. The private run is `tools/physical-workcell/output/demo-v1`; its two inspected native renders are `render-000000.png` and `render-000001.png`.

| Check | Observed |
|---|---|
| Before physical condition | Block x = -0.119999988 m; center outside zone |
| Premature completion | Refused; no software order file created |
| Native contact motion | Block x = 0.200757019 m; center inside x=[0.18,0.26], y=[-0.04,0.04] m |
| Controller | 2,000 native steps; 4,192 pusher/block contact samples; peak axis actuator force 1.278071451 N against a 4 N cap |
| Fresh process | Same generation, state hash and block pose; no implicit reset |
| Stale/out-of-envelope requests | Refused before dispatch |
| Conditional computer result | One local `order.json` with state `staged`; separate public Footwork byte check passed |
| Repeated motion/completion tokens | Retained physics, result and manifest bytes unchanged; no redispatch |
| Native rendering | Actual MuJoCo RGB before/after images inspected; source identified as simulation |

The scoped conformance suite passed 13 tests on the actual pinned native engine. It also covers noncontact motion failing fulfillment, lost physical/software receipts, interrupted state publication, tampered state/order/model/runtime, missing/tampered results without recreation, invalid/nonfinite inputs and cross-process ownership. Fault injection tests address local bookkeeping failures; they do not qualify hardware failure recovery.

## Decision

Keep this prototype under `tools/physical-workcell`, inside Footwork. The agent-facing interface is `init`, `observe`, `act`, `complete`, with separate `render`. It delegates motion to a bounded native physics controller; it checks physical state before the local computer effect. No new core motion API or external project write is introduced.

The next experiment should replace pose ground truth with camera-based observation and compare it against held-out simulator truth. After that, a mobile simulated body can navigate to an observation point before initiating a computer task. These are proposed experiments, not implemented capabilities. Notes remain supporting records of task intent, observations and verified outcomes.

## Limits

This is one XY pusher, one free block, a block-center zone predicate and one local software artifact. There is no autonomous learned planner, vision grounding, gripper, navigation, robot hardware or real-time operating-system guarantee. The target uses simulator coordinates. The observations are simulator state, not camera recognition. Footwork's file check proves expected byte persistence; the native state check supplies the simulated physical evidence.

Python handles task/state/receipt orchestration. MuJoCo supplies native C/C++ physics/rendering. Existing camera capture uses FFmpeg and Swift/Apple Vision. No new Rust route was justified: earlier workbench profiling found small-file hash and in-process artifact checks cheap relative to process/helper startup. Sustained video/sensor streams and bounded action dispatch are future profiling candidates; native physics and low-level robot controllers should remain outside the model loop.
