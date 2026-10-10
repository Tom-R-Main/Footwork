# Q12b result: the input fix did the work; receipts lowered requests per progress and cost verified passes (2026-09-26)

Pre-registration: `docs/experiments/Q12b.md` (c33890a, amendment 2a9c763). Runs `results/q12b-live-dev-r1`,
`-r2`, `-r3` on 2a9c763, launched in parallel (arms interleaved task by task within each run), pooled in
`results/q12b-live-dev-pooled` (354 rows, no error rows). Tools: `evals.paired`, `evals.burden`,
`evals.rejections --arm`.

## Headline

| pooled, 177 runs per arm | verified | predicate passes | UNVERIFIED | paused | false completions | driver requests | no-fact refusals |
|---|---|---|---|---|---|---|---|
| guarded | 137 | 172 | 26 | 14 | 0 | 802 | 50 |
| guarded_receipts | 133 | 175 | 32 | 12 | 0 | 794 | 67 |

Paired against `guarded`, per task, 95% bootstrap intervals: requests per unit of progress (primary, 59
of 59 tasks with progress in both arms) −0.28 [−0.69, −0.01]; raw driver requests −0.05 [−0.19,
+0.10]; verified passes −0.02 [−0.09, +0.05]; predicate passes +0.02 [0.00, +0.05].

## Against the pre-registration

- **The primary moved**, its interval just below zero: receipts lowered requests per unit of progress,
  which Q12 did not (−0.02 [−0.14, +0.10]). Raw requests did not move.
- **Guardrails breached: H0(c) is the outcome by the rule as written.** Verified passes −4 pooled
  (−2 allowed), as in Q12; no-fact refusals 67 against 50, with receipt-arm runs at 18, 21, 28 against
  the silent arm's 14 to 19. Only 3 of 354 final done texts quote a receipt, so quoting is not the
  mechanism; the visible done texts narrate their process ("Steps verified in this session: ..."),
  which the claim check cannot match. This build did not record refused done texts, so the mechanism
  is inferred, not observed (package E's build records them).
- **`undelivered_inputs` was not zero**, and the guardrail found a false receipt: every
  `ls-sort-cheapest` run on both arms has one `not_delivered` receipt on `select_dropdown`, which sets
  the value by script and changed the page. The probe counted only untrusted clicks as script
  delivery. No input was lost; the receipt was wrong, and on the receipt arm the verifier's line
  carried `input: not_delivered` for a sort that happened. Fixed after this run (untrusted events of
  any kind read `by_script`).
- False completions 0 on both arms; no unauthorized run reached a committing URL; every saucedemo
  pause (12, 6 per arm) is on `ls-order-backpack-unauthorized` or `ls-order-jacket-unauthorized`.
- Expectation written before the run, H0(a), was wrong: the primary moved, and the cost fell on
  verification, not on work.

## What the input fix did (descriptive; Q12 and Q12b are different days, not paired)

| `guarded`, pooled | verified | predicate passes | saucedemo verified | saucedemo paused |
|---|---|---|---|---|
| Q12 (d23d0f3) | 121 | 153 | 9 of 36 | 22 |
| Q12b (2a9c763) | 137 | 172 | 22 of 36 | 6 |

Q12's no-op receipts (63 per run on `guarded`) fell to under one per run, most from package C (dead
saucedemo clicks) and the rest from not issuing receipts for read-only steps (amendment); the two are
not separable here.

## Decision

H0(c), per the rule: receipts are not adopted as the default on the driver's side; the silent arm stays
the baseline, and receipts stay recorded (they, and the delivery field, are how C's lost input and this
run's false `not_delivered` were found). Before any rerun: fix the delivery probe (done), and measure
receipts again only on the claim check package E settles in Q16, since the verified-pass cost runs
through no-fact refusals, the check Q16 changes. L2 gains no burden claim; L3 is confirmed: the route
fix (package C) moved verified passes by 16 pooled, more than any declaration or receipt has.
