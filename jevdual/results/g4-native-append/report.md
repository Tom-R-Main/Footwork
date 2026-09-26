# native dev split, arms dual, guarded

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dual | 3 | 0 | 0% | 0 | 0 | 25.0 | 75 | 75 | 145370 | 0.0278 | 1288 | 3 |
| guarded | 3 | 0 | 0% | 0 | 0 | 25.0 | 75 | 0 | 134618 | 0.0207 | 1193 | 3 |

## Outcomes (external success and claimed completion kept apart)

| arm | verified pass (passed and claimed) | unclaimed pass (passed, UNVERIFIED or paused) | false done | model requests (tracker) | evaluate refusals | cost per verified pass |
|---|---|---|---|---|---|---|
| dual | 0 | 0 | 0 | 0 | 0 | 0.0000 |
| guarded | 0 | 0 | 0 | 0 | 0 | 0.0000 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | deleg. | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|---|
| textedit-append-line | dual | no | predicate | - | 25 | 0/25 | 0/0 | 0.0093 | 399 | budget_exhausted: 25 steps |
| textedit-append-line | dual | no | predicate | - | 25 | 0/25 | 0/0 | 0.0095 | 527 | budget_exhausted: 25 steps |
| textedit-append-line | dual | no | predicate | - | 25 | 0/25 | 0/0 | 0.0089 | 362 | budget_exhausted: 25 steps |
| textedit-append-line | guarded | no | predicate | - | 25 | 0/25 | 0/0 | 0.0068 | 374 | budget_exhausted: 25 steps |
| textedit-append-line | guarded | no | predicate | - | 25 | 0/25 | 0/0 | 0.0067 | 370 | budget_exhausted: 25 steps |
| textedit-append-line | guarded | no | predicate | - | 25 | 0/25 | 0/0 | 0.0072 | 449 | budget_exhausted: 25 steps |
