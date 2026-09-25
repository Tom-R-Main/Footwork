# live-dev split, arms guarded, guarded_receipts

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| guarded | 2 | 1 | 50% | 0 | 1 | 4.0 | 8 | 6 | 135575 | 0.0148 | 158 | 0 |
| guarded_receipts | 2 | 1 | 50% | 0 | 1 | 4.0 | 8 | 5 | 124204 | 0.0137 | 199 | 0 |

## Outcomes (external success and claimed completion kept apart)

| arm | verified pass (passed and claimed) | unclaimed pass (passed, UNVERIFIED or paused) | false done | model requests (tracker) | evaluate refusals | cost per verified pass |
|---|---|---|---|---|---|---|
| guarded | 1 | 0 | 0 | 10 | 0 | 0.0148 |
| guarded_receipts | 1 | 0 | 0 | 9 | 0 | 0.0137 |

## Judge (upstream judge prompt, run by the System 2 model)

Predicate-graded rows: agreement, false accepts (judge yes, predicate no) and false rejects (judge no, predicate yes). Rows graded by the judge alone are counted separately.

| arm | judged | judge pass | agree | false accept | false reject | captcha | impossible | graded by judge |
|---|---|---|---|---|---|---|---|---|
| guarded | 2 | 1 | 2 | 0 | 0 | 0 | 0 | 0 |
| guarded_receipts | 2 | 1 | 2 | 0 | 0 | 0 | 0 | 0 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | deleg. | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|---|
| ls-add-backpack-cart | guarded | no | predicate | no | 5 | 0/5 | 0/0 | 0.0087 | 104 |  |
| ls-add-backpack-cart | guarded_receipts | no | predicate | no | 5 | 0/5 | 0/0 | 0.0070 | 111 |  |
| lw-chain-dune-herbert | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0061 | 53 |  |
| lw-chain-dune-herbert | guarded_receipts | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0067 | 88 |  |
