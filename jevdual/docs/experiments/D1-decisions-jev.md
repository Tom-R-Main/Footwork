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

## Amendment before measurement: fan-out accounting and label scope, 2026-10-08

The guide does not establish whether question fan-out bills shared context once. Conservatively
reserve 64,000 input tokens **per Decisions question**, versus 64,000 once for Jev. Settle only
reported total usage and retain the full reservation otherwise. The earlier below-$3 statement
assumes shared billing and is not an established worst-case bound; the adaptive $5 ceiling may
stop an incomplete run. Short per-question context is still bounded by the 24,000-byte request.

Risk labels describe permission-bearing persistent/external effects; the current captured
judge_destructive prompt describes irreversible/external commit. Save, append, export and similar
cases may expose that question/label scope mismatch rather than provider weakness alone. Preserve
both prompts and labels, disclose mismatch cases, and do not credit benchmark correctness as proof
of a complete permission classifier. Action raw pair correctness includes a correct done choice;
its subsequent Arbiter escalation is mandatory completion verification, not a wrong pair.

## Amendment: bounded request diagnosis and replay repair, 2026-10-08 14:39

The original version stopped after seven attempts on an HTTP 400 at A12. Preserve its receipts;
the response body was not retained, so no particular API constraint or access failure is inferred.
Authorize a single explicit diagnostic request of that frozen case under the remaining original
budget, with bounded key-redacted provider metadata. This is not automatic retry or a resumed run.
Any diagnosed adaptation is committed with its contract tests before a fresh paired run version.

Independent review found that alternate-admission correctness used the original target rather than
the effective alternate, and coarse abstention accepted premature done. Before new measurement,
report exact selected pairs, coarse abstention and effective admitted pairs separately. Connection
pooling differs in the original version; treat those timings as implementation wall times. A new
version may use pooled clients for both providers, still reporting connection, parsing and replay
overhead and making no intrinsic-model or live-session speed claim. All earlier/diagnostic spend
and unknown-usage reservations carry into the same total $5 cap.

## Amendment: diagnosed singleton capability and version 2, 2026-10-08

The explicit frozen-request diagnostic returns array_below_min_length at questions[2].choices:
the endpoint requires at least two choice options. Code may bind a singleton's sole supplied value
without a model request. Version 2 filters those heads from the wire request and marks their
one-hot conditional distribution/confidence as forced_single_option, never provider judgment or
empirical correctness confidence. Preserve the actual native receipt and hash the actual wire body.
Jev still receives its existing supported singleton heads; disclose this adaptation in speed/cost
and quality reports. All logical evidence and current code admission thresholds remain unchanged.

Use pooled clients for both providers. Record implementation wall time and candidate transport
wall time; cold connections and local replay overhead remain disclosed. Compute exact selected
pair correctness separately from safe abstention, and score admitted alternates on their effective
target. This repair applies to a fresh version 2 run directory; version 1 remains incomplete.
Carry the diagnostic's conservative budget upper forward, including all unknown-usage failures.

The user clarified that quality and speed determine full agnosticism. Treat money as descriptive;
recommend broader interchangeability only where both quality/safety and measured latency warrant
it. A visual capability win may justify a dedicated role without a full provider-neutral refactor.
Image-versus-text information effects require a separate preregistration and do not establish a
text-judgment win or live-session performance. Any adoption still requires independent validation.

## Result — 2026-10-08

All 636 scheduled version 2 attempts finished; 627 satisfy the strict batch contract. Completion rule fails: Decisions accepts 5/18 negative cases finally and 10/18 semantically, versus Jev 0/18 for both; positive final coverage is 13/18 versus 11/18. No speed advantage is observed in this implementation. Risk correctness is 35/40 versus 33/40 with the preregistered question/label scope limitation.

Primary action correctness remains 26/30 versus 28/30. A separately disclosed offline analysis recovers nine unused-target refusals without inventing scores, yielding exploratory 29/30 versus 28/30; this does not alter the primary. Keep Jev active and avoid a broad neutralization. Evaluate visual value separately under D2. Full accounting, timings, failures, recovery and limitations: ../../results/d1-v2-dev-20261008/report.md. No heldout run or runtime backend change.
