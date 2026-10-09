# Qualify a visual role

The local VQ1 package prepares and checks qualification evidence. It does not collect real-provider judgments or certify model quality. Its CLI is offline: no key lookup, paid call, application action or model routing change. [VQ1](experiments/VQ1-visual-qualification.md) records the experiment and decision rules; [the native advisory service](visual-checks.md) remains separate.

## Start with the concrete development corpus

From `jevdual/`, the checked-in `evals/visual/vq1/development/` contains 24 authored PNG cases across document/reference matching and crop/subject containment. Each family has three source groups and supported, near-miss, ambiguous and adequate-text-control variants. Placeholder native surface identifiers describe authored contract fixtures; these are not Cua captures. Labels and construction notes are excluded from provider requests. Fixed .5 smoke answers exercise mechanics without reading labels.

Run locally with a fresh attempt name:

```sh
.venv/bin/python -m evals.visual_qualification preflight \
  --corpus evals/visual/vq1/development
.venv/bin/python -m evals.visual_qualification smoke \
  --corpus evals/visual/vq1/development \
  --protocol evals/visual/vq1/development/protocol.json \
  --out runs/vq1/example-smoke
.venv/bin/python -m evals.visual_qualification score \
  --run runs/vq1/example-smoke --out results/vq1-example-score
```

The smoke schedules 96 slots: 24 cases × two arms × two replays. The image arm uses the production Decisions serialization, response parser and durable visual ledger through injected MockTransport. The text arm validates its input projection with a fixed local callback; it does not exercise the Jev SDK or measure Jev quality. All probabilities and costs in this mode are simulated. Ordinary HTTP transport is forbidden in its regression. Replay latency includes collection/callback validation work; it excludes fresh UI capture and is not workflow speed.

To author another synthetic corpus, `seed --out <fresh-directory>` writes manifests, PNGs, source notes and an example protocol. To prepare a run without collecting even mock judgments, use `freeze` with the same corpus/protocol/output arguments. All outputs must be fresh. Historical artifacts are never overwritten.

## Prepare independent inputs and labels

Use the development manifest as the executable schema example; replace authored inputs with authorized real captures and supplied reference/source renders. Each case has an opaque case ID, role, source group, input envelope and local provenance record. Capture PNG dimensions, hash, surface/viewport/target binding and crop transform are checked against the production evidence contracts. Paths remain inside the corpus and symlinks are refused. Preserve actual capture identity; do not turn a supplied image into an alleged native capture.

`labels.json` maps every case ID to true, false or null. Null means the available evidence cannot resolve the predicate; it is not an error or a negative label. Hash the label file in the manifest. The provider projection includes only the typed criterion, available AX/OCR and authorized image/geometry evidence. Local paths, labels, source groups, reviewer identities and construction notes are not provider inputs. Accessible controls must include the text actually available to the competing text arm; invented text or weak OCR is not a valid quality comparison.

Qualification preflight requires `split: qualification`, independent real-source declarations, a hashed local source record, at least two distinct annotator identities and adjudication for every case. Supply every development corpus the team exposed with repeated `--development` arguments; source-group or exact image overlap with those references makes the corpus ineligible. Identical images assigned to different groups are also ineligible. These checks establish necessary provenance conditions, not independence or representativeness: reviewers must still assess source overlap, case difficulty and annotation quality. Related crops/pages/revisions from one source stay in one group.

The initial protocol proposes .90/.10 interpretation bands, a .01 upper false-endorsement bound, .80 lower positive-support bound and .95 lower epistemic-abstention bound, each at .95 marginal confidence. These apply only to this experiment; no runtime threshold changes. With no misses, the lower bounds need at least 14 independent positive and 59 ambiguous groups; the negative bound needs 300 groups. Both families therefore need substantially more than the 24-case dev corpus. Bounds assume representative independent groups and do not provide simultaneous confidence across all roles/arms.

The example's 200-call/$2 local ceiling is for bounded machinery development, not sufficient capacity or an authorized spend estimate for independent qualification. The .01-per-attempt reservation is a conservative example setting, not verified provider pricing. A real collection package must freeze source/prompt/model/evidence identities and adequate limits after inspecting its corpus, current provider behavior and concrete cost estimate, before any paid calls.

## Collect, score and measure without conflating evidence

`runner.collect` accepts explicitly supplied asynchronous callbacks over PreparedCall objects; it discovers no provider or credential. A PreparedCall contains only the safe body and its digests plus the typed visual request for an image arm. The image body is the production wire contract; the text body is an evaluation projection for a future Jev callback. The current CLI exposes only mock callers. An additional multimodal reference may be declared in a protocol and injected later; no such provider is built or measured here.

A callback must return status, probability and returned model identity, plus a cost bound when available. Reservation is fsynced before callback dispatch. Missing usage retains the reservation; a larger unknown-usage estimate retains the larger bound. Over-reservation stops collection and invalidates the answer. Timeouts, cancellations and errors are recorded without retries. Unstarted slots are recorded as not_run; interrupted collections retain partial rows and charged reservations. Changed corpus, labels, protocol, schedule, dependency versions or pinned production interpretation code refuses further collection/scoring. Raw provider errors, credentials and images are not included in attempt rows.

A run contains `frozen.json`, `started.json`, `budget.json`, `attempts.jsonl`, `summary.json` and `closed.json` when it completes. The frozen schedule binds each case/arm/replay to request, evidence and prompt hashes. Score refuses duplicate, malformed, mismatched or changed bindings; missing rows remain explicit. Complete means every schedule slot is accounted for, including not_run, not that every judgment succeeded. Qualification also rejects measurement errors, synthetic/mock/import provenance, insufficient source groups, poor coverage or ambiguity endorsements.

Quality reports count source groups rather than variants/replays. They include wrong endorsements, confidence bounds, supported coverage, false rejection, epistemic and conservative ambiguity handling, status counts and descriptive Brier/calibration bins. Invalid results cannot retain a probability or impersonate abstention. Qualification is reported per family and arm, with execution_authority always false.

`WorkflowTimer` starts before a real workflow and records measured wall time independently from named phases. Its `measure(name)` context manager covers actual work; `skip(name)` marks an explicitly unused phase. `finish(verified_outcome=..., interventions=...)` requires route, capture, OCR, encoding, provider, validation, escalation, review, dispatch, settle and readback to be accounted for. The caller must establish the outcome through independent readback; the timer does not operate an app or verify a document.

The reusable collector records evidence replay only. A future approved workflow driver can import rows matching the frozen request/evidence/prompt identities and timing contract; this package contains no such driver. Speed scoring requires complete workflow rows for both arms, measured totals and phase consistency, preserved baseline-success cases and no higher mean interventions. Its p95 ratio uses the same successful case/replay pairs; extra easy successes cannot mask a slowdown. All attempted timings and each arm's complete success distribution remain visible. Replay-only, mixed or incomplete timing cannot qualify speed.

## Build on the result

First collect and independently label one real document-preview/reference corpus. Review the concrete inputs, frozen protocol and bounded spend before provider-backed measurement. If the family passes quality, run one measured document workflow with operator review and independent document identity readback. Qualify browser capture separately. Crop execution, automatic visual routing, broader provider interchangeability and additional action authority remain later scoped decisions.
