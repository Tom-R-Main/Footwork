# A reusable simulated experiment bench

Prepare the block in the measurement region, run an optical measurement on the computer, return the block and pusher home, then accept another job. The bench retains one identity and a single continuous native integration state across jobs. Job identity changes; body identity does not.

This is an isolated Footwork experiment. It reuses the pinned MuJoCo model, native contact controller, PNG codec and color-specific RGB detector. It preserves the older single-order routes and uses a deterministic image-guided host. It makes no language-model calls and controls no hardware.

## Run two jobs

Use a new private directory below `tools/physical-workcell/output`. Run from the repository root with the existing pinned environment:

```sh
tools/physical-workcell/.venv/bin/python tools/physical-workcell/bench.py \
  --root tools/physical-workcell/output/my-bench/body init --diagnostic-enabled

tools/physical-workcell/.venv/bin/python tools/physical-workcell/bench_runner.py \
  --bench-dir tools/physical-workcell/output/my-bench/body \
  --journal-dir tools/physical-workcell/output/my-bench/job-1 --job-id job-1

tools/physical-workcell/.venv/bin/python tools/physical-workcell/bench_runner.py \
  --bench-dir tools/physical-workcell/output/my-bench/body \
  --journal-dir tools/physical-workcell/output/my-bench/job-2 --job-id job-2 --disturb

tools/physical-workcell/.venv/bin/python tools/physical-workcell/bench.py \
  --root tools/physical-workcell/output/my-bench/body status
```

Initialization only accepts an empty owned directory. It never clears an existing bench. Each job and journal needs a new identity. Omit `--diagnostic-enabled` and `--disturb` for ordinary use. The diagnostic flag authorizes a bounded simulated external force, separate from planner-controlled actuator motion.

The host positions the orange block near x=0.07 m, clears the blue pusher, and calls the measurement worker. It then routes the pusher around the block at y=0.135 m, pushes the block back near x=-0.12 m, and parks the pusher at x=-0.30 m, y=0. Reset uses contact dynamics; it never assigns block position or resets native data.

With `--disturb`, a simulated force moves the block after preparation. The host deliberately submits its old image for a move and a measurement. Both must refuse. It reads a new image, detects displacement, repositions the block, and resumes measurement and reset. Recovery supports one known block near y=0, reachable positions and recognizable silhouettes. Unsupported placements stop the host and retain the partial job.

## The computer action

`measurement.py` runs in a separate process. It reads the exact image bound to the job and computes the orange silhouette's pixel count, centroid and apparent footprint area using simulated camera calibration. It writes a SQLite row with bench ID, job ID, image and state digests, generation, native time and worker identity. The controller reads that row back independently and recomputes the image result before accepting it.

The result is a simulated optical measurement. It is not a physical mass, volume, material-quality or calibrated instrument measurement. A future adapter could replace this worker with an instrument or measurement application while retaining preparation and verification.

Read the retained results separately:

```sh
sqlite3 -readonly tools/physical-workcell/output/my-bench/body/measurements.sqlite \
  'SELECT job_id,generation,receipt_json FROM measurements ORDER BY job_id;'
```

## Control and evidence

Jobs progress through `prepare`, `measured`, `resetting`, and `completed`. Only one job may be active. Another cannot start until the block and pusher home positions and retained reset-contact steps have been verified. Measurement history describes an earlier measurement; current placement requires a new observation.

Each effect binds its operation ID to exact arguments. An identical repeat reads history; conflicting arguments refuse. Fresh effects require exact bench, job, phase, generation, state, image, calibration and source identity. Modified state, source, image or measurement evidence blocks further work. Interrupted dispatch stays unknown and blocks new effects; it is not automatically replayed or repaired.

The bench holds an exclusive writer lock during actions and the measurement subprocess. Each command restores the same integration state and saves its successor. Simulation time pauses between commands; this is not a continuously running hardware controller. Physical verification and computer persistence are separate steps, not an atomic physical/software transaction.

The host's `event-*.json` files retain observations, targets, action receipts, stale refusals, measurement reconciliation and reset. They contain no native pose guidance. Native state belongs to the separate qualification scorer. An unsuccessful run retains its partial journal and active or unknown job. Use a fresh diagnostic bench when testing changed source.

## Qualification

Preregistration: [SIM6](../../jevdual/docs/experiments/SIM6-reusable-bench.md).
Notebook: [reusable bench](../../jevdual/docs/notebook/2026-10-11-reusable-bench.md).

`qualify_bench.py --output PRIVATE_OUTPUT --source-commit COMMIT` verifies that every measured source file matches the named Git commit. It runs ordinary and disturbed jobs in separate host processes on one bench. Separate read-only SQLite/native scoring checks historical measurement placement, contact reset, retained state continuity and receipt identity. All attempts and failed output are retained. See the [results](../../jevdual/results/reusable-bench-20261011/report.md) for the frozen run and limits.

Local references: MuJoCo simulation/state documentation and integration-state APIs at commit `0696cdc85fc3741fdf71a97dec09467d19105e75` in `/Volumes/External SSD/referencerepos/mujoco`; LeRobot policy/client separation in `docs/source/async.mdx` at commit `b9cb121cb7d4e3e26ec5c906d08dda68d151ba52`. This loop uses MuJoCo directly and introduces no LeRobot dependency or network controller.
