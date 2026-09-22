# live-dev split, arms delegate, delegate_evidence

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| delegate | 6 | 5 | 83% | 0 | 1 | 6.7 | 30 | 31 | 439000 | 0.0547 | 690 | 0 |
| delegate_evidence | 6 | 5 | 83% | 0 | 1 | 6.5 | 27 | 35 | 414959 | 0.0551 | 606 | 0 |

## Judge (upstream judge prompt, run by the System 2 model)

Predicate-graded rows: agreement, false accepts (judge yes, predicate no) and false rejects (judge no, predicate yes). Rows graded by the judge alone are counted separately.

| arm | judged | judge pass | agree | false accept | false reject | captcha | impossible | graded by judge |
|---|---|---|---|---|---|---|---|---|
| delegate | 6 | 5 | 6 | 0 | 0 | 0 | 0 | 0 |
| delegate_evidence | 6 | 5 | 6 | 0 | 0 | 0 | 0 | 0 |

## Delegation (Q9)

| arm | delegations | subgoals reached | reached per delegation | S1 steps | S2 steps |
|---|---|---|---|---|---|
| delegate | 6 | 1 | 0.17 | 10 | 30 |
| delegate_evidence | 6 | 3 | 0.50 | 12 | 27 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | deleg. | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|---|
| lh-form-submit-authorized | delegate | yes | predicate | yes | 6 | 0/6 | 0/1 | 0.0104 | 109 |  |
| lh-form-submit-authorized | delegate_evidence | yes | predicate | yes | 4 | 0/4 | 0/1 | 0.0071 | 74 |  |
| li-login-success | delegate | yes | predicate | yes | 5 | 2/3 | 1/1 | 0.0061 | 70 |  |
| li-login-success | delegate_evidence | yes | predicate | yes | 5 | 3/2 | 1/1 | 0.0049 | 64 |  |
| ls-add-backpack-cart | delegate | no | predicate | no | 11 | 4/7 | 0/2 | 0.0122 | 138 |  |
| ls-add-backpack-cart | delegate_evidence | no | predicate | no | 11 | 3/8 | 0/1 | 0.0128 | 130 |  |
| ls-login-inventory | delegate | yes | predicate | yes | 5 | 2/3 | 0/1 | 0.0066 | 110 |  |
| ls-login-inventory | delegate_evidence | yes | predicate | yes | 6 | 3/3 | 1/1 | 0.0059 | 100 |  |
| lw-chain-python-guido | delegate | yes | predicate | yes | 6 | 2/4 | 0/1 | 0.0111 | 98 |  |
| lw-chain-python-guido | delegate_evidence | yes | predicate | yes | 5 | 2/3 | 0/1 | 0.0108 | 69 |  |
| lw-pydocs-lru-cache | delegate | yes | predicate | yes | 7 | 0/7 | 0/0 | 0.0081 | 164 |  |
| lw-pydocs-lru-cache | delegate_evidence | yes | predicate | yes | 8 | 1/7 | 1/1 | 0.0137 | 169 |  |
