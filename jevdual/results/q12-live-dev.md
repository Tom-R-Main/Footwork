# Q12 result: receipts cut repeated no-op clicks, not the work per unit of progress (2026-09-26)

Pre-registration: `docs/experiments/Q12.md` (95f22d5, launch note ace4de8). Runs
`results/q12-live-dev-r1`, `-r2`, `-r3` on d23d0f3, task-major with both arms interleaved, pooled in
`results/q12-live-dev-pooled` (354 rows, no error rows). Tools: `evals.paired ... --arm
guarded_receipts --vs guarded`, `evals.burden ... --vs guarded`, `evals.rejections --arm`.

## Headline

Per run, 59 tasks, repeats averaged over three runs:

| arm | verified | predicate passes | UNVERIFIED | paused | false completions | driver requests | steps | no-op receipts | cost USD |
|---|---|---|---|---|---|---|---|---|---|
| guarded | 40.3 | 51.0 | 9.3 | 9.3 | 0 | 266.0 | 241.7 | 63.3 | 0.393 |
| guarded_receipts | 39.0 | 51.0 | 10.7 | 9.3 | 0 | 253.7 | 227.0 | 52.0 | 0.372 |

Paired against `guarded`, per task, 95% bootstrap intervals:

| Δ per task | guarded_receipts |
|---|---|
| requests per unit of progress (primary, 53 tasks with checkpoints) | −0.02 [−0.14, +0.10] |
| driver requests | −0.21 [−0.42, −0.02] |
| steps | −0.25 [−0.51, +0.01] |
| no-op receipts | −0.19 [−0.37, −0.02] |
| verified passes | −0.02 [−0.06, +0.02] |
| refused dones | +0.05 [−0.05, +0.15] |

By terminal mode (runs, mean requests): `done_claimed` 121 at 3.8 against 117 at 3.6; `unverified`
28 at 6.7 against 32 at 6.5; `paused` 28 at 5.6 against 28 at 4.5. No run on either arm hit the step
cap.

## Against the pre-registration

- **H1 not supported.** The primary, requests per unit of progress, did not move: −0.02 with the
  interval centred on zero. Raw requests fell about 5% and steps about the same, both at the edge
  of their intervals, and repeated no-op clicks fell 18%.
- **H0(b) is the outcome.** The pause count is identical (28 per arm: 21 `evaluate`, 6 "Submit
  order", 1 "Finish"), but the paused runs cost fewer requests (5.6 to 4.5). The driver read the
  receipt and reached for page script sooner; the run ended the same way, earlier. On saucedemo
  requests fell from 207 to 185 pooled and no-op receipts from 88 to 60, verified passes 9 to 8. No
  route around the dead click exists, so a receipt can only shorten the way to the same failure.
- **Guardrails.** False completions 0 on both arms. No unauthorized run on either arm reached a
  committing URL (every pooled trace checked). Verified passes 121 against 117 pooled, −4, which
  breaches the pre-registered −2 while the paired interval includes zero; the nine tasks that lost
  a run and the five that gained one are scattered across sites with no pattern. No-fact refusals
  44 against 49: the silent arm's runs spread 13 to 16, the receipt arm's 12, 15, 22, one run above
  the spread. Neither excursion is a story the traces tell; both are reported.
- **False-receipt audit.** 156 `suspected_noop` receipts on the receipt arm; on 6 the next step
  landed on a different URL, an upper bound on receipts that called a late navigation "no change".
  The rest concentrate on docs pages (`lw-pydocs-keyerror` 14, `lw-ddg-mdn-fetch` 12) where an
  in-page anchor or a scroll changes nothing the diff measures; those receipts are literally true
  and useless, and a receipt that named the scroll position or the focused heading would not be.

## Decision

Per the H0(b) branch: receipts are kept, recorded on every System 2 arm and delivered on the
receipt arm, and not claimed as a burden reduction; the default guarded configuration is unchanged.
Next is P2: fix the trusted-input loss after navigation (exf 9b9916a6), then Q12b re-measures the
same two arms, since a receipt helps only where another route exists. Two receipt changes go in
before that: a click receipt on a page that did not navigate names what did change (scroll,
focus, an expanded section) instead of "no change", and the type receipt already names the field's
value (6d71222). The measurement correction from Q11 held up: raw requests moved, requests per
progress did not, and the terminal-mode table is what showed why.
