# Secondary review and AI annotation audit — 2026-09-24

Reviewed checkout: `ee0d287`. This is an AI review performed for the user, not human validation. The native integration is a useful research adapter. Keep it experimental: neither default adoption nor a general calibration-transfer claim is supported yet. The next milestone should repair task semantics, authorization coverage, and evaluation evidence before expanding the app set.

## Completed audit work

- `web-audit.csv`: all 40 requested Q1 audit rows, each with a label and rationale.
- `native-audit.csv`: all 40 requested Q10 audit rows, each with a label and rationale.
- `percent-disagreements.csv`: separate judgments on all 31 native model-disagreement rows (some overlap the 40-row native audit).
- `enriched-adjudications.json`: four packet-unclear append completions become wrong when earlier same-run observations are admitted.
- `agreement.json`: comparison with the existing two model passes, using run ID to distinguish repeats.
- `sensitivity.json`: independently recomputed native totals and confidence discrimination analyses.
- `probes.py` / `probes.json`: fake-bridge reproductions; no real desktop actions or model requests.
- `provenance.json`: reviewer identity, scope and hashes. Original audit sheets and model labels are preserved.

The handoff exposed aggregate results and some conclusions before this review. Individual model-label files were not read until the initial 80 judgments were frozen. This is therefore partially blinded at best. The packets themselves expose the confidence scores being evaluated. No claim of fully independent ground truth is warranted.

| Packet-only audit | Right | Wrong | Unclear | Agreement with agreed model labels | Kappa |
|---|---:|---:|---:|---:|---:|
| Web, 40 rows | 11 | 15 | 14 | 24/36 = 66.7% | 0.495 |
| Native, 40 rows | 22 | 4 | 14 | 19/32 = 59.4% | 0.329 |

The denominators exclude existing `disagree` labels. These disagreement-enriched samples are not random accuracy samples; the agreement figures are not estimates of model accuracy on all tasks. Some disagreement is a difference in what is being judged: selecting a password field can be appropriate while the missing value makes the complete input action unjudgeable. Split operation/target appropriateness, argument correctness, and completion support into separate labels rather than conflating them.

Under the supplied rubric, a `done` can be a plausible stopping point without certifying an unseen answer. For example, a visible `Capital Canberra` row supports stopping to answer. A Calculator key history without its display does not establish the observed result. The rubric should make this distinction explicit.

## What the recent work establishes

The native adapter reuses the policy, arbiter, verifier and trace vocabulary over Cua window observations. Keeping element tokens out of the model-facing candidate table and checking candidate membership are sound choices. The native two-stage policy path preserves the initial operation confidence and nouls rather than replacing them. The developer recorded an unfavorable experiment and did not adopt the backend by default; that decision is appropriate.

Recomputed from the 63 result rows:

| Arm | Predicate passes / 21 | Predicate + done / 21 | Estimated recorded cost | Cost per predicate + done |
|---|---:|---:|---:|---:|
| S1 only | 11 | 6 | $0.02102 | $0.00350 |
| Dual | 12 | 6 | $0.06476 | $0.01079 |
| Guarded | 17 | 11 | $0.05212 | $0.00474 |

Dual costs about 24% more overall and 2.28 times as much per recorded verified completion as guarded. The five-completion gap is exactly the two guarded percent completions plus three guarded calculator-answer completions. Subtract, append/save, and document-word reporting have zero verified completions in all three arms; their shared failures do not explain the between-arm gap. Seven task types and three repeats are exploratory coverage, not a broad product benchmark.

## Findings that change the interpretation

### 1. Append-and-save is a correctness failure, not just an overly strict verifier

`native.py` implements `type` with `set_value`, which replaces the text. All six measured S1/dual append runs first replace `First line.` with `Second line.`. The predicate in `evals/native/tasks/dev.yaml` only requires the file to contain the latter string. It therefore passes loss of the original content. Four sampled `done` rows are wrong with full same-run evidence, even though the original packets cannot establish the starting document contents.

Preserve the original contents and line boundaries, distinguish replace from append, and assert the exact final file contents. Verify saving separately where the task requires an explicit save. An oracle passing a weak predicate does not validate that predicate. Do not relax the verifier to accept these corrupted end states.

### 2. Native authorization covers clicks better than equivalent keyboard actions

`desktop_s2.py` routes `key` and `hotkey` directly to the bridge without calling `gate`; menu actions use a keyword check rather than the full click judgment. A fake bridge confirms that command-delete can dispatch with a deliberately denying gate installed: gate call count is zero. This demonstrates a missing guard boundary, not that a real file was deleted.

The semantic click classifier also returns allow when its judgment raises an exception. A fake exception reproduces this behavior. Candidate labels and broad substring authorization are not sufficient capability scopes for native effects. Every action route must resolve to an effect and resource scope before dispatch, including Enter, keyboard shortcuts, menu invocation, and text replacement. Classifier unavailability needs an explicit safe outcome. Consent tests should test equivalent actions through every route before adding Finder or Mail workflows.

### 3. Annotation evidence loses information the agent actually had

`build_label_packets.py` retains controls but omits native window static text, including Calculator displays. The trace writer also omits that page text and the initial document baseline. Native `_write` does not populate S1 `proposed`, so native input packets have `<needs value>` even for executed inputs. Prior action strings discard effects and prefer labels over typed values. Failed attempts can look like completed steps.

The web packet shows several stale URL/menu combinations. Identical Add to cart labels lose explicit product association. Password values must remain hidden, but a safe `has_value` flag would make readiness judgeable. Preserve redacted pre-action observations, typed action arguments, operation semantics, associations, snapshot/run identity, and prior effect outcomes. Keep future outcomes hidden during decision annotation.

