# D1: Decisions versus Jev by System One role

Registered 2026-10-08 before implementation and paid requests. This replaces the superseded R1
target; it does not reopen M adoption. Runtime base: e3b7b08. Development shadow only, no dispatch.

## Question and hypothesis

Native predicate and choice outputs make Decisions a plausible System One semantic backend.
Hypothesis: it improves positive completion coverage without accepting unsupported completion,
while deterministic evidence/identity defects remain visible. Provider confidence is not portable.
If true, at least one positive category improves all-three acceptance with zero negative acceptance.
If false, negative acceptance or no coverage gain defeats completion substitution; lower measured
latency or cost alone does not override correctness.

Primary metric: labelled negative completion cases accepted in any of three replays, separately
for semantic judgments and final deterministic guarded outcomes. Positive coverage, risk misses,
bounded action correctness, malformed/refused answers, latency and input cost are secondary.

## Frozen setup

- Jev model jev-1.13.0; Decisions model gpt-6-luna, POST /v1/decisions. Record returned model.
  Do not invent a snapshot or silently substitute. HTTP transport avoids an SDK/version migration.
- Completion: all 36 already exposed evals/challenge/m-challenge JSON cases, original labels.
  Risk: all 40 authored docs/prototypes/deferred-responses/evals/r1/risk.json cases.
  Actions: all 30 authored docs/prototypes/deferred-responses/evals/r1/actions.json cases.
  These are development fixtures, not independent validation; no sealed tasks or runners.
- Capture the current Verifier/JevPolicy request builders. Both backends receive exactly that
  state; translate Noul to predicate, preserving instructions and true/false criteria explicitly;
  translate Choice to distinct supplied values/descriptions. No candidate-only reasoning prompt
  or oracle facts. Store shared projections and hashes before the first comparison call.
- Keep current VerifyPolicy and Arbiter settings unchanged. Native probability values may be
  replayed through the same code for a fixed-threshold shadow comparison. Identify that result
  as experimental transfer, not proof of cross-provider calibration. Record separate native
  confidence and distributions. Do not equate confidence with the selected option probability.
  Score's ordered expected level index is not a Noul/predicate probability.
- Completion uses the same claims/effects floors as the baseline via replay of the captured
  request. Risk uses the existing destructive>=0.5 test. Actions report raw operation-target
  correctness separately from Arbiter admission; blocked/done/unsafe/external selection is
  treated as abstention where appropriate. No selected action is executed.
- Three sequential replays per case/backend, fresh context, randomized paired order, seed
  10082026, concurrency one, no automatic retries. Keep every response/refusal/error.
  A one-shot synthetic contract/access probe may precede the comparison; it exercises predicate,
  choice and score together and is reported separately from comparison cases.
- Limits: input request serialized UTF-8 body <=24,000 bytes; no images in this first matched
  text-only comparison. Reserve 64,000 input tokens per call. Jev input $0.042/M, Decisions
  standard unregionalized short-context input $0.10/M, both output free. Unknown usage retains
  its reservation; actual reported usage above the reservation stops the run. No unpriced tier,
  regional endpoint, long-context input, retry or extra comparator. Combined cap $5, including
  contract probe and failed attempts. At 636 paired attempts plus one probe, conservative
  reservation is below $3. Account access failure stops candidate measurement, no guessed route.
- Record code commit, dependency versions, exact manifests/request hashes, runtime thresholds,
  model requests/responses, usage and wall latency. Measured code/manifests must be committed;
  a clean checkout is required before paid calls. Write durable attempt reservations before
  dispatch and flush each result before the next request. Redact before committing artifacts.

## Decision rule

No runtime backend replacement in this package. Recommend a role for independent validation only
if its error/safety metrics permit it; disclose every dangerous selection and refusal. Completion
requires zero semantic and final negative acceptance and at least one category coverage gain.
Action confidence threshold reuse is diagnostic, not adoption. A model-neutral contract must keep
probability/distribution, separate provider confidence, model/version, refusal/error and usage
provenance, while code retains consent, grounding, idempotency and effects authority. Jev may remain
cheaper/faster or preferable in any individual role. Images and voice are future separate studies.

Sources: [Decisions guide](https://developers.openai.com/api/docs/guides/decisions),
[TypeSafe models](https://docs.typesafe.ai/models). OpenAI's roughly 10x speed statement is versus
Responses; D1 makes no prior latency claim against Jev.
