# Decisions, Jev and Footwork's System One boundary

Source audit refreshed 2026-10-08 against runtime e3b7b08. D1 is the paired development comparison;
D1 and D2 measurements live in the linked results directories. The archived Responses
prototype is not evidence about Decisions.

## Measured recommendation

Keep **Jev as the active text judgment backend**. Use Decisions as a **dedicated visual candidate** for independent validation. Defer full System One agnosticism: quality and speed have not earned broad interchangeability.

| Evidence | Result | Implication |
|---|---|---|
| D1 completion | Decisions finally accepts 5/18 unsupported cases; Jev 0/18 | Frozen substitution fails safety |
| D1 speed | Decisions medians and p95s higher in this run | No demonstrated text speed gain |
| D1 action recovery | Exploratory exact correctness 29/30 Decisions, 28/30 Jev after validating unused-head refusals | Preserve per-answer refusal and consumed dependencies; primary remains 26/30 |
| D2 visual information | Both image arms 12/12 all-three correct; sparse text 0/12, appropriately unknown/refused | Visual role merits independent cases |
| D2 speed | Combined median 171 ms, p95 748 ms | Added capability with tail-latency work remaining |

These are development experiments, including authored synthetic screens, not adoption proof. Reports: [D1](../results/d1-v2-dev-20261008/report.md), [D2](../results/d2-dev-20261008/report.md).

Jev stays in text completion, risk and bounded selection; source selection was audited but not compared. Decisions fits bounded visual questions when text lacks the needed state. System Two retains generated arguments and open-ended reasoning. Footwork code owns consent, scope, freshness, target/source identity, effects and dispatch. A small typed capability seam can support this split without making every role interchangeable. Model/role/prompt-specific admission and independent real-case latency/quality validation precede any activation.

No active factories or thresholds changed. The authenticated contract, development adapters, paired harnesses and receipts are committed locally; existing credentials were reused. Reported-input cost estimate for the full pilot is $0.0513, conservative upper $0.1921 under the authorized $5 ceiling.

## Recommendation before measurement

Evaluate a **provider-neutral semantic judgment contract**, with Jev and OpenAI Decisions as
explicit adapters. A broad refactor depends on measured quality and speed; an image capability
win can justify a dedicated visual backend. Keep admission settings specific to model, role and
prompt version. Jev is
currently the active implementation of bounded judgments; it need not define System One itself.
Decisions is a direct candidate for that role and cannot generate System Two's arbitrary action
arguments, extracted fields or written answers. Keep those with the existing generative backend.

Keep deterministic authority in Footwork: executable target IDs, scope/consent, revision binding,
repeat/effect identity, source grounding, completion floors and dispatch. Neither provider's
probability can establish a server acknowledgment that the offered evidence lacks.

## What the new API changes

