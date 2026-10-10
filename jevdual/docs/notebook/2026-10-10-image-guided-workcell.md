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
