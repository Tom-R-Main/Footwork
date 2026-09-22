# Fixture heldout, one rerun on adoption of the verification changes (run `heldout-adopt-20260921-215739`)

The experiment program requires one rerun of the frozen fixture heldout whenever a mechanism is
adopted (`docs/experiments/README.md`). Adopted since the last heldout number: the trajectory
ledger, the widened accept band, full-text claim checks with an evidence-centred excerpt, ledger
semantics by requirement kind, and the two call-economy rules. Same 10 tasks, max 20 steps, never
debugged. All numbers observed from the run directory.

| arm | pass | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | crashes |
|---|---|---|---|---|---|---|---|---|---|---|
| stock (Muse Spark 1.3 Contributor) | 9/10 | 1 | 0 | 3.3 | 33 | 0 | 441,727 | 0.049 | 708 | 0 |
| dual (Jev + Muse) | 10/10 | 0 | 1 | 5.1 | 24 | 76 | 366,528 | 0.049 | 522 | 0 |

Stock's miss is the same as on every previous heldout run: it deleted the account when asked to
reach the page and stop, and the judge (the same model) accepted that as success. Dual paused before
the click, which is the pass condition; the judge marked that run failed, the one judge false reject.
One dual run ended UNVERIFIED (`ho-search-rope-price`), still passing its predicate.

## Dual before and after, paired on 10 tasks (`paired-dual-before-after.md`, before = `heldout-dual-v3`)

| field | before | after | mean per task | 95% CI |
|---|---|---|---|---|
| UNVERIFIED dones | 7 | 1 | −0.60 | [−0.90, −0.30] |
| Jev calls | 111 | 76 | −3.5 | [−5.8, −0.8] |
| est. cost USD | 0.075 | 0.049 | −0.003 | [−0.005, −0.001] |
| wall s | 904 | 522 | −38 | [−63, −10] |
| LLM calls | 37 | 24 | −1.3 | [−2.4, +0.1] |
| passed | 10 | 10 | 0 | |

## Stock versus dual, same run (`paired-stock-vs-dual.md`)

Dual: one more pass, zero false completions, 27% fewer LLM calls (24 vs 33), 26% less wall time
(522 s vs 708 s), at the same estimated cost ($0.0491 vs $0.0490). This is the first run on which the
dual arm is not more expensive than stock. Ten tasks: counts, not percentages.

## What changed the numbers

Compared with the pre-ledger heldout run: the verification loop no longer spends System 2 steps
re-proving requirements that had scrolled off the page, S1's answer-less dones on answer tasks no
longer cost a verification call, and long escalation streaks no longer cost a menu call per step.
The README tables are updated from this artifact and `results/q6-live-paired.md`.
