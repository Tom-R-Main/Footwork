# native dev split, arms dual, guarded

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dual | 3 | 3 | 100% | 0 | 0 | 4.0 | 6 | 22 | 7715 | 0.0022 | 76 | 0 |
| guarded | 3 | 3 | 100% | 0 | 0 | 4.3 | 13 | 4 | 15485 | 0.0025 | 109 | 0 |

## Outcomes (external success and claimed completion kept apart)

| arm | verified pass (passed and claimed) | unclaimed pass (passed, UNVERIFIED or paused) | false done | model requests (tracker) | evaluate refusals | cost per verified pass |
|---|---|---|---|---|---|---|
| dual | 3 | 0 | 0 | 0 | 0 | 0.0007 |
| guarded | 3 | 0 | 0 | 0 | 0 | 0.0008 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | deleg. | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|---|
| textedit-append-line | dual | yes | predicate | - | 3 | 2/1 | 0/0 | 0.0004 | 12 |  |
| textedit-append-line | dual | yes | predicate | - | 4 | 2/2 | 0/0 | 0.0007 | 25 |  |
| textedit-append-line | dual | yes | predicate | - | 5 | 2/3 | 0/0 | 0.0011 | 39 |  |
| textedit-append-line | guarded | yes | predicate | - | 6 | 0/6 | 0/0 | 0.0013 | 53 |  |
| textedit-append-line | guarded | yes | predicate | - | 4 | 0/4 | 0/0 | 0.0007 | 35 |  |
| textedit-append-line | guarded | yes | predicate | - | 3 | 0/3 | 0/0 | 0.0005 | 21 |  |
