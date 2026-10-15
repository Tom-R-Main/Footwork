# SC1: SubQ Snap versus pinned Jev on Footwork development fixtures

Registered 2026-10-15 before implementation/tests or new paid requests. This is a development
shadow comparison with no app dispatch or heldout access. The user's aggregate ceiling is $1
for this package, including any new probe, diagnostic, failure or repaired run; SQ1's earlier
completed smoke is outside this new package.

## Hypothesis and primary metric

SubQ Snap preserves unsupported-completion safety while matching positive completion coverage and
client wall latency of Footwork's currently pinned Jev. If true, no negative completion is accepted
in any of three valid replays and positive all-three coverage is at least Jev's. If false, disclose
each unsafe acceptance, missing replay, coverage loss or slower latency unchanged.

Primary metric: number of labelled negative completion cases accepted in any replay, separately
for native semantic judgments and final deterministic guarded outcomes. Report missing/error
negative cases explicitly; incomplete measurements cannot establish safety. Secondary: positive
all-three/any coverage, completion error count, risk correctness/misses, raw exact action pairs,
incorrect admitted action pairs, latency and input-token charge.

## Frozen design

- Models: application baseline `jev-1.13.0` and `subq-snap-preview`. Record requested and returned
  identities. Do not substitute latest aliases or upgrade to newly available Jev versions.
- Inputs: all 36 exposed `evals/challenge/m-challenge/*.json` completion fixtures, 40
  `docs/prototypes/deferred-responses/evals/r1/risk.json` cases and 30 corresponding
  `actions.json` cases, preserving existing labels. No sealed/heldout fixtures.
- Reuse D1's capture/replay helpers to freeze current Verifier/JevPolicy states/questions and
  claims/effects floors. Hash shared projections and actual wire requests before measurement.
  Preserve JSON instruction/criterion values on both providers unless an explicitly recorded
  amendment is needed after a provider rejection. No oracle enrichment or prompt tuning.
- Snap supports 1–16 heads and 2–255 choice options. Locally bind singleton choices to their
  sole supplied option, one-hot probability and confidence 1, with explicit
  `forced_single_option` provenance. This is deterministic conditional binding, never a model
  judgment or empirical confidence. Jev continues receiving its supported singleton heads;
  disclose the transport difference in cost and latency. Current development projections have
  at most twelve heads. Fail closed on unsupported limits; never truncate silently.
- Three fresh-context sequential replays per provider/case: 636 scheduled attempts. Role blocks
  completion, risk, actions; randomized case order and paired provider order, seed 15102026.
  Concurrency one, persistent clients for both, automatic retries disabled. No separate paid
  synthetic probe is planned; the first comparison call also checks real access.
- Preserve separate choice confidence and selected probability. Replay unchanged VerifyPolicy
  and Arbiter settings; threshold transfer is experimental, not calibrated interchangeability.
  Score isn't used by these fixtures. Report final action admission independently of pair
  correctness and score any admitted alternate using its effective target.
- The frozen risk prompt asks about irreversible/external commits, whereas some fixture labels
  include persisted writes; retain this existing scope limitation and list misses.

## Budget, credentials and evidence

Use current published input prices: Jev $0.042/M and Snap $0.05/M; output free. Every dispatched
attempt first reserves 64,000 input tokens for Jev or 64,000 per Snap wire question, persists the
reservation and request hash atomically, and checks the aggregate cap before sending. This is a
conservative local reservation, not a provider billing guarantee. Settle only nonnegative integer
reported total input tokens; retain unknown usage reservations. Stop if reported usage exceeds
reservation, the next reservation would exceed $1, or a request/access/billing/transport error
prevents valid measurement. Semantic misses do not stop the run. No automatic retry.

A repaired or diagnostic run must carry the full conservative prior total from preserved run
ledgers, so a fresh directory cannot reset the $1 limit. Keep a single package ledger/lock and
refuse concurrent or stale unresolved runs. Never overwrite an existing run. Keep every attempt.
No extra paid calls beyond this schedule without an appended preregistered amendment.

Use environment keys or explicitly approved existing Jev credential loading, and a hidden native
dialog for missing keys. Never open unrelated credential files or write key values into artifacts,
logs, commands or git. The Snap key from SQ1 was deliberately not saved. Use the existing verified
CA bundle; do not disable certificate verification or install packages. Sanitize any echoed keys
before atomic artifact writes and run the repository result redactor before committing artifacts.

Commit measured code/config/manifests before paid calls; start from a clean checkout. Freeze
that revision during the run. Record dependency versions, model IDs, rates, thresholds, transport
settings/CA digest, request hashes, usage, cold/first request and timings. Save shared-inputs,
per-attempt native receipts, results, budget, summary and report under a new results/sc1-* directory.

## Latency analysis and decision rule

Report ordinary median and nearest-rank p95 request wall time and total replay wall time by
provider/role, with valid and failed measurements separate. Compare common-success paired
case/repeat observations and paired Snap/Jev ratios; report cold first calls separately and a
warm-only sensitivity. These are implementation/network timings, not isolated model inference.

Recommend independent validation for a role only if its complete evidence supports the safety
rule. Any unsupported final completion defeats recommending Snap for completion. A semantic
safety failure remains visible even if deterministic floors catch it. Good action/risk results
cannot repair completion failure. No runtime default changes, threshold tuning, heldout run,
production dispatch or claim of adoption in this package.

The backend implementation may expose explicit experimental provider/model selection while
retaining Jev defaults and existing code authority, regardless of this study's ranking. Test that
all active S1 factories propagate model and pricing correctly; unsupported configuration or
malformed outputs fail closed. Document how to select/revert, and recommend defaults based on
measured results rather than automatically promoting the candidate.

Sources checked 2026-10-15:
[SubQ Decisions](https://docs.subq.ai/endpoints/decisions-api/),
[SubQ pricing](https://docs.subq.ai/using-the-api/models/),
[Jev models](https://docs.typesafe.ai/models).
