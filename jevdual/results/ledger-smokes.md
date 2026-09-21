# Ledger smokes on live-dev (dual arm, six tasks each), 2026-09-21

Quick checks of the trajectory ledger (commit 2f601c0) and the widened accept band (06a5b60) before
the paired three-arm rerun. Both ran while repeat 1 was running on the same machine, so wall times
are inflated. All numbers observed from the run directories.

| run | change under test | pass | paused | verified accepts | S2 rejections | S1 done vetoes | UNVERIFIED dones |
|---|---|---|---|---|---|---|---|
| `ledger-smoke-20260921-141456` | ledger on, old band (complete ≥ 0.85, unmet ≤ 0.20) | 4/6 | 2 | 0 | 6 | 18 | 6 of 6 |
| `ledger-smoke2-20260921-145439` | ledger on, widened band (complete ≥ 0.80, unmet ≤ 0.30) | 5/6 | 1 | 4 | 2 | 8 | 2 of 6 |
| `ledger-smoke3-20260921-151528` | as above plus outcome-phrased requirements; six answer-heavy tasks | 5/6 | 0 | 4 | 2 | 7 | 1 of 5 verified runs (cart task hit max steps) |
| `ledger-smoke4-20260921-155234` | as above plus full-text claim checks and an evidence-centred excerpt (a9a4287); six long-page answer tasks | 6/6 | 0 | 6 | 0 | 13 | 0 of 6 |

Run 0 on the first smoke's six tasks: 25 rejections, every run UNVERIFIED.

## What each smoke showed

1. **Ledger, old band.** Per-requirement rejections on actions no longer visible: 0 of 24 (run 0:
   120 of 224). The ledger carried met requirements forward 37 times. But every remaining rejection
   was the uncertain band with unmet at 0.22 to 0.30 and complete at 0.84 to 0.91 on runs whose
   predicate passed: the accept band, a conjunction over all requirements at 0.20 each, was the
   next wall.
2. **Ledger, widened band.** Four of six runs verified and accepted in two to four steps
   (li-login-success 2 steps, ls-login-inventory 4, both Wikipedia chains 4), judge agreeing on all
   four. The answer task `lw-pydocs-keyerror` stayed UNVERIFIED for a task-wording reason: its
   requirement "Docs searched" was judged unmet (p 0.61 to 0.69) because the agent navigated to the
   exceptions page without using search, which the task never needed. Sixteen live tasks phrased
   an incidental process as a requirement ("Searched Wikipedia", "MDN searched", "PyPI searched");
   all are now outcome phrased on both live files (heldout had never been run). The DuckDuckGo tasks
   keep "Search submitted" because the task demands it and a checkpoint grades it.
3. **`ls-add-backpack-cart` failed in both smokes** after passing run 0: S1's first step typed the
   product name into the username field (the literal text source picked task text for an input),
   System 2 then signed in, and four clicks on the same element produced no visible change, S1
   escalated on no-effect and stuck, and System 2 reached for `evaluate`, which the gate refuses.
   Inferred: the repeated no-effect click is flakiness under load; the first-step text choice is an
   S1 defect worth its own dev task; the `evaluate` refusal is the Q8 consent class (Siftable a140b874).

4. **Outcome-phrased requirements, answer tasks.** Four of five answer tasks verified and accepted
   (Wikipedia creator 3 steps, RFC 2 steps, MDN font-weight 4, PyPI licence 6). `lw-pydocs-keyerror`
   stayed UNVERIFIED with a correct answer: on the long exceptions page the verifier's page text is
   the first 6,000 characters of the DOM text, and the claim check ran against the same window, so
   "KeyError" was an unsupported claim and `complete` sat at 0.36 to 0.42. Fix in progress: claim
   checks run on the full page text and the verifier's excerpt is centred on the answer's evidence.
   `ls-add-backpack-cart` ran to max steps (3 S1 / 22 S2) without a done: the same no-effect clicks
   as before, now without an `evaluate` pause.

5. **Evidence-centred excerpt, long pages.** Six of six verified and accepted, judge agreeing on all
   six; zero System 2 rejections and zero UNVERIFIED dones. The Python exceptions task went from 12
   steps UNVERIFIED to 7 steps verified. The 13 S1 vetoes are S1's own `done` proposals refused
   because S1 cannot compose an answer, which is the intended division of labour and costs one Jev
   call each. What remains is one or more "uncertain" verdicts before the accept on some tasks
   (complete 0.53 to 0.83 with max unmet just above 0.30); that is Q3's threshold question, left
   for the labelled trajectories rather than tuned here.

## Not yet measured

The paired three-arm rerun after repeat 1 is the measurement; these smokes only say the mechanism
moves the right numbers on the tasks that motivated it.
