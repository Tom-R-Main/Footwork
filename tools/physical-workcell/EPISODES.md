# Repeatable visual work orders (SIM3)

This isolated simulation package exposes a cold-host episode lifecycle around the existing
image-guided route. Footwork's core capability service is unchanged. Images come from the pinned
MuJoCo renderer; they are neither a real camera feed nor generated illustrations.

The parent supplies one exact private output directory and a case path/SHA256 for each job.
Treat case files as opaque initialization inputs. A fresh host reads this document and the
public [proposal schema](proposal.schema.json), views returned RGB PNGs, and uses public packets
and receipts. It does not read case configurations, simulator state/model/source, the evaluator,
previous trajectories, baseline code/results or another participant's output. This is a role
boundary on a shared filesystem, not an adversarial filesystem sandbox.

## Readiness and initialization

Run from the repository root using the existing pinned environment:

```sh
tools/physical-workcell/.venv/bin/python tools/physical-workcell/episode_runner.py doctor

tools/physical-workcell/.venv/bin/python tools/physical-workcell/episode_runner.py init \
  --case-file ABSOLUTE_CASE_PATH --case-sha256 EXACT_CASE_SHA256 \
  --run-dir ABSOLUTE_OWNED_RUN_DIRECTORY
```

`doctor` reports native dependency/version, in-memory renderer and Footwork artifact-checker
readiness. It performs no motion, episode initialization, persisted-state update or real-camera
acquisition. Its success is not episode success.

Initialization records the episode identity, source/case/run/participant bindings and start
time before setup. A failed setup stays counted and cannot silently retry. Repeating the same
successful initialization returns its existing state; a different case, digest, source or
participant refuses reuse. There is no reset operation. Output lives in an owned, private
subdirectory of `tools/physical-workcell/output`; one owner lock covers each operation.

The public initialization response contains task intent, opaque case/state identities,
generation and calibration validity. It contains no initial native poses or scene perturbations.

## Inspect and act

```sh
tools/physical-workcell/.venv/bin/python tools/physical-workcell/image_guided.py view \
  --run-dir ABSOLUTE_OWNED_RUN_DIRECTORY
```

Inspect the returned `image_path` PNG. The packet provides its exact SHA256, state generation,
task region, camera calibration, pixel-derived perception and remaining dispatch budget. Pixel
boxes are `[xmin,ymin,xmax,ymax]` with exclusive maximum edges. Calibration states whether the
pixel-to-world transform is valid; valid calibration permits using its meters-per-pixel scale,
image center and axis directions. Perception has a separate `state`: `recognized`, `ambiguous`
or `unavailable`. An acquired image remains inspectable when recognition or calibration fails.
Unsupported recognition/calibration cannot authorize a move or completion.

Use the current image and public task region to choose a proposal. A move contains exactly
`version`, `run_dir`, `generation`, `image_sha256`, `token`, `block_box`, `decision` and `target`.
`version` is 1, `decision` is `move`, and `target` has only `x` and `y`. A completion contains the
same fields except `target`, with `decision` set to `complete`. Use the exact schema to check
types and bounds. Tokens identify intended effects and must be new for a new proposal.

Save each proposal privately, compute its exact digest, then submit:

```sh
shasum -a 256 ABSOLUTE_PROPOSAL_FILE

tools/physical-workcell/.venv/bin/python tools/physical-workcell/image_guided.py apply \
  --run-dir ABSOLUTE_OWNED_RUN_DIRECTORY \
  --proposal-file ABSOLUTE_PROPOSAL_FILE --proposal-sha256 EXACT_PROPOSAL_SHA256
```

The independent RGB gate checks the supplied block box. Forward motion is bounded to 0.005–0.12 m
from the RGB pusher estimate, within the existing controller workspace/force/step limits.
Target `|y|` is at most 0.01 m and observed pusher `|y|` at most 0.02 m. Leave room for pixel
quantization near bounds. Completion needs the RGB block center inside the task rectangle with
a 0.005 m margin, then a separate private native predicate and saved-byte checker. Public feedback
contains historical receipts and current software checks, never native poses.

An executed move requires a fresh view before the next decision. Refused unsupported proposals
cause no effect. Unknown outcomes require explanation and review; they cannot replay. Repeated
exact proposals return history without repeating movement or computer publication. All admitted
native effect intents, including completion, consume the case budget; views and pre-dispatch
refusals do not. Reserve one remaining dispatch for completion.

## Declare the episode's outcome

After a supported staged receipt, or when blocked, save a nonempty UTF-8 explanation and finish:

```sh
shasum -a 256 ABSOLUTE_EXPLANATION_FILE

tools/physical-workcell/.venv/bin/python tools/physical-workcell/episode_runner.py finish \
  --run-dir ABSOLUTE_OWNED_RUN_DIRECTORY \
  --outcome completed --explanation ABSOLUTE_EXPLANATION_FILE \
  --explanation-sha256 EXACT_EXPLANATION_SHA256 --interventions 0
```

Choose `completed`, `unresolved` or `failed` and explain the evidence or blockage. Declare the
actual intervention count; omitting `--interventions` leaves it unknown. `finish` records the
end time and exact retained explanation. It echoes a participant declaration and receipt history;
it performs no motion, computer staging or native-oracle scoring. Identical finish calls keep
the original end time and return unchanged; conflicting declarations refuse.

## Parent-only evaluation and deterministic comparator

The parent evaluates each attempted episode after the participant finishes:

```sh
tools/physical-workcell/.venv/bin/python tools/physical-workcell/episode_runner.py evaluate \
  --run-dir ABSOLUTE_OWNED_RUN_DIRECTORY
```

The evaluator reads current native state, the current exact saved software artifact, historical
native/image receipts and durable pre-oracle visual completion verdicts. It restores each verdict's
SHA-bound historical integration vector in memory, so later placement cannot hide an earlier
visual false positive. Evaluation does not update the manifest, states, receipts or explanation.
Its native truth is parent-only evidence and must not be fed back into participant planning.

Elapsed time is initialization to declared finish and includes participant/tool latency; an
unfinished episode has no elapsed finish value. Counts include attempted/setup-failed episodes,
admitted actions, genuine motion/contact history, software staging, unresolved/failed declarations,
declared interventions and incorrect completion claims. A satisfactory scene alone cannot invent
motion or staging history. A job already placed at initialization can qualify with zero motion
only through real fresh visual completion and native/software staging.

The parent's deterministic comparator uses `baseline` with the same case/digest/run arguments
as `init`. It derives every forward target from current RGB block/pusher locations and task intent,
observes the same action/completion gates and budget, and calls the same public finish declaration.
It has no native pose guidance, stored target trajectory or provider/model call. Its successes
are deterministic controller results, not AI trials. Each participant gets its own fresh output
directory; failures remain part of the frozen comparison.

Development conformance uses separate private case values, actual native rendering/contact,
finish/binding/false-claim checks, and read-only historical verdict scoring:

```sh
tools/physical-workcell/.venv/bin/python -m unittest discover \
  -s tools/physical-workcell -p 'test_episode_runner.py' -v
jevdual/.venv/bin/ruff check tools/physical-workcell/episode_runner.py \
  tools/physical-workcell/test_episode_runner.py
```

Preregistration: `jevdual/docs/experiments/SIM3-repeatable-visual-work-orders.md`.
Notebook: `jevdual/docs/notebook/2026-10-10-repeatable-visual-work-orders.md`.
