# SIM3: Repeatable visual work orders and a fresh host

Mode: source-frozen small diagnostic comparison, not a statistical model benchmark or robot qualification.

## Hypothesis

Separating RGB acquisition from interpretation and binding independently specified episodes will let a fresh image-capable host use the public workcell tools on varied work orders. Both a fresh host and a deterministic RGB controller can complete reachable ordinary jobs; recognition/calibration challenges remain visible and unresolved rather than falsely completed. The comparison can identify whether movement needs an AI planner in this bounded setting.

## Caller and scope

The job is: move the known part into the requested staging region, inspect placement, and record completion only when supported; otherwise explain the blockage. Keep the implementation under tools/physical-workcell. Add immutable case specifications, an episode lifecycle/evaluation CLI and a deterministic RGB baseline. Do not add a model API, second agent framework, robot semantics to the production capability service, persistent controller process, application fixture, Rerun dependency or new hardware.

The host is a fresh Codex agent context, with no parent conversation, previous trajectories, baseline code/results or native state. Supply public tool documentation, case paths/digests for opaque initialization, exact owned run/output paths and the task. It may inspect returned PNGs and pixel-based perception summaries, submit proposals and explain unresolved jobs. It must not inspect raw case configurations, native state/scene/source, evaluator data or earlier outputs. This is instruction-based separation on a shared filesystem, not an adversarial sandbox claim. The host owns planning; Footwork does not gain an internal model runner.

## Cases and freeze

The parent owns six qualification cases in tools/physical-workcell/cases/sim3-suite.json. Freeze them and their hashes before implementation measurements. The implementation worker must not inspect or tune against these cases; use separate development fixtures. Ordinary cases vary initial block x/y and requested zone. Challenge cases specify low illumination, a static render-only occluder or camera displacement. Initialization may set the case's initial state once; action must still move through native contact and must never teleport. Camera displacement invalidates the existing calibration and must not silently receive a corrected transform.

Base dynamics, detector thresholds and controller limits remain unchanged. Model/case/source/order/calibration/action bounds bind the episode. Different case or source bindings refuse reuse; no implicit reset. Valid acquired images persist even when perception is ambiguous/unavailable. Recognition status is separate from image availability; unsupported evidence still blocks action.

## Measurement

After scoped development/conformance, freeze source before initializing six fresh baseline runs and six fresh-host runs. Use the same ordered cases, observations and admitted actions. One fresh host processes the set; within-set learning is allowed and disclosed. Run each case once per participant for this adoption; retain setup failures, refusals, blocked outcomes and interventions. No corrective hints, repeated episodes or tuning to qualification failures. Capture each participant's per-episode elapsed time from initialization to declared finish, including its runtime/tool latency; elapsed values are descriptive, not a controlled performance benchmark.

Primary metric: completed ordinary physical-and-local-computer jobs per three attempted ordinary cases for each participant. Also report completed/all-six, unresolved, setup/driver failures, interventions and incorrect completion claims. Count every case. Independently score final native state and exact saved software artifact after the participant finishes. Capture the visual verdict durably before consulting native truth on each completion attempt, so an oracle-blocked visual false positive remains visible. Scene satisfaction alone does not create historical motion or software receipts.

The deterministic baseline uses only the same RGB-derived boxes/calibration/task intent and forward bounds; it receives no native pose feedback. It is a serious comparator, not a replayed target sequence. The fresh host's actual image views, decisions, finish declarations and explanations are retained separately from conformance tests.

## Checks and decision

Predictions: all valid rendered frames can be inspected despite detector failure; each case/source binding is enforced; native poses never enter host packets; completion verdicts precede native checks; ordinary jobs can finish through contact and a saved result; failed perception/calibration cannot complete; repeated/unknown effects do not replay. Independent scorer catches a declared completion without qualified physical/software evidence. Cold-host tool discovery/readiness and refusal comprehension are observed, not inferred from source.

Against: detector failure discards a valid frame; invalid calibration admits motion; author/native-state guidance chooses host targets; missing cases vanish from totals; simulator protection conceals visual false-positive verdicts; a satisfied current scene manufactures execution history; repeated effects or unsupported success claims.

Conformance must cover capture with unavailable/ambiguous perception, binding/tamper/freshness, changed initialization, invalid calibration, pre-oracle verdict ordering, budgets, false participant claims and existing SIM1/SIM2 regressions. Source/case settings changes start a new measured version; preserve earlier failures. Check notebook and redact committed results.

Decision: adopt only the bounded episode/evidence interface supported by the observed run. If the deterministic controller performs movement equally well, retain it for that role; do not infer AI value from successful movement alone. Independent controller recovery and real application handoff remain subsequent experiments.

## Result

Pending.
