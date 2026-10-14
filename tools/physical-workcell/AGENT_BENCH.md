# Visual AI control of the simulated bench

An external multimodal agent can inspect the bench image and propose its next action through `agent_bench.py`. The controller still owns dispatch, freshness, physical limits, measurement persistence and reset verification. The handoff supplies no detector coordinates, native body poses or automatic motion planner.

This interface works with the AI host's existing image-view and shell tools. It calls no provider API and needs no model key. The initial experiment uses the AI in a Codex conversation, rather than an unattended model service. The `host_role` label identifies the intended caller; it is not authentication or proof that a particular model authored a proposal.

## Start a session and task

Run from the repository root with the existing pinned Python/MuJoCo environment. Choose new private output directories. Initialize a bench using [BENCH.md](BENCH.md), then bind a separate agent session:

```sh
tools/physical-workcell/.venv/bin/python tools/physical-workcell/agent_bench.py \
  --session-dir tools/physical-workcell/output/my-ai/session \
  init --bench-dir tools/physical-workcell/output/my-ai/bench

tools/physical-workcell/.venv/bin/python tools/physical-workcell/bench.py \
  --root tools/physical-workcell/output/my-ai/bench start --job-id trial-1 \
  --target-zone '{"x_min":0.035,"x_max":0.105,"y_min":-0.025,"y_max":0.025}'

tools/physical-workcell/.venv/bin/python tools/physical-workcell/agent_bench.py \
  --session-dir tools/physical-workcell/output/my-ai/session observe
```

The returned challenge includes an exact image path and digest, calibration, job/phase identity, task region, home region, pusher dimensions and bounds. Open the actual image with the host's image tool before choosing a move. Positions are meters in the calibrated `sim_world` frame; targets position the blue pusher, not the orange block. Native contacts move the block.

CLI responses remove detector coordinates and private poses from measurement and status
receipts. Pixel counts, footprint area and receipt identities remain available. Full receipts
stay on disk for the separate scorer; the internal Python methods are not a filtered model-input
surface. Use the CLI when supplying observations to an AI host.

## Propose, dispatch, inspect

The AI supplies one bounded action and a short description of its purpose:

```sh
tools/physical-workcell/.venv/bin/python tools/physical-workcell/agent_bench.py \
  --session-dir tools/physical-workcell/output/my-ai/session propose \
  --challenge-id CHALLENGE_ID --action move --target-x TARGET_X --target-y TARGET_Y \
  --intent 'Describe the intended next movement.'

tools/physical-workcell/.venv/bin/python tools/physical-workcell/agent_bench.py \
  --session-dir tools/physical-workcell/output/my-ai/session dispatch --proposal-id PROPOSAL_ID
```

The other actions are `measure`, `begin_reset` and `finish_reset`; they accept no target coordinates. Preparation must pass the bench's image/native placement checks before `measure`. The measurement worker saves and verifies the result separately. `begin_reset` requires the measured active job. `finish_reset` requires image/native home verification and retained reset-contact evidence.

A dispatch result includes its outcome and, when available, a new observation challenge. Inspect that image before another proposal. An exact repeated dispatch reads its historical result; the embedded observation is the snapshot from that earlier result, not a new observation. Call `observe` for current evidence. A new job can start only after reset is verified.

Proposals and dispatch intent are retained before effects. A stale challenge refuses. An unresolved or unknown dispatch blocks new effects and is never automatically replayed. The AI should stop on unknown outcomes and inspect the retained evidence. It cannot declare measurement or reset successful by returning a model-written success field.

Session evidence is retained in SHA-bound challenge, proposal, intent and result files under its private directory. Source changes invalidate the session. Keep all failed proposals and outcomes. The interface deliberately leaves perception and action selection to the external AI host; its records alone do not prove image consumption, which the host trial must record separately.

## Trial and limits

[SIM7 preregistration](../../jevdual/docs/experiments/SIM7-agent-visual-bench.md) specifies two successive AI-controlled jobs and a disturbance between saved proposal and dispatch. [Post-trial scoring](score_agent_bench.py) reads native state and SQLite after the AI attempt, so truth data cannot guide its moves. The [trial report](../../jevdual/results/agent-visual-bench-20261011/report.md) records the outcome.

The existing simulation pauses between commands. This interface controls one known block and a bounded pusher, not a general robot or real actuator. It does not add provider integration, unattended scheduling, hardware permissions or a production Footwork capability grant.
