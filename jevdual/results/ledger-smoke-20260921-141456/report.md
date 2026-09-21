# live-dev split, arms dual

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dual | 6 | 4 | 67% | 0 | 2 | 8.7 | 43 | 79 | 516866 | 0.0832 | 2223 | 0 |

## Judge (upstream judge prompt, run by the System 2 model)

Predicate-graded rows: agreement, false accepts (judge yes, predicate no) and false rejects (judge no, predicate yes). Rows graded by the judge alone are counted separately.

| arm | judged | judge pass | agree | false accept | false reject | captcha | impossible | graded by judge |
|---|---|---|---|---|---|---|---|---|
| dual | 6 | 3 | 5 | 0 | 1 | 1 | 0 | 0 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|
| li-login-success | dual | yes | predicate | yes | 5 | 2/3 | 0.0051 | 157 |  |
| ls-add-backpack-cart | dual | no | predicate | no | 9 | 2/7 | 0.0127 | 313 |  |
| ls-checkout-total | dual | no | predicate | no | 7 | 1/6 | 0.0110 | 228 |  |
| ls-login-inventory | dual | yes | predicate | yes | 8 | 0/8 | 0.0107 | 524 |  |
| lw-chain-python-guido | dual | yes | predicate | yes | 8 | 2/6 | 0.0216 | 281 |  |
| lw-ddg-mdn-fetch | dual | yes | predicate | no | 15 | 1/13 | 0.0221 | 719 |  |
