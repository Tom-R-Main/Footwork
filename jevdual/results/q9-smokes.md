# Q9 smokes: guarded, delegate and delegate+evidence on six live-dev tasks, 2026-09-21

Quick checks of the Q9 arms before the pre-registered run (`docs/experiments/Q9.md`). Six tasks:
two sign-ins, a cart flow, a form submit, a Wikipedia chain, a docs read. Stock and dual rows are
the same tasks from the post-ledger live run for reference. All numbers observed from
`delegate-smoke-20260921-221133` (no System 2 guidance) and `delegate-smoke2-20260921-222726` (guidance via the system-message
extension, commit 5eb4aaa).

| arm | pass | steps | LLM calls | Jev calls | est. cost USD | delegations | reached |
|---|---|---|---|---|---|---|---|
| stock (reference) | 6/6 | 25 | 25 | 0 | 0.037 | | |
| guarded | 5/6 | 24 | 24 | 7 | 0.039 | | |
| dual (reference) | 5/6 | 30 | 20 | 42 | 0.044 | | |
| delegate, no guidance | 5/6 | 20 | 20 | 7 | 0.035 | 0 | |
| delegate, guided | 5/6 | 40 | 30 | 31 | 0.055 | 6 | 1 |
| delegate+evidence, guided | 5/6 | 39 | 27 | 35 | 0.055 | 6 | 3 |

## What the smokes showed

1. **Without guidance Muse never delegates.** The tool alone, with its description, was not enough;
   the delegate arm was the guarded arm under another name.
2. **With guidance it delegates on five of six tasks**, 12 delegations in all: 4 reached with observed
   support (both sign-ins in 2 to 3 S1 steps, the docs search), 2 stuck, 1 no-effect, 2 paused by the
   gate inside the delegation, and the Wikipedia chain where S1 claimed done on the search page and
   the subgoal check refused it (p 0.14 to 0.19), after which System 2 finished the task itself.
3. **The guard alone is cheap.** Four to seven verification calls per six tasks put the guarded arm
   at stock's cost with the gate and verification in place. On this sample S1 acting, reactive or
   delegated, added Jev calls without adding passes. That is the branch of Q9 the guarded arm exists
   to expose; six tasks cannot decide it.
4. **Evidence selection worked once** (lru_cache: three spans, answer present 0.91, task passed) and
   was not called on the other read task.
5. **`ls-add-backpack-cart` fails for every arm tonight**, including System 2 alone, after passing in
   the morning; it is the site, and it will be paired across arms in the full run.

## Decision

Run Q9 as pre-registered on the full live-dev set with the four arms (guarded, dual, delegate,
delegate+evidence), same code, same evening, judge verdicts recorded. The interesting outcome is
already visible in miniature: the question is not whether S1 can act but whether its acting pays
for itself over the guard.
