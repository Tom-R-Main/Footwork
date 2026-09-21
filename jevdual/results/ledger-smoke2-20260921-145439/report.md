# live-dev split, arms dual

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dual | 6 | 5 | 83% | 0 | 1 | 5.8 | 23 | 50 | 347292 | 0.0642 | 1143 | 0 |

## Judge (upstream judge prompt, run by the System 2 model)

Predicate-graded rows: agreement, false accepts (judge yes, predicate no) and false rejects (judge no, predicate yes). Rows graded by the judge alone are counted separately.

| arm | judged | judge pass | agree | false accept | false reject | captcha | impossible | graded by judge |
|---|---|---|---|---|---|---|---|---|
| dual | 6 | 5 | 6 | 0 | 0 | 0 | 0 | 0 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|
| li-login-success | dual | yes | predicate | yes | 2 | 1/1 | 0.0022 | 52 |  |
| ls-add-backpack-cart | dual | no | predicate | no | 8 | 2/6 | 0.0112 | 245 |  |
| ls-login-inventory | dual | yes | predicate | yes | 4 | 3/1 | 0.0034 | 48 |  |
| lw-chain-austen-year | dual | yes | predicate | yes | 4 | 3/1 | 0.0079 | 128 |  |
| lw-chain-python-guido | dual | yes | predicate | yes | 4 | 3/1 | 0.0098 | 173 |  |
| lw-pydocs-keyerror | dual | yes | predicate | yes | 13 | 0/13 | 0.0298 | 497 |  |
