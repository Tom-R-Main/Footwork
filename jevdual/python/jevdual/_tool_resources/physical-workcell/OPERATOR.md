# Footwork Bench

Queue an inspection, watch the AI prepare the block from camera images, and get a saved optical measurement after placement is verified. The AI then returns the block and pusher home by contact so the next job can use the same bench.

This is a local simulated product. The camera is a MuJoCo render and the actuator is a bounded XY pusher. Real cameras and robots are future adapters.

## Start

Run from the Footwork repository root with the existing pinned workcell environment and Codex CLI 0.147.0 signed in. Each new operator needs an empty private directory. No API key is provisioned. The policy uses saved CLI authentication as described in the [Codex non-interactive documentation](https://learn.chatgpt.com/docs/non-interactive-mode).

```sh
tools/physical-workcell/.venv/bin/python tools/physical-workcell/bench_operator.py init \
  --root tools/physical-workcell/output/my-bench
tools/physical-workcell/.venv/bin/python tools/physical-workcell/bench_operator.py serve \
  --root tools/physical-workcell/output/my-bench --port 8765
```

Open the printed loopback URL. Select **New job**, name the inspection, choose a region and add it to the queue. **Test recovery** uses the far region and applies a bounded external force after the AI's first measurement decision is saved. The stale decision must be refused before the AI receives another image.

The operator shows the most recent captured image, planning state, last intent, queued jobs, measurement and retained activity. The optical area is the orange image footprint multiplied by calibration; it is not a claim about the block's true surface area. Job completion requires the separately saved SQLite measurement and verified native contact reset. Reloading preserves jobs and results.

**Pause** cancels a pending model process and withholds its reply. An already running native action may finish before the next boundary. **Resume** requires a known bench state. An uncertain physical outcome blocks further work. Stop the server with Ctrl-C; restart on its retained port and explicitly resume after inspecting unfinished state.

The current limit is six jobs per operator, 32 model requests per job and 96 requests per operator lifetime. Reservations count even when a model call fails or is cancelled. Token totals include only reported usage and show when reporting is incomplete. Monetary cost is not measured.

## Boundaries

`bench_operator.html` provides the browser interface. `bench_operator.py` serves loopback HTTP. `operator_runtime.py` serializes queue ownership, model reservations and dispatch. `codex_policy.py` sends the exact PNG and bounded task history to an ephemeral Codex process with action tools disabled, then validates its structured response. Existing `agent_bench.py` and `bench.py` own image freshness, source identity, movement bounds, measurements, replay refusal and native verification.

The model chooses each action. No coordinate planner runs beside it. Detector locations and native poses stay out of its input. Source changes invalidate the retained operator; create a new operator for changed source. Private call directories retain failures, model output and process outcomes, while committed reports contain derived evidence.

This package lives beside the existing workcell experiments in Footwork. Python and browser JavaScript are sufficient here; native MuJoCo already performs the integration. A Rust hot path needs a measured bottleneck and a pure-Python equivalence test before adoption.

The prototype does not establish hardware transfer, unattended physical safety, broad model reliability or customer demand. Preregistered qualification: [SIM8](../../jevdual/docs/experiments/SIM8-bench-operator.md).
