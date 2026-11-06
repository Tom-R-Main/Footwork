# SQ1: SubQ Snap synthetic contract and routing smoke test

Registered 2026-10-15 before harness implementation or inference. Model: subq-snap-preview,
POST https://api.subq.ai/v1/systemone. No runtime integration, app dispatch, heldout fixtures,
Jev comparison, private documents or real screenshots.

## Hypothesis and predictions

Snap returns valid choice, noul and score answers for obvious synthetic agent states and retains
the expected next route with irrelevant historical context. If true, every call is schema-valid
and its route matches the declared oracle. If false, at least one valid response selects the wrong
route or distractor text changes the decision. Missing access is inconclusive.

## Design

Four cases crossed with zero, 8000 and 80000 ASCII distractor characters, twelve calls total.
Distractor text is explicitly historical and contains no instructions. Current authoritative
state follows it. Ask all three questions in each call: route (act/wait/done/escalate), completion
probability, and completion score with three ordered levels (not started/partial/complete).

Oracles:
- act: requested local draft has not been created; an enabled Create draft control is available;
  completion false and score near 0.
- wait: local draft is being saved, busy indicator active, no completion receipt;
  completion false and score near 1.
- done: exact requested draft content and one successful durable save receipt are present;
  completion true and score near 2.
- escalate: requested draft requires a missing required value and user clarification;
  completion false and score near 0.

Primary metric: exact route accuracy out of twelve planned calls. Report incomplete denominator
separately. Secondary diagnostics: contract validity, completion noul threshold 0.5, score within
0.5 of expected level, reported usage, each request's wall latency, descriptive median and maximum.
No calibration, tail-latency, long-context-limit or general agent-performance claims from this sample.

## Guardrails

One GET /v1/models access check, then at most twelve POST attempts; no automatic retries. Stop on
any HTTP, transport, malformed-response or billing/access error. Thirty-second per-call timeout.
Only synthetic states leave the machine. Read the API key from SUBQ_API_KEY or an explicit hidden
macOS dialog; never write or print it. No paid action until measured code is committed.

Input is ASCII and each serialized request must be <=90000 bytes. Reserve that byte count once
per question, conservatively at $0.05 per million input tokens, before dispatch. Cap cumulative
reservation/settled usage at $0.20; retain reservations when usage is unavailable, and stop if reported
tokens exceed reservation. These are local test bounds at documented pricing, not a provider billing
guarantee. Report actual usage and estimated charge separately. Never overwrite an existing run.
Keep durable attempt reservations and request hashes before sending; flush results after each call.
Save source commit, model list, per-case results and summary under results/subq-snap-*; run
scripts/redact_results.py before committing artifacts. No credentials in request/response artifacts.

## Decision rule

Twelve valid routes matching the oracle justify a larger separately registered development study,
not adoption. Any failure is reported unchanged; no prompt tuning or extra live retry in SQ1.
Existing Jev thresholds, confidence semantics and runtime policy stay unchanged. Image capability,
100K-token speed, 384K context and vendor benchmark claims remain untested.

Sources: https://docs.subq.ai/endpoints/decisions-api/ and
https://docs.subq.ai/using-the-api/models/ (checked 2026-10-15).

## Amendment before new measurement: verified CA configuration, 2026-10-15 15:48

The first run, results/subq-snap-20261015T154737 at 6f8ae86, stopped at the model-list GET
with a local certificate error and zero inference attempts. Preserve it. Select this environment's
already installed certifi CA bundle using SSL_CERT_FILE, retaining certificate verification,
and test public connectivity before a fresh access/inference run. No package installation,
provider-error retry or changed prompts. The original aggregate limit of twelve inference attempts
and $0.20 local reservation ceiling includes every run; zero inference attempts have occurred.
Record the CA bundle digest with the new results. Commit the atomic ledger-write refinement
before the new measurement; preserve the previous ledger if replacement fails.

## Result

Completed 2026-10-15 at ff69a0f. Fresh run returned 12/12 valid response sets and expected routes,
with 12/12 expected completion classifications and progress checks. Reported usage is 54,769 input
tokens and zero output tokens; estimated charge is $0.00273845 at the documented rate. Median client
wall latency is 376 ms; maximum is 779 ms. Maximum per-call reported context is 11,805 input tokens.
The initial TLS access failure sent no inference requests; aggregate inference attempts remain twelve.

The smoke hypothesis holds. This result justifies separately registered development evaluation;
it does not justify runtime adoption or vendor benchmark claims. Full records and limits:
[report](../../results/subq-snap-20261015T154911/report.md),
[summary](../../results/subq-snap-20261015T154911/summary.json), and
[initial access failure](../../results/subq-snap-20261015T154737/summary.json).