### 4. The audit tools cannot currently be used as advertised for native repeats

`show_row.py` searches only the web packet directory and expects the older four-part key. `audit_agreement.py` keys by run/task/arm/step and omits `run_id`: the native full table has 176 key collisions. The comparison in this review uses full run identity instead.

`evals.annotation` scans all trace files and collapses result rows by task/arm. Six labelled rows come from `textedit-append-and-save-dual-62ccb520`, which is absent from the 63-row measured result manifest. Keep exploratory/aborted attempts explicitly separate; join measured annotations to exact trace identities. Do not silently let directory contents define the evaluation population.

### 5. Confidence discrimination is promising; calibration transfer remains unproven

Recomputed on existing agreed model labels, without changing any labels:

- Overall target AUROC: **0.899**, 184 target-bearing labelled rows.
- Preregistered click-only target AUROC: **0.888**, 171 labelled clicks.
- Percent-task target AUROC: **0.663**.
- Excluding percent: **0.953**; this does not mean a robust result, since the remaining target errors are concentrated in append/save controls.
- 43 of 70 wrong-labelled decisions come from percent (41 clicks plus two blocked decisions). All 31 excluded model disagreements come from that same task.
- A task-cluster bootstrap gives an exploratory target-AUROC interval of approximately **[0.797, 0.983]**; 3611/4000 draws contain both classes. Seven tasks still offer limited support.

AUROC measures ranking of right versus wrong, not whether a reported confidence corresponds to an empirical success probability. Actual calibration requires reliability analysis on an appropriate outcome, preferably by operation and task family. Likewise, a target-threshold false-escalation rate does not measure the complete arbiter, whose operation floor, nouls and other rules also escalate.

Both original labellers saw the confidence and probability alternatives being evaluated. That is a potential source of label bias. Agreement between two passes of the same model is not independent validation. Hide confidence, routing reasons and model verdicts in the next semantic-label packet. Evaluate on unseen task families and bootstrap by task/run. Report undecidable and disagreement coverage rather than deleting it from the headline without sensitivity analysis.

### 6. The percent disagreement is not a single yes/no question

Starting with 15 is not inherently wrong: multiplication permits either operand order, and a path such as 15 times 240 followed by Percent can satisfy the task. The exact behavior of Percent and Clear depends on the observed Calculator state, which the packets omit. Some disputed rows are straightforward operand prefixes; others are resets, discarded valid digits, or partially corrupted sequences. The supplemental CSV adjudicates each separately: 16 right, six wrong, nine unclear. Platform-specific percent semantics remain unverified by this offline review.

Do not automatically label every deviation from the oracle key order wrong. Conversely, mathematical commutativity does not make an arbitrary key sequence valid. A state-transition fixture should cover both legitimate operand orders and the missing-multiplication failure.

## Recommended next sequence

1. **Repair the evidence and task contracts.** Exact append preservation; typed replace/append semantics; full pre-action observations; separately recorded S1 proposals; stable run joins; safe password occupancy; explicit partial/unknown state. Acceptance: the actual overwritten-document trace fails the strengthened predicate, and every sampled decision can be reconstructed or explicitly marked insufficient.
2. **Complete one shared native dispatch guard.** Apply resource/effect authorization to clicks, keys, hotkeys, Enter, menus, and replacements. Exercise denial, classifier failure, stale state and post-action uncertainty with offline fakes and scratch-app tests. No real user files or accounts are needed.
3. **Repair the annotation protocol and regenerate packets.** Hide the evaluated scores; split target correctness, value correctness and completion; include observation effects; separate exploratory traces. Reuse the AI audit to identify ambiguity, not to claim human validation or overwrite ground truth.
4. **Run a narrow amended Q10b.** Preserve Q10 as historical. First diagnose oracle end states against the verifier. Then compare guarded and dual on corrected tasks with fixed budgets, counterbalanced order and explicit application mode/reset. Add genuinely unseen task variants; report result correctness, verifier acceptance, policy compliance, pauses, cost and latency separately. Freeze thresholds before the untouched validation set.
5. **Expand native scope only after those gates.** Prefer scratch TextEdit/Calculator/Finder workflows with exact checks. Keep app coverage, alternative S1 models and GUI benchmark comparisons behind the correctness work. The shared contract should separate observations, typed effects, authorization and evidence; the browser and desktop adapters need not share every loop implementation.

The useful S1 goal is selective execution of cheap, local, well-observed decisions. S2 should own task interpretation, text transformations, recovery and changes of strategy. A stalled S1 sequence should trigger a bounded S2 repair with a progress condition before S1 resumes. The optimization target is end-to-end cost and time per correctly completed authorized task, not the share of steps assigned to S1.

## Validation and reproduction

Focused offline suites: 95 tests passed across native, desktop, desktop S2, policy, S1 and arbiter; another eight native-runner tests passed. These tests coexist with the reproduced guard gaps and do not certify native safety. No source behavior was changed, no paid inference was run, and no live desktop action was performed. Existing unrelated worktree changes were preserved.

From `jevdual`:

```sh
python3 results/annotation/secondary-audit-20260924/write_audit.py
PYTHONPATH=. .venv/bin/python results/annotation/secondary-audit-20260924/analyze.py
PYTHONPATH=. .venv/bin/python results/annotation/secondary-audit-20260924/probes.py
```

The original 80 annotations are frozen separately from later evidence-enriched adjudications. They are reviewer judgments with stated evidence limits, not a replacement benchmark truth set.
