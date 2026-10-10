# Image-guided physical and computer workcell

## SIM2 · prediction · 2026-10-10 15:41
Hypothesis: an AI agent using rendered RGB views and known camera calibration can locate the simulated block, move it, observe residual placement error and correct it before a visually gated local computer action.
Test: unchanged SIM1 dynamics with an isolated image wrapper, fresh generation/digest-bound proposals, actual RGB box/pixel checks, bounded native contact moves, at least one image-informed correction, final image placement and separate native oracle, exact saved result readback. Freeze implementation before parent-run public trial; exercise visual/stale/tamper/no-replay counterexamples.
Predicts: the planner needs no native block coordinates; final visual placement agrees with oracle; only fresh visual plus native physical evidence allows the computer result. Bad/ambiguous/stale evidence and unknown effects remain refused or unresolved.
Against: hidden-state-driven planning, prerecorded moves reported as AI visual decisions, wrong/blank image accepted, completion without fresh visual evidence, repeated effect or no corrective movement demonstrated.
Refs: docs/experiments/SIM2-image-guided-workcell.md; results/physical-workcell-20261010/report.md; /Volumes/External SSD/referencerepos/mujoco/doc/XMLreference.rst

## SIM2-U1 · update · 2026-10-10 15:54
Observed: parent AI trial on fbc9815 used six viewed frames and five bounded moves, observed a residual error near the target boundary and selected a smaller correction. Fresh visual completion passed with a separately observed native oracle and public Footwork file check. Source review also found that a cached packet dictionary could contain unvalidated extra fields.
Inferred: the clean generated image/control loop works, but schema hardening is needed before treating cached planner evidence as fully constrained.
Next: SIM2A; preserve version 1, harden packet admission and repeat the image-guided trial on version 2.
Refs: results/image-guided-workcell-20261010/trial-v1.json; docs/experiments/SIM2-image-guided-workcell.md

## SIM2A · prediction · 2026-10-10 15:54
Hypothesis: exact packet field admission and fixed perception-scope validation can prevent injected native-oracle fields reaching the planner while preserving the existing image-guided workflow.
Test: reject forged extra fields and altered perception scope on actual retained camera packets; freeze revised source, then repeat the AI RGB placement/correction/computer loop on a new run with unchanged dynamics, calibration, detector and motion settings.
Predicts: mutated packets refuse without exposing injected fields; valid generated packets still support fresh visual decisions, correction and a separately verified local work order.
Against: forged oracle fields returned, mutated packets authorize dispatch, or valid image-guided placement cannot complete after hardening.
Refs: docs/experiments/SIM2-image-guided-workcell.md; tools/physical-workcell/image_guided.py

## SIM2-U2 · update · 2026-10-10 15:58
Resolves: SIM2 = held
Observed: the parent AI session viewed six native RGB frames on frozen version f96ac4a and supplied five bounded moves. The frame at generation 4 showed residual horizontal error; its completion was refused, then a smaller image-informed correction produced a fresh accepted visual placement. Post-planning native observation and an independent public Footwork saved-byte check passed. Wrong-object/stale-generation requests refused; repeated motion/completion left all run artifact bytes unchanged.
Inferred: the agent-facing RGB/control/local-computer workflow supports feedback correction in this known scene without native poses in the planner interface. A single trial does not measure general visual-model quality.
Next: close SIM2; retain camera/control separation for future scene variation or real-camera calibration experiments.
Refs: results/image-guided-workcell-20261010/trial-v2.json; results/image-guided-workcell-20261010/report.md

## SIM2A-U1 · update · 2026-10-10 15:58
Resolves: SIM2A = held
Observed: the strict packet admission at f96ac4a rejected a forged extra-oracle field through both public view and apply, without returning the injected field or creating effect intents. Scoped conformance also rejected changed perception scope. The fresh parent RGB placement/correction/computer run passed after hardening; dynamics, camera/detector and motion settings were unchanged.
Inferred: exact cached-packet admission closes the reviewed planner-output gap for this local workflow.
Next: close the package.
Refs: results/image-guided-workcell-20261010/packet-admission-negative.json; results/image-guided-workcell-20261010/verification.json

## SIM2-S1 · summary · 2026-10-10 15:58
Established: actual AI-viewed images and structured decisions drove bounded contact motion, residual-error correction and fresh visual completion, followed by separate native and software verification. Versioned trial evidence is preserved; final scoped conformance and prior SIM1 regressions passed.
Uncertain: varied lighting/object identity/camera geometry, general vision accuracy, hardware transfer, global access control and unattended model orchestration remain unqualified. The RGB checker is specific to known colored silhouettes; the base SIM1 CLI remains an unguided route.
Decision: retain image_guided.py as an experimental Footwork body interface, with agent intent, native controller, RGB placement, native oracle and software persistence kept distinct. Do not change production model authority or add Rust without workload evidence.
Refs: results/image-guided-workcell-20261010/report.md; tools/physical-workcell/IMAGE_GUIDED.md
