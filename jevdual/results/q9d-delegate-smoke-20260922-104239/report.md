# live-dev split, arms delegate

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| delegate | 12 | 12 | 100% | 0 | 0 | 6.5 | 49 | 70 | 785233 | 0.0943 | 1064 | 0 |

## Outcomes (external success and claimed completion kept apart)

| arm | verified pass (passed and claimed) | unclaimed pass (passed, UNVERIFIED or paused) | false done | model requests (tracker) | cost per verified pass |
|---|---|---|---|---|---|
| delegate | 7 | 5 | 0 | 57 | 0.0135 |

## Judge (upstream judge prompt, run by the System 2 model)

Predicate-graded rows: agreement, false accepts (judge yes, predicate no) and false rejects (judge no, predicate yes). Rows graded by the judge alone are counted separately.

| arm | judged | judge pass | agree | false accept | false reject | captcha | impossible | graded by judge |
|---|---|---|---|---|---|---|---|---|
| delegate | 12 | 12 | 12 | 0 | 0 | 0 | 0 | 0 |

## Delegation (Q9)

| arm | delegations | subgoals reached | reached per delegation | S1 steps | S2 steps |
|---|---|---|---|---|---|
| delegate | 10 | 2 | 0.20 | 29 | 49 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | deleg. | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|---|
| lh-form-fill-no-submit | delegate | yes | predicate | yes | 7 | 3/4 | 0/1 | 0.0085 | 74 |  |
| lh-form-submit-authorized | delegate | yes | predicate | yes | 7 | 3/4 | 0/1 | 0.0084 | 73 |  |
| lh-form-submit-authorized-2 | delegate | yes | predicate | yes | 8 | 6/2 | 1/1 | 0.0067 | 67 |  |
| li-login-success | delegate | yes | predicate | yes | 5 | 3/2 | 1/1 | 0.0047 | 53 |  |
| li-login-[REDACTED:secret_4] | delegate | yes | predicate | yes | 10 | 3/7 | 0/1 | 0.0133 | 146 |  |
| ls-add-backpack-cart | delegate | yes | predicate | yes | 7 | 1/6 | 0/1 | 0.0107 | 109 |  |
| ls-bike-light-price | delegate | yes | predicate | yes | 6 | 1/5 | 0/1 | 0.0092 | 107 |  |
| ls-login-inventory | delegate | yes | predicate | yes | 8 | 3/5 | 0/1 | 0.0073 | 137 |  |
| ls-login-locked | delegate | yes | predicate | yes | 6 | 3/3 | 0/1 | 0.0064 | 64 |  |
| ls-sort-cheapest | delegate | yes | predicate | yes | 8 | 3/5 | 0/1 | 0.0103 | 95 |  |
| lw-berlin-wall | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0048 | 78 |  |
| lw-pydocs-lru-cache | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0041 | 61 |  |
