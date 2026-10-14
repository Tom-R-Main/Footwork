# SIM7: an AI host controls the reusable simulated bench

## Question and hypothesis

Can the multimodal AI in this Codex session choose actions from native RGB images, complete two successive prepare-measure-reset jobs on one bench, and recover after an unexpected block displacement while the existing controller guards remain unchanged?

The hypothesis is that an external visual AI host can use a typed observation/action handoff instead of the deterministic RGB coordinate planner. It receives images, camera calibration, task regions, pusher dimensions and bounded action descriptions. It receives no detector coordinates or private native poses. Deterministic bench code continues to own effects and verification.

## Predictions

If true, both jobs complete with one measurement each and contact-driven reset, one bench identity and continuous integration state. A disturbance between the AI's observation/proposal and dispatch causes the original proposal to refuse. The AI inspects a new image, proposes corrective motion and completes the second job.

Against: the host needs the baseline coordinate planner or native poses; stale evidence dispatches; either job cannot complete within 64 motion actions; recovery requires a reset/teleport or controller guard changes; computer success is claimed without independent persistence readback.

## Design

Add a small source-bound external-agent session interface beside the existing bench. The agent observes a saved image, writes a typed proposal with a short action intent and exact observation digest, and dispatches it. Retain proposals, receipts, refusals and fresh observations. Never add an automatic coordinate planner, model-result success flag, provider API or fallback motion path. The existing Codex conversation supplies the actual AI; this is not an unattended API-backed service.

Freeze the interface source before the AI trial. Run job one with target x in [0.035, 0.105], y in [-0.025, 0.025]; job two with target x in [0.045, 0.115], the same y bounds. After the AI prepares a measurement proposal for job two, the diagnostic harness applies a bounded native external force before dispatch. The stale proposal must refuse. The AI then receives a fresh image and chooses recovery actions. A separate scorer may inspect native states and read-only SQLite only after both jobs finish or the attempt stops.

## Primary metric and decision

Primary metric: complete job cycles, required 2/2 on the first frozen trial attempt. Each requires independently verified measurement placement, exact saved result, and contact reset. Disturbance recovery and stale refusal are required guardrails. Retain a failed attempt; any subsequent repair is a separately preregistered version, not a hidden retry.

## Guardrails and limits

Keep bench.py, measurement.py, native controller and image gate source unchanged. One writer, typed finite actions, exact observation/source/job binding, retained intent before dispatch, no replay of unknown effects, and independent effect readback. No keys, paid provider calls, real cameras, hardware, production application changes or cloud deployment. The trial establishes this AI session's behavior, not a repeatability rate, a deployed policy service or general robotics.

## Result

Frozen `9a5d2f8bfac8088b13c63052887e0c0c2e9d5c7e` passed both first-attempt cycles with the Codex conversation AI authoring 29 proposals from presented images. A prepared measurement refused after a 0.13303 m native-force displacement; the AI observed the changed image, corrected placement, measured and reset. Post-trial native/SQLite scoring confirmed both cycles and exactly two saved measurements. Native guards remained unchanged; 29 focused checks passed. See `results/agent-visual-bench-20261011/report.md` and its structured evidence. Adopt the external visual-agent handoff as an isolated experimental interface, not an unattended policy service.
