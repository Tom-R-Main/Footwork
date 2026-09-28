# native dev split, arms s1_only, dual, guarded, bounded

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bounded | 1 | 1 | 100% | 0 | 0 | 8.0 | 7 | 2 | 10810 | 0.0014 | 31 | 0 |
| dual | 1 | 1 | 100% | 0 | 0 | 8.0 | 0 | 9 | 0 | 0.0012 | 14 | 0 |
| guarded | 1 | 1 | 100% | 0 | 0 | 8.0 | 8 | 1 | 11612 | 0.0014 | 30 | 0 |
| s1_only | 2 | 2 | 100% | 0 | 0 | 8.5 | 0 | 19 | 0 | 0.0025 | 31 | 0 |

## Outcomes (external success and claimed completion kept apart)

| arm | verified pass (passed and claimed) | unclaimed pass (passed, UNVERIFIED or paused) | false done | model requests (tracker) | evaluate refusals | cost per verified pass |
|---|---|---|---|---|---|---|
| bounded | 1 | 0 | 0 | 0 | 0 | 0.0014 |
| dual | 1 | 0 | 0 | 0 | 0 | 0.0012 |
| guarded | 1 | 0 | 0 | 0 | 0 | 0.0014 |
| s1_only | 2 | 0 | 0 | 0 | 0 | 0.0013 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | deleg. | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|---|
| calc-multiply | bounded | yes | predicate | - | 8 | 1/7 | 0/0 | 0.0014 | 31 |  |
| calc-multiply | dual | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 14 |  |
| calc-multiply | guarded | yes | predicate | - | 8 | 0/8 | 0/0 | 0.0014 | 30 |  |
| calc-multiply | s1_only | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 15 |  |
| calc-subtract | s1_only | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0013 | 16 |  |
