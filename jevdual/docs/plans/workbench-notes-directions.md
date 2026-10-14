# Project-linked workbench notes: useful directions and language boundaries

The near-term goal is a physical observation that resolves a project question, changes a bounded work proposal, or supplies an acceptance check. Saving another transcript is insufficient evidence of utility. The first implementation binds a reviewed note to the user's selected Footwork project, its checkout revision and code references; it names a proposed next check without pretending that check ran.

## The local record contract

Keep separate fields for retained camera/approved-text evidence, caller interpretation, project identity/revision, proposed action/check, expected observation and actual outcome. A photo does not authorize an action; a saved packet does not establish its proposed physical effect. Keep local workbench artifacts private and checked through Footwork's exact-artifact command. An external task or project write needs an explicit resource binding and a real readback.

The first record uses the previously verified live paper note. It asks whether project-bound workbench evidence can produce an actionable next experiment, proposes a separately preregistered paper-region/word-review comparison and records that the comparison has not run. This exercises association and handoff, not automated experimentation.

## Grounded use cases

| Direction | Existing project asset | Useful outcome beyond capture | First bounded experiment |
| --- | --- | --- | --- |
| Footwork physical experiment notebook | Camera receipt, OCR provenance, exact file readback, engineering predictions | A physical setup/observation changes one explicit hypothesis or next test; source evidence survives agent handoff | Bind one reviewed frame to project/code revision, hypothesis and acceptance check, then separately run that check |
| ExecuFunction/Siftable work intake | Project/task graph and Taster's evidence/coverage contracts | A sketch/blocker becomes a reviewed work proposal with owner, dependency and observable acceptance; avoid duplicate or misrouted work | Draft one project-bound proposal locally, review identity/acceptance, then exercise a future task adapter with real task readback |
| Family-history evidence intake | Missionaries in China / Kuliang Main research; current task Upload and classify family-side materials | A photographed original supports or contradicts a particular timeline/identity claim, with location/source/privacy labels and unresolved readings | One family letter/photo -> source record + cited claim + corroboration question; Chinese OCR/translation is a separate route from the current en-US helper |
| Best-Edit field evidence | Newsroom/Civic reporting, document verification and PDF parser provenance | A public notice or field note is linked to the article claim it supports and a verification checklist | Photograph one non-sensitive notice; retain original, reviewed quote and source/date; propose a claim-verification check before editorial use |
| OBS MCP bench/demonstration record | Watched takes, chapter markers, capture preflight and media readback | Align observed actions and test results to recording phases so a failed experiment can be reproduced and inspected | One disposable setup with deliberate before/after capture and an explicit expected result; recordings remain opt-in and are checked against actual file metadata |
| Instrument/assembly acceptance | Local OpenHTF measurements/phases/attachments and AprilTag/OpenPnP reference patterns | Compare actual readings/setup steps to a written test specification and mark missing or unresolved evidence | Manually bind an instrument/object ID, unit, operator/calibration context and reviewed reading to one criterion; add direct sensor data before relying on it for actuation |

Live grounding on 2026-10-10: Codex app local project identities; Siftable project list and specific contexts. The family-history project currently has an open Upload and classify family-side materials task. Meta Wearables Integration is also an existing planning project describing hands-free/photo-to-note work and mobile-release prerequisites; it is a future capture surface, not proof of a deployed camera workflow. Duplicate ExecuFunction project names exist, so identifiers/namespaces must be explicit. Do not automatically map Siftable IDs from name similarity or Codex local project IDs.

Source code ground: ExecuFunction packages/taster/src/engine/coverageReads.ts records which changed ranges were read at the reviewed revision; packages/taster/src/contract/verdict.ts withholds complete when stages/evidence/reconciliation are incomplete. Best-Edit README defines Newsroom/Civic and document-verification workflows. pdf-parser README defines native extraction, OCR routing and typed provenance. OBS_MCP README defines watched takes, recording preflight and media verification. These are source/context observations, not new live qualification of those products.