The [official guide](https://developers.openai.com/api/docs/guides/decisions) now establishes public
beta availability, POST /v1/decisions with gpt-6-luna, text and inline base64 images, named
predicate/choice/score questions, and independent question batching. Predicates return an estimate
of truth probability. Choices return a selected supplied value, the full option distribution and
a separate confidence. Scores are expectations over zero-based ordered level indices.

This removes the earlier Responses experiment's largest mismatch: we no longer need generated
categorical JSON or invented confidence as a substitute for native semantic probabilities.
It does **not** establish equal calibration, Jev-compatible confidence semantics, model snapshot
stability, account access or Footwork task accuracy. The example choice confidence differs from
its selected probability; do not replace one with the other. A severity score is not a truth
probability, even if normalized to 0..1.

[TypeSafe documents](https://docs.typesafe.ai/confidence) Choice confidence as
`(p_max - 1/n) / (1 - 1/n)`. The OpenAI guide's four-option example is consistent with that statistic
after rounding, but does not specify its formula. Code can define a shared distribution statistic
and retain both native confidences; that makes the statistic comparable in meaning, not the models'
empirical accuracy or calibration. Such a change to admission requires its own settings package.

The guide quotes $0.10/M input tokens with free output/cache reads/cache writes. Regional and
long-context premiums may apply. [Jev 1.13](https://docs.typesafe.ai/models) quotes $0.042/M input
and free output. At equal billed input tokens, Decisions costs about 2.38 times as much. Actual
serialized questions and billing may differ. OpenAI's roughly 10x speed statement is against
Responses; it makes no demonstrated comparison against Jev. D1 must measure matched calls.

## Placement by role

| Role | Current seam | Decisions fit | Required boundary |
|---|---|---|---|
| Completion and unmet requirements | Verifier.build_questions/build_state and verify, verify.py | Direct predicate candidate | Same offered evidence, separate complete/unmet questions, original claims/effects floors, role-specific calibration |
| Destructive effect of an offered proposal | Verifier.judge_destructive; agent.py gate and session.py do | Direct predicate candidate | Judge the exact proposal; probability describes an effect, never grants permission |
| Bounded operation and target choice | JevPolicy.build_request/_consume, policy.py | Direct choice/distribution candidate | Validate IDs, full distribution and freshness; preserve independent confidence; measure selection separately from admission |
| Source segment selection and answer existence | EvidenceSelector.select, evidence.py | Direct choice plus predicate candidate | Return supplied segment IDs; code binds exact text/offsets; synthesis stays in System Two |
| Free-text answer or tool arguments | NativeS2 ChatFn/ChatReply, desktop_s2.py; CrossLoop chat | Outside Decisions' documented finite-answer contract | Existing generative model plus deterministic validation |
| Image predicates | New capability; Jev accepts text only | Plausible additional Decisions role | Separate image experiment; same screenshots cannot be treated as matched text evidence |

Current outer browser S1Policy and native/cross-surface chat callables already permit swapping
some implementations. Internally, SystemOneClient still returns TypeSafe SystemOneResponse;
policy.py, verify.py and evidence.py import TypeSafe questions and inspect provider-native answer
objects. Session factories create AsyncTypeSafeClient separately for do, s1 and done. Replacing
one evaluation factory would not replace all live judgment routes.

## Contract and admission

A narrow portable contract needs named predicate and categorical questions, explicit option IDs
and criteria, typed native answers, full distributions, **separate provider confidence**, requested
and returned model identity, prompt/schema/evidence hashes, usage, latency and refusal/error state.
Providers may support different capabilities; do not force every future model to fabricate scores
it cannot provide. Keep ordered scores separate. Refusal, missing/duplicate answer names, unknown
options and non-finite/out-of-range distributions cannot enter admission.

The optional decisions.py transport added for D1 has no TypeSafe imports. The evaluation bridge
translates current request builders and replays native answers through the current verifier and
arbiter solely to diagnose fixed-threshold transfer. That bridge is not a production neutralization
of those modules. A later adoption package should move neutral types into a small shared module,
adapt Jev and Decisions behind it, and normalize provider errors without losing provenance.

Current verifier acceptance is complete>=0.80 and every unmet<=0.30; action admission uses operation
confidence>=0.55 and target>=0.45, with other code guards. Those numbers remain unchanged in D1.
They are not universal confidence cutoffs. Policy also multiplies group and within-group confidence;
that heuristic is not demonstrated joint calibration for a second provider.

The guide says to use separate requests when a question depends on an earlier answer. Target heads
here explicitly assume a named operation and can be asked independently. The action `destructive`
head instead predicts the most likely next action from the page; it is not bound to the operation
and target actually selected. Portable execution should bind risk judgment to that selected proposal
(a second call when needed) or precompute exact candidate-specific effect heads. Keep action selection
and consent authority separate. D1 risk cases already exercise an explicit offered proposal.

## Adoption sequence

Run the committed D1 development shadow first; retain raw semantic judgments and final guarded
outcomes separately. A role can move to independent validation only if the correctness/safety
criteria permit it. Development fixtures and unchanged-threshold diagnostics cannot justify a
runtime switch. Validate source selection, image-only value and real end-to-end latency separately
if evidence warrants those studies. Do not reopen M sealed adoption or lower thresholds to fit a
preferred backend. Jev can remain the active or preferred backend in any individual role.

If the account lacks Decisions access, preserve an incomplete access receipt and the preregistration;
availability in public documentation is not proof that an authenticated request succeeded.

## Measured text conclusion, 2026-10-08

D1 does not justify broad interchangeability on the user's quality-and-speed criteria. Decisions finally accepts 5/18 negative completion cases versus Jev 0/18, despite positive coverage 13/18 versus 11/18. It is modestly slower at the median and has worse tails in this implementation run. Keep Jev active for text roles. This is frozen-prompt, fixed-threshold development evidence, not a universal model ranking.

The primary action result is confounded by nine refusals on unused target heads: offline recovery validates retained native heads and replays unchanged policy, yielding exploratory Decisions 29/30 exact cases versus Jev 28/30. Keep the registered primary at 26/30. A narrow future contract should preserve per-answer refusals, consume only validated dependencies, and bind effect judgment to the exact selected proposal. Such a seam is worthwhile interoperability work; it is not a reason to route every role to every model. Risk gains retain the registered question/label scope limitation.

Evidence and complete accounting: ../results/d1-v2-dev-20261008/report.md. D2 separately evaluates image added information; its results cannot repair failed text completion safety. Neither experiment grants runtime adoption or relaxes code authority.
