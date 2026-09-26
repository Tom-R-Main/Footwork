# Q17 result: native recovery ownership is money against time, not calls (2026-09-26)

Pre-registration: `docs/experiments/Q17.md` (4c17b45). Run: `results/q17-native-dev` on 4c17b45, native
dev split (7 tasks), three arms, three repeats, the desktop cleared by the owner. Verified completion
is the pre-registered one: predicate passed and done accepted (no error row). The runner's own
`report.md` prints 0 verified passes on every arm because it reads a `success` field native rows do not
set; that column is wrong and is not used here.

| arm | verified | cost USD | cost per verified | wall s per verified | System 2 calls | Jev calls |
|---|---|---|---|---|---|---|
| s1_only (floor) | 9 of 18 | 0.0138 | 0.00154 | 22.5 | 0 | 108 |
| dual | 15 of 18 | 0.0284 | 0.00189 | 37.2 | 36 | 181 |
| guarded | 15 of 18 | 0.0264 | 0.00176 | 53.9 | 137 | 21 |

Paired by task (7 tasks, repeats averaged), Δ(guarded − dual) with 95% bootstrap intervals: cost per
task −$0.0001 [−0.0005, +0.0002]; wall per task +13.9 s [+8.6, +19.1].

## Against the pre-registration

- **H1 not supported.** `guarded` is 7% cheaper per verified task, but the paired interval on cost
  includes zero.
- **H0(b) is the outcome.** Cost within 10%; `dual` is 31% faster per verified task, the interval
  excluding zero. System 1's fast steps on Calculator are where the time goes.
- The old reading (36 against 137 System 2 calls) would have called `dual` a large saving; on cost it
  is not one.
- **Guardrails.** No false completion, no pause, no unauthorized action on any arm. All six failures
  on `dual` and `guarded` are the same task, `textedit-append-line`: the predicate passed, and the
  verifier stayed uncertain (complete 0.75 to 0.83, max unmet 0.36 to 0.51) until the refusal budget
  ended the run, on work the append's exact readback had confirmed. That is the verifier-evidence gap
  package E names, on the native side: the verifier does not read the receipt's readback.

## Decision

Per the H0(b) branch: both arms stay, and the choice between them is per task, money against time.
System 2 call counts are not reported as a saving again. Next on this path: the native verifier reads
the append's and save's readback receipts as typed evidence (the `textedit-append-line` failures), and
the native report's verified column is fixed.
