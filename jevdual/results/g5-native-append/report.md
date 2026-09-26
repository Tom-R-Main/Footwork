# native dev split, arms dual, guarded

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dual | 3 | 3 | 100% | 0 | 0 | 3.7 | 5 | 17 | 6177 | 0.0018 | 59 | 0 |
| guarded | 3 | 3 | 100% | 0 | 0 | 5.3 | 16 | 5 | 21197 | 0.0035 | 146 | 0 |

## Outcomes (external success and claimed completion kept apart)

| arm | verified pass (passed and claimed) | unclaimed pass (passed, UNVERIFIED or paused) | false done | model requests (tracker) | evaluate refusals | cost per verified pass |
|---|---|---|---|---|---|---|
| dual | 3 | 0 | 0 | 0 | 0 | 0.0006 |
| guarded | 3 | 0 | 0 | 0 | 0 | 0.0012 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | deleg. | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|---|
| textedit-append-line | dual | yes | predicate | - | 3 | 2/1 | 0/0 | 0.0004 | 13 |  |
| textedit-append-line | dual | yes | predicate | - | 4 | 2/2 | 0/0 | 0.0007 | 21 |  |
| textedit-append-line | dual | yes | predicate | - | 4 | 2/2 | 0/0 | 0.0007 | 24 |  |
| textedit-append-line | guarded | yes | predicate | - | 3 | 0/3 | 0/0 | 0.0005 | 21 |  |
| textedit-append-line | guarded | yes | predicate | - | 7 | 0/7 | 0/0 | 0.0016 | 68 |  |
| textedit-append-line | guarded | yes | predicate | - | 6 | 0/6 | 0/0 | 0.0013 | 56 |  |
