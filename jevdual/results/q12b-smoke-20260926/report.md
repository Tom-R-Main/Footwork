# live-dev split, arms guarded, guarded_receipts

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| guarded | 2 | 2 | 100% | 0 | 0 | 6.5 | 13 | 6 | 217619 | 0.0242 | 191 | 0 |
| guarded_receipts | 2 | 2 | 100% | 0 | 0 | 6.0 | 12 | 8 | 188858 | 0.0209 | 138 | 0 |

## Outcomes (external success and claimed completion kept apart)

| arm | verified pass (passed and claimed) | unclaimed pass (passed, UNVERIFIED or paused) | false done | model requests (tracker) | evaluate refusals | cost per verified pass |
|---|---|---|---|---|---|---|
| guarded | 1 | 1 | 0 | 15 | 0 | 0.0242 |
| guarded_receipts | 0 | 2 | 0 | 14 | 0 | 0.0000 |

## Judge (upstream judge prompt, run by the System 2 model)

Predicate-graded rows: agreement, false accepts (judge yes, predicate no) and false rejects (judge no, predicate yes). Rows graded by the judge alone are counted separately.

| arm | judged | judge pass | agree | false accept | false reject | captcha | impossible | graded by judge |
|---|---|---|---|---|---|---|---|---|
| guarded | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| guarded_receipts | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | deleg. | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|---|
| ls-add-backpack-cart | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0061 | 53 |  |
| ls-add-backpack-cart | guarded_receipts | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0081 | 60 |  |
| lw-pydocs-keyerror | guarded | yes | predicate | yes | 10 | 0/10 | 0/0 | 0.0182 | 138 |  |
| lw-pydocs-keyerror | guarded_receipts | yes | predicate | yes | 7 | 0/7 | 0/0 | 0.0128 | 79 |  |
