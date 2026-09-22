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
