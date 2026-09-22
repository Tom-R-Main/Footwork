# Q9c: coherent delegation build, corrected guidance, delegate arm alone (run `q9c-delegate-20260922-085642`)

The measurement Q9b was meant to be. Build 65da803 (subgoal-scoped questions, ownership transfer on
any unresolved verdict, per-assignment accounting) with guidance 48d1e27 (delegate sign-in, forms,
cart, search-then-open first; single visible clicks stay with the driver). Paired against the
same-day guarded and dual rows of `q9b-coherent-20260922-050153`. All numbers observed.

| arm | predicate pass | verified pass | false done | LLM calls | Jev calls | est. cost USD | cost per verified pass | wall s |
|---|---|---|---|---|---|---|---|---|
| guarded (q9b) | 52/55 | 45 | 0 | 226 | 84 | 0.385 | 0.0086 | 4,789 |
| dual (q9b) | 52/55 | 45 | 0 | 161 | 360 | 0.449 | 0.0100 | 4,386 |
| delegate v3 (this run) | 50/55 | 44 | 0 | 276 | 166 | 0.473 | 0.0107 | 5,999 |

Paired, per task, 95% intervals (`paired-*-q9b-vs-delegate-v3.md`):

| against | passed | LLM calls | Jev calls | cost | wall s |
|---|---|---|---|---|---|
| guarded | −0.04 [−0.13, +0.06] | +0.9 [+0.2, +1.8] | +1.5 [+0.9, +2.2] | +0.002 [+0.001, +0.003] | +22 [+5, +41] |
| dual | −0.04 [−0.13, +0.06] | +2.1 [+1.3, +3.1] | −3.5 [−4.6, −2.5] | 0 [−0.001, +0.002] | +29 [+7, +53] |

## Assignments

30 delegations on 26 tasks, every one closed with a status: 5 reached, 9 stuck, 8 handed back on
low operation confidence, 5 paused by the gate inside the assignment, 3 not reached (S1 claimed
done, the stop-condition check refused). Mean S1 steps before closing: reached 1.8, stuck 2.2, low
confidence 1.4, not reached 2.7, gate 0. Of the 26 delegating tasks 22 passed, so System 2 finished
most of what the executor handed back.

Recovery attribution: the executor, not the assignment, is what fails. Stuck and low-confidence
handbacks are S1 unable to ground or progress the subgoal on the live page within two steps; the
driver then does the work it had tried to delegate, so the task pays both sides. Gate pauses inside
assignments are the Q8 consent classes (cart "Remove", `evaluate` is not S1's). Not-reached is the
stop-condition check doing its job.

## Verdict

With the instrument fixed, the result stands: coherent delegation completes no more tasks than
either baseline, costs 23% more than guarded and the same as dual, makes more LLM calls than both,
and is slower than both (intervals excluding 0 on cost against guarded and on wall time against
both). Its one advantage is 54% fewer Jev calls than the reactive loop. Q9's decision holds:
the reactive loop stays the default; delegation remains a tool. The reason is now specific: on
these live pages S1 reaches a bounded subgoal 5 times in 30, and a failed handoff costs the
driver's work plus the assignment's. Delegation cannot pay until the executor's reach rate is far
higher, which is Q1's calibration and grounding question, not a loop-structure question.

## Misses

`lw-chain-rust-hoare` (UNVERIFIED on the Rust article), the three saucedemo order tasks at the
checkout step (every arm, every run today), and `ls-cart-stop-unauthorized` paused by the gate
before its checkpoints (Q8).

## Q9d: executor fixes from these traces, smoke on the twelve tasks they came from (run `q9d-delegate-smoke-20260922-104239`)

Fixes (a4caad0): authorised tasks skip the arbiter's confirm rules; operation floor 0.45 inside an
assignment; the subgoal check runs through the done verification band with the trajectory; a field
already holding its known value is finished. Delegate arm alone on the twelve sign-in, form, cart
and search tasks; the other arms are the same tasks from the same-day runs.

| arm | predicate pass | passed and claimed | est. cost USD | wall s | assignments | reached |
|---|---|---|---|---|---|---|
| guarded (q9b) | 11/12 | 8 | 0.070 | 980 | | |
| dual (q9b) | 11/12 | 8 | 0.076 | 854 | | |
| delegate, coherent build (q9c) | 12/12 | 8 | 0.101 | 1,394 | | |
| delegate with fixes (this smoke) | 12/12 | 7 | 0.094 | 1,064 | 10 | 2 |

(Matched on all twelve tasks after restoring a task id the results redactor had rewritten; an
earlier version of this table matched only eleven. On the matched set the fixed build keeps the
coherent build's predicate passes, has one fewer passed-and-claimed completion, costs 34% more
than guarded and 25% more than dual, and is faster than the coherent build but slower than both
baselines. These are sequential development runs, not an isolation of each fix's effect.)

The fixes removed the two defect classes they targeted: no assignment was paused by the gate and
none looped on a retyped value. Reach did not move: 2 of 10. The remaining closings, re-read after an audit: 3 "not reached"
where the subgoal verification sat in the uncertain band on signed-in pages (complete 0.45 to 0.81,
one at 0.79 against the 0.80 floor); 1 "not reached" that was correct (the locked-out login's
expected error, judged not signed in); 1 "not reached" on a form filled but deliberately not
submitted; 2 sign-ins handed back on a collapsed target head after S1 had typed the product name
from the task text into the Username field (every assignment in this smoke carried empty
`known_values`, so the executor fell back to the task's quoted literal: a software defect, not a
confidence problem, fixed in the correctness tranche); 1 stuck form. Cost stayed 40% above
guarded and dual on these tasks.

Reading, corrected: this smoke does not show that only calibration remains. An audit found two
reproducible software defects behind the failures (values typed from the task literal when the
assignment supplied none; the two-stage target path discarding the first stage's confidence and
safety nouls) and three handback paths that left assignments open. Those are fixed in the
correctness tranche and need their own measurement before any calibration claim. The delegated
operation floor of 0.45 introduced here was an exploratory tuning change and is recorded as such.
Q9's decision stands on the measurements so far: reactive loop by default, delegation a tool.