[OpenHTF](https://github.com/google/openhtf) supplies a useful physical-test model: measurements with passing specifications plus free-form attachments. A workbench photo belongs beside a measurement and its criterion. [OpenCV marker pose estimation](https://docs.opencv.org/5.0/tutorials/objdetect/aruco_detection/aruco_detection.html) requires known marker size and camera calibration for metric pose. Detecting an object or tag in a picture alone does not establish voltage, force, depth, calibration or completed assembly.

## What to prioritize

1. Complete the Footwork record/handoff and readback route using one real reviewed source.
2. Improve paper-region/word review and measure correction effort against ordinary note entry; raw handwriting currently requires corrections.
3. Try an evidence-to-claim workflow with the family-history materials the user can actually access, or an OBS-linked before/after bench experiment. Select one question and one expected observation.
4. Add direct measurements and deterministic criteria before actuation. Keep model judgments advisory until their role is independently qualified.

## Languages and measured hot routes

Python standard library owns current workflow orchestration, schema validation, explicit project binding, local filesystem journals and CLI handoff. Swift calls native Apple Vision for OCR and camera-permission inspection; FFmpeg/ffprobe perform native media acquisition/decoding. Static review uses HTML/CSS. The new workbench package stays inside Footwork's tools directory.

Footwork already has a Rust/PyO3 boundary in jevdual/crates/jevdual-core. The observed local backend uses native paint_order, element_hashes and evidence_match; snapshot_lookup currently falls back to Python. This is a read-only runtime observation, not evidence that a port would help the camera route. New Rust ports require a Python twin, fixture equality and before/after measurements under jevdual/docs/rust-boundary.md.

Recorded route samples in jevdual/results/workbench-20261010/route-profile.json show approximately 1.3 ms to read/hash the 2.46 MB retained PNG, 0.18 ms for the direct exact-note check, 201 ms for a fresh public Footwork check process, 286 ms for public desk status and 452 ms for a Swift process plus real OCR on a three-line printed fixture with a warm module cache. Ranges and sample counts are retained. No sustained-video workload or Rust implementation was compared; human review was not timed.

Current optimization candidates are process startup and reuse/compilation of native helpers, where warranted. A Rust rewrite of small-note JSON/hash plumbing is unsupported by these measurements; hashlib SHA256 already runs in the native _hashlib extension. [Apple's accurate OCR mode](https://developer.apple.com/documentation/vision/vnrecognizetextrequest/recognitionlevel) prioritizes recognition accuracy and does more computation than fast mode; language choice alone does not accelerate that native engine.

Rust becomes a plausible boundary for sustained frame ingest, bounded latest-frame queues, high-rate image transforms/diffs, tracking, and sensor-stream fusion after those costs are measured. Prefer existing native implementations such as OpenCV/AprilTag for their algorithms rather than reimplementing them in Rust for naming consistency. On macOS, Swift is a direct route to AVFoundation/Vision. A future robot's low-level control loop needs its own hardware/runtime qualification; the conversational/project layer should supply bounded objectives rather than pretend to be a real-time controller.

## User steering · 2026-10-10 15:26
The user prioritizes physical applications mixed with computer actions and agents with bodies that can traverse environments. They report no robot hardware and chose simulation. Notes are supporting evidence, rather than the main product. Start a bounded MuJoCo workcell: read an explicit software work order, move a simulated part into an inspection zone, verify observed simulator state, then update the software order only when that predicate holds. Give an agent observe/act/status interfaces and generation-bound actions; do not claim simulated motion qualifies a real robot.

Toward general bodies, use body-specific calibrated controllers behind an explicit action/observation contract. [LeRobot Robot](https://huggingface.co/docs/lerobot/main/api/robots) exposes connect/get_observation/send_action/disconnect; [MuJoCo](https://mujoco.readthedocs.io/en/3.15.0/programming/simulation.html) supplies native simulated dynamics; [ROS2 actions](https://github.com/ros2/ros2_documentation/blob/rolling/source/ROS-Framework/interfaces/actions/Working-with-actions/Understanding-ROS2-Actions/Understanding-ROS2-Actions.rst) separate goals, feedback, results and cancellation. These provide seams for a future adapter, not an already universal Footwork body. Physical movement needs its own coordinate frame, limits, controller, state readback and cancellation qualification.
