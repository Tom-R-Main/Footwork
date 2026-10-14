# SIM2: AI image-guided physical and computer loop

The final public trial passed on frozen source `f96ac4a`. The current Codex session viewed each native RGB image, identified the orange block, supplied a bounded move proposal, inspected the resulting frame and chose subsequent corrections. A smaller final correction resolved visible placement error before the visually gated local computer action. The wrapper did not choose targets or call a model API.

## Final trial

`trial-v2.json` retains source/runtime/driver hashes, frame identities, exact agent proposals and concise feedback, with a reference and digest for the private raw public-CLI trajectory. The run is `tools/physical-workcell/output/image-demo-v2`; six inspected images span generations 0 through 5. Initialization's native pose output was withheld from the planner. The native oracle was separately read after image-guided planning/completion.

| Criterion | Observed |
|---|---|
| Image-guided actions | Five bounded moves, each chosen after viewing its source frame |
| Before final correction | RGB block center x=0.170833333 m; target center x=0.22 m; completion refused |
| Corrective decision | Smaller 0.05 m commanded-target increment, then a fresh image |
| Final visual placement | RGB center x=0.220833333 m, y=0; conservative center-in-zone check passed |
| Separate native oracle | Block x=0.220743231 m; native center-in-zone predicate passed |
| Modeled force envelope | Peak axis actuator force 1.501413009 N against a 4 N cap |
| Computer effect | One local staged work-order file, then separate public Footwork byte check passed |
| Wrong-object/stale requests | Refused without dispatch |
| Repeated completion/motion | Every run artifact byte unchanged; no second motion or order |
| Injected cached packet | Public view/apply refused extra oracle field; no field returned or effect intent created |

The image estimate and native oracle are observations in this scene, not a subpixel accuracy claim. Scale is 0.001666667 m per pixel. Completion checks the known block center with a 0.005 m margin; it does not certify an entire object placement or inspection procedure.

## Verification and version history

Prediction `fa41529` preceded implementation tests. Version 1 source `fbc9815` also completed an AI-viewed public loop and is preserved in `trial-v1.json`. Source review identified that cached packets could contain extra fields. The amendment and SIM2A prediction were committed in `36c44d1` before the strict-admission tests. Version 2 changed only packet field/scope validation; dynamics, camera, detector thresholds, target intent and motion settings stayed unchanged. The final trial used a deliberate new run and fresh AI decisions, not an upgraded version-1 receipt.

`verification.json` records 26 passing tests: 13 native renderer/image-route cases and 13 SIM1 native-engine regressions, plus Ruff. Image cases cover malformed/ambiguous/off-frame silhouettes, wrong boxes and motion bounds, premature completion, stale/tampered metadata, lost receipts/partial views, no replay, current software tamper without recreation, filtered planner outputs and evaluator-only oracle agreement. The independent extra-field check is in `packet-admission-negative.json`.

## Interface and limits

`image_guided.py view` returns a calibrated native RGB frame and task intent. An image-capable agent supplies a digest-bound proposal to `apply`. The wrapper verifies RGB evidence, exact identity and freshness; the unchanged native controller executes admitted motion. Completion additionally checks native physical state and saved software bytes. The code lives inside `tools/physical-workcell`; no production Footwork model or authority default changed.

This is an agent-driven simulated camera loop. There is no unattended model runner, real-camera acquisition, robot hardware, provider call or external project write. The RGB checker depends on known orange/blue silhouettes and camera calibration; general recognition, varied scenes/lighting, substantial occlusion and same-color impostors are unqualified. SIM2 guards apply to its own proposal route; the original SIM1 CLI remains available. Root/owner modification of all private state is outside the local receipt consistency contract.

The next useful experiment is variation in starting position, lighting and viewpoint with separately chosen task cases, followed by real-camera calibration. That extension is proposed, not implemented or qualified here.
