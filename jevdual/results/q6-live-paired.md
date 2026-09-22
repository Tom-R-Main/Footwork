# Live-dev, three arms, after the verification changes (run `live-dev-post-ledger-20260921-182626`)

The measurement the program asked for after the trajectory ledger (Q6 Amendment 2 and 3). Same 55
live-dev tasks as validation run 0, all three arms, frozen arbiter, judge verdict recorded per row.
"After" includes the verifier changes (ledger 2f601c0, widened band 06a5b60, full-text claim checks
and evidence excerpt a9a4287) and the task-file fixes (two defects, sixteen outcome-phrased
requirements); the confound is stated in Q6.md. All numbers observed from the run directory;
paired tables are `paired-*.md` there, produced by `evals.paired` (paired bootstrap 95% intervals).

| arm | pass | false done | paused | mean steps | LLM calls | Jev calls | est. cost USD | wall s | crashes |
|---|---|---|---|---|---|---|---|---|---|
| s1_only | 13/55 | 23 | 0 | 8.0 | 0 | 427 | 0.192 | 787 | 0 |
| stock (Muse Spark 1.3 Contributor) | 50/55 | 1 (see note) | 0 | 4.8 | 265 | 0 | 0.382 | 5,508 | 0 |
| dual (Jev + Muse) | 50/55 | 0 (see note) | 2 | 5.9 | 196 | 458 | 0.504 | 6,158 | 0 |

Note on "false done": the report counts 2 for stock and 1 for dual, but two of those three are
`lw-ddg-python-pathlib`, where the DuckDuckGo checkpoint I added after run 0 was wrong
(`duckduckgo.com/?q=` never matches the real query URL `duckduckgo.com/?ia=web&…&q=`); both arms
visited the query page and opened docs.python.org, so both are passes under the corrected
checkpoint (fixed in this commit). The one real false done is stock on `lw-chain-rust-hoare`: it
stopped on the Rust article and reported success; the judge accepted it too. Corrected pass counts:
stock 51/55 with 1 false done, dual 51/55 with 0.

## Dual before and after, paired on 55 tasks (`paired-dual-before-after.md`)

| field | run 0 | after | mean per task | 95% CI | tasks better / worse |
|---|---|---|---|---|---|
| UNVERIFIED dones | 43 | 9 | −0.62 | [−0.76, −0.47] | 36 / 2 |
| Jev calls | 613 | 458 | −2.8 | [−3.9, −1.7] | 38 / 11 |
| est. cost USD | 0.627 | 0.504 | −0.002 | [−0.004, −0.001] | 37 / 18 |
| LLM calls | 232 | 196 | −0.66 | [−1.40, +0.16] | 33 / 12 |
| steps | 343 | 322 | −0.38 | [−1.15, +0.47] | 32 / 11 |
| wall s | 5,538 | 6,158 | +11 | [−15, +39] | 31 / 24 |
| passed | 52 | 50 (51 corrected) | −0.04 | [−0.13, +0.04] | 2 / 4 |

Done rejections fell from 224 to 105 (System 2: 89 → 28; S1 vetoes: 135 → 77). The class the ledger
targeted, requirements judged on the final page, went from 120 to 4. What remains is the uncertain
band (64 of 105) and S1's own answer-less dones on answer tasks (14), which are cheap and correct.

## Drift control: stock before and after (`paired-stock-drift.md`)

Stock lost 5 passes (55 → 50) and 22 s per task of wall time (CI excludes 0) with no code change
on its side. The losses are all saucedemo checkout tasks that ran to the step limit at "Checkout:
Your Information" in the evening runs, on both arms; run 0 passed them in the morning. Inferred: the
site or the headless form behaviour changed, not the agents. It means dual's wall-time increase is
environmental (dual +11 s per task, stock +22 s), and the pass comparison is against a moving site.

## Stock versus dual, same run (`paired-stock-vs-dual.md`)

| field | stock | dual | mean per task | 95% CI |
|---|---|---|---|---|
| passed | 50 | 50 | 0 | [−0.07, +0.07] |
| LLM calls | 265 | 196 | −1.26 | [−2.46, −0.27] |
| Jev calls | 0 | 458 | +8.3 | |
| est. cost USD | 0.382 | 0.504 | +0.002 | [+0.001, +0.004] |
| wall s | 5,508 | 6,158 | +12 | [−11, +38] |

Dual now makes 26% fewer LLM calls than stock at 1.32× its estimated cost (run 0: 4% more calls at
1.84×). The whole remaining gap is Jev volume: 458 calls, /bin/zsh.146. Wall time is not distinguishable.

## Judge against predicates (Q3's first data)

| arm | judged | agree | judge false accept | judge false reject |
|---|---|---|---|---|
| dual | 54 | 53 | 1 (the checkpoint defect above) | 0 |
| stock | 55 | 53 | 2 (one is the real false done) | 0 |

The judge, run by the same model as System 2, accepted stock's one wrong completion. Zero false
rejects on either arm; its agreement with dual's own success report is 51 of 54.

## Q6 read

Escalation from S1-eligible steps: 190 of 309 (61%; run 0 69%; fixture 58%). Op confidence below
0.95 on 65% of steps (fixture 28%); below 0.55 on 43. S1-only on live: 13 of 55 with 23 false
dones, against 10 of 23 on the fixture. The direction of Q6 holds on both live runs; calibration
still needs the labels.

## Misses (dual)

- `ls-add-backpack-cart`, `ls-checkout-total`: paused on System 2's `evaluate` after no-effect
  clicks on saucedemo (Q8 consent class, Siftable a140b874; S1 text-source defect 99ad9646).
- `ls-order-backpack-authorized`, `ls-order-jacket-authorized`: step limit at checkout, same
  saucedemo behaviour that took stock's three.
- `lw-ddg-python-pathlib`: checkpoint defect, a pass once corrected.

## Decision

Adopt: the ledger, the widened band and the evidence excerpt stay in the default. Fixture heldout
rerun once on adoption (program rule) follows this commit. Next tranche is Jev call economy:
the 458 calls are now the entire cost gap.
