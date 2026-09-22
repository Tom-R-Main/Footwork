# live-dev split, arms guarded, delegate

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| delegate | 6 | 5 | 83% | 0 | 1 | 3.3 | 20 | 7 | 313756 | 0.0345 | 394 | 0 |
| guarded | 6 | 5 | 83% | 0 | 1 | 4.0 | 24 | 7 | 357897 | 0.0394 | 518 | 0 |

## Judge (upstream judge prompt, run by the System 2 model)

Predicate-graded rows: agreement, false accepts (judge yes, predicate no) and false rejects (judge no, predicate yes). Rows graded by the judge alone are counted separately.

| arm | judged | judge pass | agree | false accept | false reject | captcha | impossible | graded by judge |
|---|---|---|---|---|---|---|---|---|
| delegate | 6 | 5 | 6 | 0 | 0 | 0 | 0 | 0 |
| guarded | 6 | 5 | 6 | 0 | 0 | 0 | 0 | 0 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | deleg. | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|---|
| lh-form-submit-authorized | delegate | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0067 | 60 |  |
| lh-form-submit-authorized | guarded | yes | predicate | yes | 6 | 0/6 | 0/0 | 0.0098 | 107 |  |
| li-login-success | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0052 | 64 |  |
| li-login-success | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0032 | 31 |  |
| ls-add-backpack-cart | delegate | no | predicate | no | 5 | 0/5 | 0/0 | 0.0082 | 84 |  |
| ls-add-backpack-cart | guarded | no | predicate | no | 6 | 0/6 | 0/0 | 0.0103 | 165 |  |
| ls-login-inventory | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0036 | 40 |  |
| ls-login-inventory | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0039 | 82 |  |
| lw-chain-python-guido | delegate | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0066 | 89 |  |
| lw-chain-python-guido | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0063 | 62 |  |
| lw-pydocs-lru-cache | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0041 | 59 |  |
| lw-pydocs-lru-cache | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0058 | 71 |  |
