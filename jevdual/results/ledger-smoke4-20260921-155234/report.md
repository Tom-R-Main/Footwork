# live-dev split, arms dual

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dual | 6 | 6 | 100% | 0 | 0 | 5.2 | 28 | 50 | 305578 | 0.0716 | 1775 | 0 |

## Judge (upstream judge prompt, run by the System 2 model)

Predicate-graded rows: agreement, false accepts (judge yes, predicate no) and false rejects (judge no, predicate yes). Rows graded by the judge alone are counted separately.

| arm | judged | judge pass | agree | false accept | false reject | captcha | impossible | graded by judge |
|---|---|---|---|---|---|---|---|---|
| dual | 6 | 6 | 6 | 0 | 0 | 0 | 0 | 0 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|
| lw-arxiv-attention-title | dual | yes | predicate | yes | 3 | 0/3 | 0.0091 | 171 |  |
| lw-github-browser-use-license | dual | yes | predicate | yes | 5 | 0/5 | 0.0151 | 487 |  |
| lw-gutenberg-pride | dual | yes | predicate | yes | 2 | 1/1 | 0.0036 | 70 |  |
| lw-mdn-418 | dual | yes | predicate | yes | 9 | 0/9 | 0.0212 | 459 |  |
| lw-pydocs-keyerror | dual | yes | predicate | yes | 7 | 0/7 | 0.0157 | 450 |  |
| lw-rfc-8259-format | dual | yes | predicate | yes | 5 | 2/3 | 0.0068 | 139 |  |
