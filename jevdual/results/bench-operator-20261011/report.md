# Footwork Bench: unattended visual workcell and local product

The final source-frozen qualification passed two queued image-guided inspection cycles on one persistent simulated bench. A real independently running Codex policy chose each move, measurement and reset action. Native state and read-only SQLite verified both cycles separately; the browser retained their results after reload and a server restart.

## What the product does

Open the local bench, add a named inspection and select a region. The AI observes the camera image, moves the pusher, corrects placement, triggers a separately executed optical measurement and returns both bodies home by contact. The browser exposes the queue, most recent camera capture, model planning, intent, measurement, activity and pause/resume. Repeat creates a new job. Simulation remains explicit throughout.

Runbook: [OPERATOR.md](../../../tools/physical-workcell/OPERATOR.md). Implementation stays in Footwork's existing physical-workcell package: stdlib Python, plain browser HTML/CSS/JavaScript and pinned MuJoCo 3.15.0. Existing native guard files are unchanged.

## Final qualification

Source freeze: `1415f594ccc91dbc6f7856ba9b2ab0252d45cfdb`. Version 2, attempt 1. Private run: `tools/physical-workcell/output/sim8-qualified-20261011-v2/`.

Bench identity: `3e46ab9264d148db8f026373a79f0078`. Native generations continued 0 → 10 → 24; simulation time continued 1.000 → 21.414 → 47.084 seconds. No body reinitialization or pose assignment reset occurred.

| Job | Reserved model calls | Native moves | Measurement generation | Reset generation | Apparent area, mm² |
|---|---:|---:|---:|---:|---:|
| Baseline inspection | 14 | 10 | 2 | 10 | 4794.4 |
| Recovery inspection | 17 | 13 | 16 | 24 | 4802.8 |

The disturbance moved the block **5.61 cm** out of its target region after the first measurement proposal was saved. The immutable proposal/challenge/result chain and native force receipt bind that decision to the older generation. The stale measurement was refused without a native measurement operation; the next executed model move used the exact post-force image. The AI recovered and later measured successfully. The scorer independently checks force, displacement, freshness, SQLite rows, native placement, contact reset and continuous body/time identity.

There were 31 reserved CLI requests: 30 typed decisions and one cancelled request. Twenty-nine decisions executed, one stale measurement was refused, and no outcome was unknown. Every launched model process exited and was reaped. Inputs contained exact matching PNG bytes and bounded task/history metadata; detector locations and native poses were absent.

Pause during actual inference left generation zero and created no proposal or dispatch. Resume obtained fresh evidence. Server restart retained both completed jobs and the same origin/body, paused without replay, and required an explicit resume. The user-facing server is intentionally left running idle at http://127.0.0.1:64370 with no pending model request. Its owned PID is recorded in `final-checks.json`; four queue slots remain. The product limit is six jobs, 32 calls per job and 96 calls per operator lifetime. Stop this instance with `kill -TERM 79998`; restart on the retained port as documented.

Reported final-trial usage: 388,482 input and 4,804 output tokens across 30 of 31 requests. Cancelled-call usage is unavailable. The CLI is 0.147.0, uses saved authentication and its default model with low reasoning; an exact model name is not reported. No API key was opened or provisioned. Monetary price is unmeasured.

## Checks and preserved failures

**54 focused conformance checks passed**: 20 runtime, 3 policy, 15 agent, 14 bench and 2 scorer. Fake policies are labelled diagnostic and supply no model-control evidence. Ruff, JavaScript syntax, whitespace and notebook validation passed.

The first no-dispatch policy probe returned a valid action but was classified as unexpected tool use because two nonfatal CLI startup diagnostics were misread. It is retained privately; the committed classifier repair accepted a second fresh probe while unknown errors and actual tool items still refuse.

Version 1's actual AI/browser workflow completed both cycles, but the original scorer first encountered a live ownership lock and then applied a 64 KiB protocol-data bound to a larger PNG. Its frozen qualification is **inconclusive**. Retrospective repaired scoring verifies its native cycles and 3.98 cm disturbance, while retaining a false source-unchanged flag; it is not promoted to a passed frozen run. The initial run and scorer failures are retained under `v1/` and its private run directory.

Read-only review then found a pause admission race between the outer loop check and step lock. The regression started a queued job/reserved a call after pause before the fix; an in-lock check now prevents both. Cancelled-motion dispatch was already guarded. The scorer was also tightened so an unrelated measurement refusal followed by a move cannot count as disturbance recovery. Both repairs were preregistered and committed before the fresh version 2 model run.

## Evidence and limits

- [Independent score](qualification-score.json), [force chain](qualification-score.json), [source freeze](source-freeze.json), [final readback and process checks](final-checks.json).
- [Conformance cases](conformance-summary.json), [all-attempt ledger](attempt-ledger.json), [version 1 retrospective record](v1/qualification-score.json).
- [Product ready](product-ready.png), [paused request](paused.png), [recovery in progress](recovery.png), [completed browser reload](completed-reload.png).

Adopt as a local simulated product prototype. The result establishes this bounded image-to-action-to-computer loop on the recorded scene and attempts. It does not establish hardware transfer, general manipulation, broad model repeatability, power-loss recovery, production security or customer demand. Optical area is an apparent calibrated image footprint, not the block's true surface area. Python remains adequate; the native integration already runs in MuJoCo. No measured Rust hot path has been identified.

The next hardware boundary is a persistent body adapter with the same observation/proposal/receipt semantics, qualified first under network delay, disconnects, duplicates and cancellation. The browser product can remain the workcell supervisor while the simulated body is exchanged for a qualified device.
