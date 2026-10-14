# SIM2: Image-guided block placement and conditional computer action

Mode: bounded simulated camera feedback with an AI agent, not hardware or general visual-model qualification.

## Hypothesis

An agent receiving only rendered RGB images, known camera calibration and work-order intent can locate the block, choose bounded pusher moves, observe a remaining placement error and correct it. A fresh image-derived placement check can gate the computer action without exposing simulator block coordinates to the planner.

## Predictions

Use the unchanged SIM1 dynamics/controller and add an isolated image-guided wrapper in tools/physical-workcell. A fixed top-down orthographic simulated camera provides a simple known pixel-to-table calibration. The current Codex agent views RGB images and supplies digest-bound structured proposals identifying the visible block box and a move or completion decision. No model API or credential setup is required for this agent-driven trial.

Every proposal binds the run, image SHA256, generation and exact token. A conservative pixel detector checks that the proposed box matches the visible orange block and derives its image-plane center; this is narrow color-specific visual support, not a general recognizer. Images with missing, ambiguous, off-frame or occluded target evidence refuse. The motion controller admits only bounded forward corrections with fresh evidence and existing SIM1 workspace/force/step limits. Completion requires the image-derived center to be inside the target zone with a conservative margin, then also requires SIM1's native-state predicate and Footwork's saved-byte check. Ground-truth block poses remain private to the simulator and a post-run evaluation record, absent from the agent-facing image packet and action feedback.

Predicts: at least one actual contact move leaves a visible residual error, followed by a fresh-image corrective move; final image-derived placement and separate native oracle agree. Early visual completion, stale/tampered images, wrong block boxes, no-contact motion, altered tokens and repeated/unknown actions cannot produce an unqualified successful computer result. Runs with ambiguous visual evidence stop rather than use hidden positions.

Against: native coordinates supplied to the planner or used to choose its correction; preselected targets masquerading as AI image decisions; a color/box check accepting blank or mismatched images; completion without fresh visual evidence; lost or repeated proposal causing another effect; failure to demonstrate correction or agreement with the separate native oracle.

## Design and checks

Prediction is committed before source tests. Parent owns preregistration, notebook, source freeze and independent public AI-driven trial; project worker owns image wrapper, schema, conformance tests and README. Keep SIM1 source/model unchanged. The wrapper renders a separate calibrated view from retained native integration state, without changing physics. Retain image/request/decision/receipt hashes under private ignored output, single owner per workcell. No real camera acquisition, physical actuation, provider call or external project write.

Primary metric: binary demonstration of image-located contact movement, observed residual error, image-informed correction, final fresh visual check and exactly one separately checked local work-order result. Verify public interface across fresh processes and scoped negative/failure paths. Freeze implementation/camera/detector/schema/settings before the measured run. No claims of visual-model accuracy from one agent-led trial; the detector uses known object colors and a known camera.

Decision: adopt only as an experimental image-driven body interface if the complete loop and refusal boundaries pass. Keep perception/model intent, controller effects, image verification, native oracle and saved software evidence separate. On failure preserve the evidence and append a dated amendment before a new measured source version.

## Result

Held for the bounded agent-driven simulated route. The final version at `f96ac4a` passed a fresh parent trial: six viewed RGB frames, five image-bound moves, a visually short placement, a smaller corrective move and fresh visual completion. The separate post-planning native oracle agreed with the visual placement, and an independent public Footwork check verified the local work-order file. Wrong-object/stale/short-completion and injected packet cases refused; repeated commands left all run artifacts unchanged. The combined scoped suite passed 26 actual-engine/renderer tests. See `results/image-guided-workcell-20261010/report.md`, versioned trial summaries and verification.

This establishes one known-color, calibrated simulation loop driven by the current AI session. It does not establish an unattended model runner, general recognition accuracy, real-camera calibration or hardware transfer. Version 1 is preserved separately; the dated amendment below records the source hardening before the final trial.

## Amendment · 2026-10-10 15:54

Version 1 at `fbc9815` completed the parent AI image-guided trial: five bounded image decisions, residual placement error at generation 4, a smaller correction at generation 5, fresh visual completion and separate native/file checks. Preserve it as `results/image-guided-workcell-20261010/trial-v1.json`.

Source review identified an additional cached-packet boundary: the reader validates known fields but returns the original dictionary, so an injected extra field could enter planner evidence. Before adopting version 2, reject unknown packet fields and any changed perception-scope marker. Add forged-oracle-field and altered-scope conformance cases; commit the amendment before these tests. Keep dynamics, camera, detector thresholds, control settings and target intent unchanged. Freeze the revised source and repeat the parent image-driven public trial on a new run; earlier run evidence remains version 1 and is not silently upgraded. This is schema hardening, not tuning from a failed placement.
