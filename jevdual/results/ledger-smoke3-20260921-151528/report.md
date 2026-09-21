# live-dev split, arms dual

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dual | 6 | 5 | 83% | 0 | 0 | 8.8 | 43 | 66 | 492974 | 0.0811 | 1987 | 0 |

## Judge (upstream judge prompt, run by the System 2 model)

Predicate-graded rows: agreement, false accepts (judge yes, predicate no) and false rejects (judge no, predicate yes). Rows graded by the judge alone are counted separately.

| arm | judged | judge pass | agree | false accept | false reject | captcha | impossible | graded by judge |
|---|---|---|---|---|---|---|---|---|
| dual | 5 | 5 | 5 | 0 | 0 | 1 | 0 | 0 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|
| ls-add-backpack-cart | dual | no | predicate | - | 26 | 3/22 | 0.0237 | 889 |  |
| lw-mdn-font-weight | dual | yes | predicate | yes | 4 | 1/3 | 0.0091 | 193 |  |
| lw-pydocs-keyerror | dual | yes | predicate | yes | 12 | 0/12 | 0.0292 | 450 |  |
| lw-pypi-requests-license | dual | yes | predicate | yes | 6 | 2/4 | 0.0070 | 307 |  |
| lw-python-creator | dual | yes | predicate | yes | 3 | 2/1 | 0.0084 | 96 |  |
| lw-rfc-9110 | dual | yes | predicate | yes | 2 | 1/1 | 0.0037 | 51 |  |
