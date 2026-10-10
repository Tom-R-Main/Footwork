# live-dev split, arms guarded, guarded_evidence

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| guarded | 3 | 3 | 100% | 0 | 0 | 4.7 | 14 | 10 | 200515 | 0.0232 | 236 | 0 |
| guarded_evidence | 3 | 3 | 100% | 0 | 0 | 3.0 | 9 | 6 | 133316 | 0.0158 | 196 | 0 |

## Outcomes (external success and claimed completion kept apart)

| arm | verified pass (passed and claimed) | unclaimed pass (passed, UNVERIFIED or paused) | false done | model requests (tracker) | evaluate refusals | cost per verified pass |
|---|---|---|---|---|---|---|
| guarded | 0 | 3 | 0 | 16 | 0 | 0.0000 |
| guarded_evidence | 2 | 1 | 0 | 11 | 0 | 0.0079 |

## Judge (upstream judge prompt, run by the System 2 model)

Predicate-graded rows: agreement, false accepts (judge yes, predicate no) and false rejects (judge no, predicate yes). Rows graded by the judge alone are counted separately.

| arm | judged | judge pass | agree | false accept | false reject | captcha | impossible | graded by judge |
|---|---|---|---|---|---|---|---|---|
| guarded | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 0 |
| guarded_evidence | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 0 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | deleg. | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|---|
| lh-form-fill-no-submit | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0071 | 71 |  |
| lh-form-fill-no-submit | guarded_evidence | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0043 | 56 |  |
| li-key-press | guarded | yes | predicate | yes | 6 | 0/6 | 0/0 | 0.0087 | 109 |  |
| li-key-press | guarded_evidence | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0034 | 62 |  |
| ls-bike-light-price | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0073 | 55 |  |
| ls-bike-light-price | guarded_evidence | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0080 | 77 |  |
