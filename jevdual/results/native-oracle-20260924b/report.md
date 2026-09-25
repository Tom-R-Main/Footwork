# native dev split, arms oracle

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| s1_only | 6 | 5 | 83% | 0 | 0 | 5.5 | 0 | 0 | 0 | 0.0000 | 65 | 0 |

## Outcomes (external success and claimed completion kept apart)

| arm | verified pass (passed and claimed) | unclaimed pass (passed, UNVERIFIED or paused) | false done | model requests (tracker) | evaluate refusals | cost per verified pass |
|---|---|---|---|---|---|---|
| s1_only | 0 | 5 | 0 | 0 | 0 | 0.0000 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | deleg. | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|---|
| calc-multiply | s1_only | yes | predicate | - | 7 | 0/0 | 0/0 | 0.0000 | 13 |  |
| calc-percent | s1_only | yes | predicate | - | 9 | 0/0 | 0/0 | 0.0000 | 15 |  |
| calc-read-result | s1_only | yes | predicate | - | 6 | 0/0 | 0/0 | 0.0000 | 11 |  |
| calc-subtract | s1_only | yes | predicate | - | 8 | 0/0 | 0/0 | 0.0000 | 14 |  |
| textedit-append-line | s1_only | no | predicate | - | 2 | 0/0 | 0/0 | 0.0000 | 7 |  |
| textedit-type-sentence | s1_only | yes | predicate | - | 1 | 0/0 | 0/0 | 0.0000 | 6 |  |
