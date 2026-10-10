# Physical movement coupled to a computer work order

Give an agent a bounded body in native MuJoCo: observe a tabletop block, move an XY pusher,
then stage a local software work-order result only when the observed block center reaches
the order's inspection zone. Footwork independently checks the saved result bytes.

Every observation, action, render and software result is labeled `mujoco_simulation`.
There is no real robot, camera acquisition, learned policy, visual-recognition claim,
cloud call or external task creation. State readback comes directly from the native
simulator. This package is an isolated experiment, rather than a production Footwork adapter.

For RGB-driven agent control, use the separate [image-guided route](IMAGE_GUIDED.md). It keeps
native poses out of planner packets and adds a fresh visual gate before computer staging.
The base commands below retain their original native-state behavior.
For independently specified cases, readiness checks, a deterministic RGB baseline and
separate participant declarations and scoring, use the [episode interface](EPISODES.md).
Its [measured comparison](../../jevdual/results/repeatable-work-orders-20261010/report.md)
covers varied ordinary jobs and lighting, occlusion and calibration challenges.
The [independent controller](CONTROLLER.md) adds a separately running owner for an initialized
episode. Clients can submit, disconnect, read status and request cancellation; retained
execution history stays separate from current state and stop evidence.

## One work order

The package uses pinned `mujoco==3.15.0` in its own ignored `.venv`. The existing Footwork
environment supplies the public file checker. Run commands from the repository root.

Create a private input JSON with this exact schema:

```json
{
  "version": 1,
  "order_id": "inspect-block-001",
  "project": {
    "namespace": "codex_app",
    "project_id": "abe2a667-dedc-4f3f-9863-62f3d80188bd"
  },
  "part_id": "block",
  "target_zone": {
    "x_min": 0.18,
    "x_max": 0.26,
    "y_min": -0.08,
    "y_max": 0.08
  }
}
```

The order's namespace/ID are explicit caller metadata, not authenticated project authority.
Only one known block and a bounded tabletop rectangle are supported. Obtain the input's
exact digest with `shasum -a 256`, then initialize:

```sh
tools/physical-workcell/.venv/bin/python tools/physical-workcell/workcell.py init \
  --work-order tools/physical-workcell/output/inputs/order.json \
  --work-order-sha256 REPLACE_WITH_THE_INPUT_DIGEST \
  --run-dir tools/physical-workcell/output/inspection-001
```

Initialization creates the native model/data and settles the block under gravity. It
records model, implementation, controller and runtime fingerprints, the input digest,
and generation zero. Repeating an identical initialization reads retained state; it
never resets the block. Unreceipted files or a changed binding refuse initialization.

## Observe, act, observe

```sh
tools/physical-workcell/.venv/bin/python tools/physical-workcell/workcell.py observe \
  --run-dir tools/physical-workcell/output/inspection-001

tools/physical-workcell/.venv/bin/python tools/physical-workcell/workcell.py act \
  --run-dir tools/physical-workcell/output/inspection-001 \
  --token push-001 --expected-generation 0 --target-x 0.15 --target-y 0
```

Coordinates are meters in `sim_world`. The free block begins at model x=-0.12 and the
pusher at x=-0.30. The example target is the pusher position, not the desired block pose.
The native controller ramps actuator targets, and modeled contact moves the block.
No action assigns the block position or teleports it.

The fixed controller settings are:

| Setting | Value |
|---|---|
| Native step | 0.002 s |
| Commanded target speed | 0.15 m/s |
| Settling interval | 1 s |
| Native actuator force bound | 4 N per axis |
| Admitted world targets | x from -0.32 to 0.18; y from -0.15 to 0.15 |
| Operation budget | 3000 native steps and 10 s wall time |

These are prototype settings. The target-speed envelope is distinct from actual body
velocity, and modeled joint limits are distinct from hardware interlocks. The loop makes
no operating-system real-time guarantee.

