# D2: visual information value in a bounded judgment role

Registered 2026-10-08 before fixture/harness implementation and paid requests. Development
capability demonstration, not independent validation or a production adoption test.

## Question and hypothesis

Can Decisions reliably judge visible UI state that Footwork's text projection does not encode?
Hypothesis: screenshots improve confident correct judgments over identical sparse text inputs,
with no confident false-positive judgment on negative visual states. Such a win supports a
dedicated visual backend; it does not establish a stronger text model or full agnosticism.

Primary metric: number of fixtures judged correctly and confidently on all three replays in
combined text+image versus Decisions text-only. Confidence here is a frozen **predicate** band:
true at p>=0.80, false at p<=0.20, otherwise unknown. Negative states confidently judged true in
any replay are the safety guardrail. Report unknowns, refused/malformed responses and observed
latency separately. No action executes, and a screenshot cannot grant consent or prove freshness.

## Design

- Twelve independently code-labelled synthetic UI fixtures: positive/negative pairs for visible
  checkbox state, radio selection, color-only status with a legend, modal occlusion, canvas bar
  height, and locked/unlocked icon state. Render PNGs deterministically from explicit fixture
  state, with no labels/expected answers embedded in model metadata. These are authored examples
  and may be easy; they cannot establish real-user accuracy or task completion.
- Text projection lists available labels and controls but intentionally omits the visual feature.
  It is identical across each opposing pair. All text-only arms get the same projection and
  question; image-only gets the same question and screenshot, combined gets both. This is an
  information ablation, not evidence-matched superiority over Jev.
- Four arms: Jev text-only, Decisions text-only, Decisions image-only, Decisions text+image.
  Jev is text-only; no imaginary image adapter. One predicate per fixture, same wording/criteria
  across provider translation. Native p is retained; bands are diagnostic, not calibrated
  equivalence. Three fresh sequential replays each, randomized paired order, seed 10082027,
  concurrency one, no retries: 144 scheduled attempts.
- Use POST /v1/decisions, gpt-6-luna, inline base64 PNG user-message input. Jev-1.13.0 baseline.
  No SDK/pin changes, no active runtime change. Pool clients. Record actual request/model/usage,
  code and prompt hashes, image hashes/dimensions, native judgments, bands and implementation
  wall latency. Do not call screenshot inference live-session latency or intrinsic model speed.
- Freeze fixture manifest/PNGs and harness before calls. Require a clean checkout and fresh
  run directory. Images <=640x400 and complete request <=24,000 UTF-8 bytes. Reserve 64,000
  tokens per candidate predicate, 64,000 per Jev call; short standard input prices are $0.10/M
  and $0.042/M, output free. Retain unknown-usage reservations. Include every D1 probe, rejected
  request and version's upper in the original combined $5 ceiling; stop rather than overrun.
- Persist the reservation before each dispatch and results before the next. Preserve errors,
  redact artifacts before commit, and never expose credentials. No sealed cases or real app data.

## Decision rule

Recommend collecting independent real visual failure cases only if combined images improve
all-three confident correctness over text-only without a confident false positive on any negative
fixture. An authored ceiling is a capability demonstration only. If this fails, inspect the
offered pixels/contract without tuning to these labels and do not recommend a visual safety gate.
Quality and speed remain the user's determinants of broader architectural interchangeability.
The useful boundary may stay specifically visual, with Jev retained for text judgments.

Source: [official Decisions guide](https://developers.openai.com/api/docs/guides/decisions),
[Jev modalities](https://docs.typesafe.ai/models).
