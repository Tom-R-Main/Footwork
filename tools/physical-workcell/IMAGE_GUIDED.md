# Image-guided simulated workcell

The SIM2 wrapper gives the planner a native rendered RGB image, a known camera calibration,
and work-order intent. An agent inspects each image and supplies a structured move or completion
proposal. The wrapper validates visible evidence and admits a bounded action through unchanged
SIM1 dynamics. It does not choose the planner's target or call a model API.

Native block/pusher coordinates and physics-oracle predicates stay out of planner packets and
action feedback. The final computer action requires fresh RGB evidence, a separate private
native-state condition, and Footwork's independent saved-byte check.

This is an experimental route in the existing isolated package. The base SIM1 CLI remains
available as an unguided route. These guards apply to SIM2 `apply`; they are not global access
control, a hardware interlock, or protection against an owner forging all private files.

## Inspect a fresh image

Initialize a new workcell with the [SIM1 instructions](README.md), or use an existing verified
run with unchanged source fingerprints. Then, from the repository root:

```sh
tools/physical-workcell/.venv/bin/python tools/physical-workcell/image_guided.py view \
  --run-dir tools/physical-workcell/output/image-demo
```

The returned packet names the private PNG and its SHA256, generation/state digest, calibration,
task intent and proposal schema. Use an image-viewing tool to inspect that PNG. It is native
MuJoCo rendering, labeled `mujoco_simulation`, rather than a real camera image or AI-generated picture.

The top-down camera is orthographic at world position `(0,0,1)`, with vertical span 0.6 m and
640 by 360 RGB pixels. Image right is positive world x; image down is negative world y.
The image center represents `(0,0)` on the table. Scale is `0.6/360` meters per pixel. This
calibration belongs to the simulated camera and supplies no real-camera calibration claim.

Images and their receipts are generation-bound. A repeated `view` validates and returns the
same image; it does not rerender. Pending receipts, unreceipted images or altered image/task/run/
scope metadata refuse promotion or overwrite. Unknown simulator or proposal outcomes block new views.

## Supply a proposal

The exact schema is [proposal.schema.json](proposal.schema.json). A move has these fields:

```json
{
  "version": 1,
  "run_dir": "/absolute/path/to/the/existing/run",
  "generation": 0,
  "image_sha256": "REPLACE_WITH_64_LOWERCASE_HEX_CHARACTERS",
  "token": "move-001",
  "block_box": [227, 159, 269, 201],
  "decision": "move",
  "target": {"x": -0.20, "y": 0}
}
```

That box and target illustrate the initial model, rather than a built-in plan. Replace them
from the actual fresh image. The run path is canonical and absolute; image digest/generation
come from the packet. Pixel boxes use `[xmin,ymin,xmax,ymax]` with exclusive maximum edges.
The token identifies one intended effect. Extra fields are refused.

Save the proposal privately and obtain its exact digest with `shasum -a 256`:

```sh
tools/physical-workcell/.venv/bin/python tools/physical-workcell/image_guided.py apply \
  --run-dir tools/physical-workcell/output/image-demo \
  --proposal-file tools/physical-workcell/output/inputs/move-001.json \
  --proposal-sha256 REPLACE_WITH_THE_PROPOSAL_FILE_DIGEST
```

The independent RGB check requires one orange block and one blue pusher. Their silhouettes
must have plausible dimensions, fill and full-frame visibility. The nominal block footprint
is 42 by 42 pixels; the pusher footprint is 24 by 84. Settings allow 8 pixels of size variation,
require at least 80 percent fill, and exclude boxes within 2 pixels of an image edge. The agent's
proposed box must match the detected block edges within 8 pixels.

Color checks are fixed for this model: orange requires red at least 80, red at least 1.3 times
green, and green at least 1.35 times blue. Blue requires blue at least 80, blue at least 1.15
times green, and green at least 1.3 times red. Significant connected regions require 20 pixels.
These are scope/settings declarations, not measured recognition accuracy. Small occlusions
within tolerances, same-colored impostors, changed lighting or general object identity are
not qualified. Missing, multiple, heavily occluded, off-frame or implausible evidence refuses.

Move targets are absolute pusher world coordinates. The wrapper derives its current pusher
estimate solely from RGB. It admits forward x increments from 0.005 to 0.12 m, with target
`|y| <= 0.01 m`, observed pusher `|y| <= 0.02 m`, and existing SIM1 workspace/force/step limits.
Leave room below the maximum for pixel quantization. Reverse, oversized or stale-image moves
refuse before dispatch. The native controller still owns low-level motion/contact dynamics.

After an executed move, request another fresh view. The feedback contains opaque state hashes,
generation, command and contact statistics, plus a historical RGB check. It does not expose
native poses or use the physics oracle to pick the next target.

## Complete from fresh visual evidence

A completion proposal has the same identity/image/box fields, with `"decision": "complete"`
and no `target`. The freshly segmented block center must lie inside the task rectangle with
a 0.005 m margin. A visually short placement refuses completion, allowing another fresh-image
move proposal with a new token.

After the visual gate, SIM1 privately checks its own native-state predicate and stages one
local computer order. Footwork's public `check-artifact` independently checks its saved bytes.
RGB placement, native state, issued command and software persistence remain separate evidence.

The wrapper reports historical operation/visual/software evidence explicitly. A repeated
completion also rechecks the current software file. Missing/tampered current output returns
unknown while retaining historical staging; it never recreates or overwrites the result.
Repeated move proposals return their receipt without stepping.

## Replay, source changes and privacy

One base-run lock covers viewing and proposal admission. Proposal intent is durable before
the effect; partial requests, lost receipts and unknown base/wrapper outcomes never replay.
Tokens bind the exact proposal bytes and arguments, source image, generation and frozen route.
Retained wrapper receipts must match their token/file, original request and native operation.

Wrapper/schema/settings/base fingerprints are bound to the run. A changed implementation
refuses existing bindings rather than silently upgrading them. Start a deliberate new run
for a newly frozen version, preserving earlier receipts/results as earlier-version evidence.

Private `vision-binding.json`, PNGs, view receipts, request bytes and proposal receipts stay
under the existing ignored run directory. The bounded PNG decoder validates CRCs, dimensions,
RGB format and decompression limits; it accepts the native encoder's filter-zero format.
No real camera, microphone, provider credential, external repository or cloud write is used.

## Conformance and the AI trial

```sh
tools/physical-workcell/.venv/bin/python -m unittest discover \
  -s tools/physical-workcell -p 'test_image_guided.py' -v
jevdual/.venv/bin/ruff check tools/physical-workcell/image_guided.py \
  tools/physical-workcell/test_image_guided.py
```

Conformance uses the actual renderer/engine and a deterministic RGB-based test harness.
Its targets are not presented as AI decisions. It checks malformed visual evidence,
stale/tampered packets, token conflicts, partial views, unknown outcomes, no replay, software
tamper, filtered public outputs and final evaluator-only native agreement.

The independent AI trial requires the current agent to actually view successive PNGs,
submit its own proposals, observe a contact move leaving residual error and choose a correction.
One successful trial does not establish general visual-model accuracy or transfer to hardware.

Preregistration: `jevdual/docs/experiments/SIM2-image-guided-workcell.md`.
Notebook: `jevdual/docs/notebook/2026-10-10-image-guided-workcell.md`.