Observation reports generation, state digest, simulation time, block/pusher positions,
the target rectangle and physical predicate. Motion receipts retain native step/contact
samples and maximum actuator force, separately from the predicate. A command that executes
without touching the block can be an executed action while the work order remains unmet.

The physical predicate is deliberately narrow: the known block center is inside the
rectangle, with z between 0.02 and 0.08 m above the table. It does not establish that the
whole block is inside, that an inspection occurred, or that an image recognized the object.

## Conditional computer action

```sh
tools/physical-workcell/.venv/bin/python tools/physical-workcell/workcell.py complete \
  --run-dir tools/physical-workcell/output/inspection-001 --token stage-001
```

Before the predicate holds, completion refuses and creates no software result. When the
current verified simulator state qualifies, it records intent and creates one local
`order.json` with state `staged`. That file retains the physical readback, work-order
digest, simulator generation/state digest and fingerprints.

The tool then calls the existing public `footwork check-artifact` against digest-bound
`expected-order.json`. Its result establishes saved-byte equality; native state readback
establishes the simulated physical condition. An actuator command alone establishes neither.
Once staged, the work order admits no further motion or another completion operation.

## Persistence and unknown outcomes

Each generation saves `mjSTATE_INTEGRATION` through native `mj_getState`; a fresh process
restores it through `mj_setState`. The finite JSON vector includes the native integration
state rather than a pickle or just the block pose. Loading refuses altered/missing state,
model, input or fingerprints. It never falls back to an initial scene.

Tokens bind exact operation arguments. Repeating a motion token returns its historical
receipt and a current observation without stepping. Changed arguments, stale generations,
nonfinite coordinates and out-of-envelope targets refuse before intent/dispatch.

Intent is persisted before movement or computer publication. Missing receipts, interrupted
state writes or partial software output stay unknown and block motion/completion. They
are never replayed. If the retained state predates an unresolved operation, its authority
is labeled `retained_unresolved_operation`; `physical_condition_verified` is false even
when the retained coordinates happen to lie in the zone.

A saved order later missing or changed makes current software evidence unknown while
preserving historical staging. Repeating completion does not recreate or overwrite it.
There is no reset command. A deliberate new run is a new simulation, not resolution of
an earlier unknown operation. Power-loss recovery is not qualified.

## Native simulator images

```sh
tools/physical-workcell/.venv/bin/python tools/physical-workcell/workcell.py render \
  --run-dir tools/physical-workcell/output/inspection-001
```

Native MuJoCo Renderer produces a 640 by 360 PNG of the retained current state, labeled as
simulation in the returned metadata. Render before and after motion for separate generations.
The inspection rectangle is a non-contact visual marker derived from the bound order.
Render files are create-only; repeated rendering refuses overwrite. If native GL is
unavailable, the command reports that gap and produces no substitute image.

An image is a simulator view, rather than camera evidence or independent perception.
Unresolved state cannot supply a current render.

## Private files and checks

Runs remain under ignored `tools/physical-workcell/output/`, with owned 0700 directories
and 0600 files. A nonblocking lock permits one owner per run. Inputs, state, model, operation
records, images and software results stay private. Retained files are bounded to 1 MiB.

Exit code 0 means a completed command with known retained state. Exit code 2 means refusal
or an unknown operation/current result. Read operation phase and observation authority as
well as the exit code. Simulation time is integrated native time, not wall-clock exposure time.

```sh
tools/physical-workcell/.venv/bin/python -m unittest discover \
  -s tools/physical-workcell -p 'test_*.py' -v
jevdual/.venv/bin/ruff check tools/physical-workcell
```

Tests use the actual pinned engine, fresh public CLI processes and the real Footwork file
checker. Fault injection covers missing receipts, interrupted state publication and artifact
tamper. The measured demonstration and before/after renders belong to a separate frozen run.
Transfer to real hardware, vision, ROS or LeRobot remains unimplemented.

Preregistration: `jevdual/docs/experiments/SIM1-physical-computer-workcell.md`.
Notebook: `jevdual/docs/notebook/2026-10-10-physical-workcell.md`.
