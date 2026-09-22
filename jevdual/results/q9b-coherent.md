# Q9b: coherent delegation build, three arms on live-dev (run `q9b-coherent-20260922-050153`)

Intended as the measurement of the coherent delegation build (65da803) against guarded and dual.
It is not that: the delegate arm made **zero delegations** in 55 tasks, including both saucedemo
sign-ins, because the rewritten guidance ("do a single visible action yourself; delegate when it
would take two or more steps") tipped Muse into never delegating. The delegate row is therefore
the guarded loop with an unused tool, and the coherent build remains unmeasured. Guidance
rewritten again (48d1e27) to name the workflows to delegate first; the delegate-only run with it is
`q9c-delegate-*`. What this run does give is a second same-code sample of guarded against dual and a
drift control for the guarded arm across the night. All numbers observed from the run directory.

| arm | predicate pass | verified pass | false done | LLM calls | Jev calls | est. cost USD | cost per verified pass | wall s |
|---|---|---|---|---|---|---|---|---|
| guarded | 52/55 | 45 | 0 | 226 | 84 | 0.385 | 0.0086 | 4,789 |
| dual | 52/55 | 45 | 0 | 161 | 360 | 0.449 | 0.0100 | 4,386 |
| delegate (0 delegations) | 50/55 | 43 | 0 | 237 | 80 | 0.384 | 0.0089 | 4,815 |

## Dual against guarded, paired on 55 tasks (`paired-guarded-vs-dual.md`)

| field | mean per task | 95% CI |
|---|---|---|
| passed | 0 | [−0.06, +0.06] |
| LLM calls | −1.18 | [−1.62, −0.69] |
| Jev calls | +5.0 | [+4.1, +6.0] |
| cost | +0.001 | [0, +0.002] |
| wall s | −7 | [−21, +9] |

Same shape as the first Q9 run: equal completions, 29% fewer LLM calls, 16% higher cost, wall time
not distinguishable. Two same-night samples now agree.

## Drift control: guarded across the two runs (`paired-guarded-drift.md`)

Passes 50 → 52, steps −0.6 per task [−1.4, −0.1], cost unchanged, wall unchanged. The site was
slightly kinder in the morning; nothing that changes the comparison.
