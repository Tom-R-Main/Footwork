# Q9: four arms on live-dev, first delegation build (run `q9-live-dev-20260921-225012`)

Pre-registration: `docs/experiments/Q9.md` (702fd84). Arms: `guarded` (System 2 behind the gate and
done verification, no S1 decisions), `dual` (reactive S1 first), `delegate` (System 2 hands bounded
subgoals to S1 via `delegate_subgoal`), `delegate_evidence` (plus `find_evidence`). Same 55 tasks,
same code (c75b5fe..5eb4aaa; the coherent-delegation build 65da803 landed after launch and is not
in this run), same night, judge verdicts recorded. All numbers observed from the run directory;
paired tables are `paired-*.md` there.

## Arms

| arm | predicate pass | verified pass (claimed) | unclaimed pass | false done | paused | LLM calls | Jev calls | est. cost USD | cost per verified pass | wall s |
|---|---|---|---|---|---|---|---|---|---|---|
| guarded | 50/55 | 41 | 9 | 0 | 2 | 260 | 80 | 0.412 | 0.0100 | 4,877 |
| dual | 51/55 | 42 | 9 | 0 | 2 | 193 | 391 | 0.492 | 0.0117 | 4,702 |
| delegate | 52/55 | 42 | 10 | 0 | 2 | 278 | 290 | 0.577 | 0.0137 | 5,242 |
| delegate_evidence | 49/55 | 43 | 6 | 0 | 3 | 300 | 321 | 0.604 | 0.0140 | 5,997 |

Judge (same model as System 2) agrees with the predicate on 54 of 55 rows for every arm. Zero false
completions on every arm; every unauthorised destructive action paused.

## Paired against guarded, 55 tasks (95% intervals on the per-task mean)

| arm | passed | steps | LLM calls | Jev calls | cost | wall s |
|---|---|---|---|---|---|---|
| dual | +0.02 [0, +0.06] | +1.0 [+0.4, +1.7] | −1.2 [−1.7, −0.7] | +5.7 [+4.5, +6.9] | +0.001 [+0.001, +0.002] | −3 [−13, +9] |
| delegate | +0.04 [0, +0.09] | +1.8 [+1.3, +2.4] | +0.3 [−0.1, +0.8] | +3.8 [+3.0, +4.7] | +0.003 [+0.002, +0.004] | +7 [−6, +19] |
| delegate_evidence | −0.02 [−0.06, 0] | +2.4 [+1.8, +3.0] | +0.7 [+0.2, +1.3] | +4.4 [+3.5, +5.3] | +0.003 [+0.002, +0.005] | +20 [+7, +33] |

Delegate against dual: passes +0.02 [0, +0.06]; LLM calls +1.5 [+0.9, +2.1] per task; cost +0.002
[0, +0.003]; wall +10 [−8, +25].

## Delegation outcomes (first build)

| arm | started | reached | stuck | no effect | paused by gate | blocked | never closed | reached with 0 S1 steps | mean S1 steps per reached |
|---|---|---|---|---|---|---|---|---|---|
| delegate | 51 | 19 | 9 | 6 | 5 | 1 | 11 | 2 | 1.8 |
| delegate_evidence | 52 | 22 | 14 | 4 | 6 | 2 | 4 | 2 | 1.8 |

"Never closed" are assignments still open when the task ended: in this build an S1 done without
observed support escalated the step to System 2 while the assignment stayed active, so System 2
finished the task inside someone else's assignment. Those, and the two zero-step "reached" per
arm, are the hybrid-loop defect the review named; the coherent build (65da803) closes every
assignment with a status. `find_evidence` was called 16 times across 55 tasks.

Recovery attribution for the 32 delegate assignments that did not reach: 9 stuck (S1 repeating an
action without page change), 6 no effect (clicks that changed nothing, mostly saucedemo's cart
tonight), 5 paused by the gate inside the assignment, 1 blocked, 11 never closed. None was a wrong
completion.

## Misses

Every arm lost the same saucedemo tasks: two cart tasks paused on `evaluate` after no-effect clicks,
two order tasks at the step limit on "Checkout: Your Information". System 2 alone (guarded) loses
them too, so it is the site tonight, not S1. `lw-chain-rust-hoare` (guarded, delegate_evidence)
ended UNVERIFIED on the Rust article; `lw-pydocs-keyerror` (delegate_evidence) paused on
`evaluate`.

## Verdict under the pre-registered rule

- (a) verified completions: delegate 42, dual 42, guarded 41; intervals on passes touch 0. Met.
- (b) cost per verified completion ≤ 0.8 × dual: delegate 1.17 × dual. **Falsified.**
- (c) completed subgoals per System 2 intervention ≥ 1.5: 0.37 reached per delegation, and the
  one-subgoal tool caps the ratio at 1 by construction. **Falsified as written; the denominator
  was wrong** (review), so the number to carry is 19 reached of 51 started.
- Evidence arm: System 2 tokens 4.42M against delegate's 4.33M, not ≤ 0.7×; passes within 2.
  **Falsified.**
- Discriminating branch: guarded matches every arm on completions within the intervals at the
  lowest cost. **Applies.** Dual keeps two real, smaller advantages: 26% fewer LLM calls than
  guarded (interval excluding 0) and the fewest steps of any S1 arm; wall time is not
  distinguishable between any pair except delegate_evidence, which is slower.

Decision: the reactive loop stays the default configuration; delegation remains a tool System 2
may call; the evidence tool stays available but off by default. The README claim becomes: zero
false completions and a destructive gate at guarded's cost, with S1's per-step speed reported as a
per-step number. The next measurement is the coherent delegation build against guarded and dual on
the same tasks, which tests whether the instrument or the idea produced this result.
