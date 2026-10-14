# SIM6: successive physical-computer experiments on one simulated bench

## Question

Can one persistent MuJoCo body support image-guided preparation, a separately executed computer measurement, contact-driven reset, and a subsequent job, including recovery from an unexpected block movement?

## Hypothesis

Separating persistent bench identity and state generation from job identity, and requiring fresh image-bound effects, permits successive jobs without reinitializing the body. A color-specific RGB host can reobserve after a diagnostic force disturbance and resume preparation instead of acting on stale placement evidence.

## Predictions

If true, two successive jobs retain one bench ID, monotonic native time and generations, each record one independently readable image measurement, and reset through native actuator/contact steps before the next job. A stale move or measurement following a disturbance refuses without its requested effect, then fresh RGB guidance completes and resets the disturbed job.

If false, reset requires state assignment/reinitialization, a disturbed job cannot recover within its bounded action budget, a stale packet authorizes measurement or motion, or job two loses the state/history of job one.

## Design

Add an isolated persistent bench under `tools/physical-workcell/`, reusing the pinned MuJoCo model, bounded native motion, PNG codec and color-specific RGB detector. Preserve the older episode/controller/application experiments. The host sees image packets and task intent, never private native pose guidance. Job phases separate preparation, measured result, resetting, and completed reset. A measurement subprocess computes the orange silhouette footprint and centroid from the exact image and records an idempotent job-bound SQLite result. This is a simulated optical measurement, not a calibrated physical instrument.

Reset routes the pusher around the block, pushes it back to the home region through contacts, then returns the pusher home. Initialization is allowed once; no reset may assign block pose or call `mj_resetData`. A bounded native external-force diagnostic produces an unexpected displacement, persists a new state generation, and is separately labeled intervention rather than planner motion.

Use private development runs and focused conformance tests. Freeze source before an independent public-interface qualification. Retain all attempts and cleanup evidence. No paid models, hardware, real camera access, cloud deployment or broad UI change.

## Primary metric

Number of successful complete job cycles in the preregistered sequence: ordinary job, disturbed job. Success requires exact measurement receipt, independently scored placement and home reset, continuous retained body identity/state, and no unsupported effect replay. Required result: 2/2 cycles and stale-evidence rejection in the disturbed cycle.

## Guardrails

One active job and exclusive bench writer; exact source, bench, job, generation and image identity; bounded motion/force/steps and action budget; historical measurement distinguished from current placement; unknown interrupted effects block new dispatch. Duplicate exact effect requests read history, conflicting IDs refuse. No implicit reset on restart or corruption. The independent scorer may inspect native state; the planner may not.

## Decision rule

Adopt only as an isolated experimental tool if the primary metric and guardrails hold. A recovery failure is retained and narrows the supported disturbance envelope. This qualification does not establish model-driven planning, arbitrary manipulation, hardware transfer, power-loss safety or production Footwork capability governance.

## Result

Frozen source `0091e5f832a3aef24ef73fdc9f1ee76bd64b7e46` passed 2/2 first-attempt cycles with one persistent bench identity and generations 0 to 29 to 70. A 0.1333 m axial disturbance invalidated the previous image; stale movement and measurement refused before fresh RGB guidance recovered placement. Separate native-state and read-only SQLite scoring verified both measurements and contact resets. Fourteen focused final-source conformance tests passed. See `results/reusable-bench-20261011/report.md` and `qualification.json` for evidence and limitations. Adopt only as the isolated experimental bench.
