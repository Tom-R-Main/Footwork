# SubQ Snap: first live smoke test

All twelve synthetic routing cases passed. Each response also satisfied the typed contract,
completion-probability check and ordered-progress check. This establishes working access and
basic decision behavior; it is enough to justify a separately registered development comparison.

| Measure | Observed |
| --- | --- |
| Model | `subq-snap-preview` |
| Inference requests | 12, no retries |
| Correct routes | 12/12 |
| Valid choice/noul/score response sets | 12/12 |
| Completion checks | 12/12 |
| Progress checks | 12/12 |
| Client wall latency, median | 376 ms |
| Client wall latency, maximum | 779 ms |
| Reported input tokens | 54,769 |
| Reported output tokens | 0 |
| Estimated charge at $0.05/M input | $0.00273845 |

The charge is calculated from reported usage and documented pricing, not an invoice.
Latency includes the Python HTTP client and network; twelve requests do not estimate a tail percentile.

| Irrelevant history, ASCII characters | Correct routes | Reported tokens per call | Median latency | Maximum latency |
| --- | --- | --- | --- | --- |
| 0 | 4/4 | 369–370 | 376 ms | 388 ms |
| 8,000 | 4/4 | 1,517–1,518 | 323 ms | 360 ms |
| 80,000 | 4/4 | 11,804–11,805 | 513 ms | 779 ms |

The four states require acting, waiting for an ongoing save, recognizing a successful durable
save, or asking for a missing required value. Every request asks for a route, a completion noul,
and progress on three ordered levels. Full synthetic prompts, response probabilities, request
hashes, usage and latency are retained in [attempts.json](attempts.json) and the request files.
The 80,000-character filler is repetitive and the decisive evidence is always at the end.
These cases do not test distributed evidence retrieval or difficult long-context reasoning.

## Provenance and verification

Prediction and experiment were committed at `d2e387d`; measured runner revision is
`ff69a0fcee3892bd6474f2a03b0bef069ba077ab`. Offline validation passed 28 tests and Ruff.
An independent saved-artifact audit reconstructed all twelve request hashes, revalidated every
response, checked expected decisions, and reconciled usage/cost totals. The repository result
redactor changed zero files. No key was written to the source tree or result artifacts; the native
hidden dialog passed it only to process memory. That process has exited.

The initial [access attempt](../subq-snap-20261015T154737/summary.json) failed before inference
because this interpreter lacked a default CA bundle. A committed amendment selected the already
installed certifi CA bundle using `SSL_CERT_FILE`, preserving certificate verification. Public
verified connectivity then succeeded before the fresh live run. The bundle's SHA-256 and Python
version are recorded in [environment.json](environment.json). No package was installed.

## Interpretation for Footwork

Snap exposes familiar choice/noul primitives and an ordered score, making it a plausible candidate
for Footwork's bounded semantic decisions. No existing backend, threshold, dispatch or completion
authority changed. The sample is deliberately easy, with no Jev comparator, real application
execution, images, prompt-injection evaluation or calibration measurement. It does not establish
the vendor's 100K-token speed, 384K context limit or benchmark superiority.

The useful next study is a matched development-fixture comparison against Jev for exact
operation/target selection and supported completion, reporting semantic decisions separately from
Footwork's unchanged admission checks. No heldout adoption or runtime replacement is authorized by
this smoke result. The preregistered twelve-request test is complete; no extra calls were made.

Current official references: [Decisions API](https://docs.subq.ai/endpoints/decisions-api/),
[Models and pricing](https://docs.subq.ai/using-the-api/models/).
