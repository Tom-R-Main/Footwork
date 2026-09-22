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

| arm | pass | verified | est. cost USD | wall s | LLM calls | Jev calls | assignments | reached |
|---|---|---|---|---|---|---|---|---|
| guarded (q9b, 11 of the 12) | 10/11 | 7 | 0.065 | 906 | 38 | 19 | | |
| dual (q9b, 11 of the 12) | 10/11 | 8 | 0.069 | 722 | 26 | 72 | | |
| delegate v3 (q9c, 11 of the 12) | 11/11 | 7 | 0.093 | 1,316 | 56 | 53 | | |
| delegate with fixes (this smoke) | 12/12 | 7 | 0.094 | 1,064 | 49 | 70 | 10 | 2 |

The fixes removed the two defect classes they targeted: no assignment was paused by the gate and
none looped on a retyped value. Reach did not move: 2 of 10. The remaining closings are 5
"not reached" where the subgoal verification sat in the uncertain band on pages that were plainly
signed in (complete 0.45 to 0.81, one at 0.79 against the 0.80 floor), 2 sign-ins handed back on a
collapsed target head (0.05 and 0.31 on the username field), 1 stuck form. Cost stayed 40% above
guarded and dual on these tasks.

Reading: with the instrument coherent and its defects fixed, delegation on live pages is limited
by two things the loop structure cannot change: the executor's target grounding on forms, and the
verifier's confidence on multi-step state. Both are calibration questions (Q1, Q3) that need the
labelled steps and trajectories, and moving the 0.80 floor to fit this smoke would be exactly the
tuning the program forbids. Q9's decision stands: reactive loop by default, delegation a tool.
