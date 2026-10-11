# SIM8: unattended visual control and a usable bench operator

## Question and hypothesis

Can a local bench-operator product run two successive image-guided jobs using the installed, authenticated Codex CLI for decisions, retain the existing simulation guards, recover from an injected displacement, and expose truthful progress, measurement results and pause controls in the browser?

The hypothesis is that the external AI handoff can be driven by an independently running model process, with deterministic scheduling, call budgets and result verification. The browser can provide task creation and supervision without creating another physical-authority path.

## Predictions

If true, two queued jobs complete on one retained bench, each with one saved measurement and contact reset. A disturbance after a saved second-job measurement decision refuses that stale action; a subsequent image-based model decision recovers. Browser reload preserves job/result state. A pause request during model inference prevents the returned decision from dispatching; resume obtains fresh evidence. Neither the browser nor a model-generated completion flag can bypass the bench.

Against: chat supervision or a deterministic coordinate planner is needed to complete jobs; stale images dispatch; stopped model replies execute; interrupted effects replay; the UI reports completion without verified reset and saved measurement; native guard source must be weakened.

## Design

Add an isolated product beside existing physical-workcell tools: a bounded Codex CLI visual-policy adapter, a durable serialized job runtime, a loopback-only HTTP app and a responsive browser operator. Reuse the current agent and bench APIs unchanged. The model receives the exact PNG, task/calibration and a bounded history of chosen actions/outcomes. Strip detector coordinates and native poses. Codex runs ephemerally with user configuration/hooks, shell/action tools and web access disabled; saved CLI authentication is used, without opening or provisioning keys. Validate structured model output before proposing an action.

Persist call reservation and dispatch intent before each boundary. Count unavailable/cancelled model calls against the budget; never retry a possibly dispatched physical effect. One active job, at most 32 model calls per job, bounded call timeout, and pause at action boundaries. Pause does not promise mid-motion hardware cancellation. Unknown physical/handoff outcomes block resume; unavailable model output pauses for operator attention. Source drift and restarts do not implicitly replay unfinished work.

Use stdlib Python and plain HTML/CSS/JavaScript with the existing MuJoCo environment. No new dependencies, cloud deployment, hardware or API-key writes. Operator jobs request an image-footprint measurement with a target region. Preserve all attempts and model logs privately; commit derived reports rather than raw model traces.

## Qualification and primary metric

After development conformance, freeze measured source before live model calls. Drive the actual browser to enqueue an ordinary job (region x=[0.035,0.105]) and a disturbance job (x=[0.045,0.115]), both y=[-0.025,0.025]. Inject one bounded native force between the second job's saved first measurement decision and dispatch. Score native measurement/reset states and read-only SQLite after the run, separately from the model. Record every model call, proposal, refusal and cleanup outcome.

Primary metric: completed queued job cycles, required 2/2 on the first frozen qualification attempt. Stale refusal and fresh-image recovery are required, as are truthful browser readback and pause semantics. Conformance can use an explicitly labelled fake policy to deterministically test failures; that is not model-control evidence. A failed frozen run is retained and reported; any repair needs a new preregistered version rather than a hidden retry.

## Decision and limits

Adopt only as a local simulated bench-operator prototype if the complete flow and guards pass. Record model/CLI identity, call count, token usage when reported and elapsed time; subscription usage does not supply an independently verified monetary price. This does not establish hardware transfer, broad model repeatability, production security, physical power-loss recovery, billing accuracy or demand.
