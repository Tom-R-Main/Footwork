# native dev split, arms s1_only, dual, guarded

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dual | 18 | 16 | 89% | 0 | 0 | 8.7 | 44 | 170 | 75633 | 0.0322 | 569 | 5 |
| guarded | 18 | 18 | 100% | 0 | 0 | 7.2 | 130 | 21 | 195432 | 0.0250 | 770 | 3 |
| s1_only | 18 | 12 | 67% | 0 | 0 | 5.3 | 0 | 105 | 0 | 0.0138 | 196 | 9 |

## Outcomes (external success and claimed completion kept apart)

| arm | verified pass (passed and claimed) | unclaimed pass (passed, UNVERIFIED or paused) | false done | model requests (tracker) | evaluate refusals | cost per verified pass |
|---|---|---|---|---|---|---|
| dual | 0 | 16 | 0 | 0 | 0 | 0.0000 |
| guarded | 0 | 18 | 0 | 0 | 0 | 0.0000 |
| s1_only | 0 | 12 | 0 | 0 | 0 | 0.0000 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | deleg. | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|---|
| calc-multiply | dual | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 15 |  |
| calc-multiply | dual | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 14 |  |
| calc-multiply | dual | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 14 |  |
| calc-multiply | guarded | yes | predicate | - | 8 | 0/8 | 0/0 | 0.0014 | 68 |  |
| calc-multiply | guarded | yes | predicate | - | 8 | 0/8 | 0/0 | 0.0014 | 33 |  |
| calc-multiply | guarded | yes | predicate | - | 8 | 0/8 | 0/0 | 0.0014 | 39 |  |
| calc-multiply | s1_only | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 15 |  |
| calc-multiply | s1_only | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 14 |  |
| calc-multiply | s1_only | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 14 |  |
| calc-percent | dual | no | predicate | - | 25 | 7/18 | 0/0 | 0.0082 | 153 | budget_exhausted: 25 steps |
| calc-percent | dual | yes | predicate | - | 14 | 11/3 | 0/0 | 0.0029 | 39 |  |
| calc-percent | dual | no | predicate | - | 25 | 17/8 | 0/0 | 0.0056 | 77 | budget_exhausted: 25 steps |
| calc-percent | guarded | yes | predicate | - | 10 | 0/10 | 0/0 | 0.0019 | 45 |  |
| calc-percent | guarded | yes | predicate | - | 10 | 0/10 | 0/0 | 0.0020 | 51 |  |
| calc-percent | guarded | yes | predicate | - | 10 | 0/10 | 0/0 | 0.0020 | 51 |  |
| calc-percent | s1_only | no | predicate | - | 4 | 4/0 | 0/0 | 0.0006 | 9 | escalated: target_confidence: target confidence 0.36 < 0.45 |
| calc-percent | s1_only | no | predicate | - | 3 | 3/0 | 0/0 | 0.0005 | 7 | escalated: target_confidence: target confidence 0.44 < 0.45 |
| calc-percent | s1_only | no | predicate | - | 5 | 5/0 | 0/0 | 0.0008 | 10 | escalated: target_confidence: target confidence 0.42 < 0.45 |
| calc-read-result | dual | yes | predicate | - | 6 | 5/1 | 0/0 | 0.0011 | 15 |  |
| calc-read-result | dual | yes | predicate | - | 7 | 5/2 | 0/0 | 0.0014 | 18 |  |
| calc-read-result | dual | yes | predicate | - | 6 | 5/1 | 0/0 | 0.0011 | 14 |  |
| calc-read-result | guarded | yes | predicate | - | 6 | 0/6 | 0/0 | 0.0010 | 28 |  |
| calc-read-result | guarded | yes | predicate | - | 6 | 0/6 | 0/0 | 0.0010 | 26 |  |
| calc-read-result | guarded | yes | predicate | - | 6 | 0/6 | 0/0 | 0.0011 | 23 |  |
| calc-read-result | s1_only | no | predicate | - | 6 | 6/0 | 0/0 | 0.0009 | 11 | escalated: done without an answer on an answer task; not ver |
| calc-read-result | s1_only | no | predicate | - | 6 | 6/0 | 0/0 | 0.0009 | 12 | escalated: done without an answer on an answer task; not ver |
| calc-read-result | s1_only | no | predicate | - | 6 | 6/0 | 0/0 | 0.0009 | 11 | escalated: done without an answer on an answer task; not ver |
| calc-subtract | dual | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0014 | 16 |  |
| calc-subtract | dual | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0014 | 16 |  |
| calc-subtract | dual | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0014 | 18 |  |
| calc-subtract | guarded | yes | predicate | - | 9 | 0/9 | 0/0 | 0.0016 | 38 |  |
| calc-subtract | guarded | yes | predicate | - | 9 | 0/9 | 0/0 | 0.0016 | 33 |  |
| calc-subtract | guarded | yes | predicate | - | 9 | 0/9 | 0/0 | 0.0016 | 51 |  |
| calc-subtract | s1_only | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0014 | 16 |  |
| calc-subtract | s1_only | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0014 | 16 |  |
| calc-subtract | s1_only | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0014 | 17 |  |
| textedit-append-line | dual | yes | predicate | - | 4 | 2/2 | 0/0 | 0.0007 | 28 | error: observation failed: Tool: tool='get_window_state', me |
| textedit-append-line | dual | yes | predicate | - | 6 | 2/4 | 0/0 | 0.0013 | 51 | error: observation failed: Tool: tool='get_window_state', me |
| textedit-append-line | dual | yes | predicate | - | 6 | 2/4 | 0/0 | 0.0012 | 48 | error: observation failed: Tool: tool='get_window_state', me |
| textedit-append-line | guarded | yes | predicate | - | 8 | 0/8 | 0/0 | 0.0019 | 82 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| textedit-append-line | guarded | yes | predicate | - | 10 | 0/10 | 0/0 | 0.0025 | 105 | error: s2 fatal: done refused 2 times; The document was save |
| textedit-append-line | guarded | yes | predicate | - | 7 | 0/7 | 0/0 | 0.0016 | 60 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| textedit-append-line | s1_only | yes | predicate | - | 3 | 3/0 | 0/0 | 0.0003 | 7 | blocked: blocked: no offered operation can make progress |
| textedit-append-line | s1_only | yes | predicate | - | 3 | 3/0 | 0/0 | 0.0003 | 7 | blocked: blocked: no offered operation can make progress |
| textedit-append-line | s1_only | yes | predicate | - | 3 | 3/0 | 0/0 | 0.0003 | 10 | blocked: blocked: no offered operation can make progress |
| textedit-type-sentence | dual | yes | predicate | - | 2 | 1/1 | 0/0 | 0.0003 | 21 |  |
| textedit-type-sentence | dual | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
| textedit-type-sentence | dual | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
| textedit-type-sentence | guarded | yes | predicate | - | 2 | 0/2 | 0/0 | 0.0003 | 11 |  |
| textedit-type-sentence | guarded | yes | predicate | - | 2 | 0/2 | 0/0 | 0.0003 | 15 |  |
| textedit-type-sentence | guarded | yes | predicate | - | 2 | 0/2 | 0/0 | 0.0003 | 10 |  |
| textedit-type-sentence | s1_only | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
| textedit-type-sentence | s1_only | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
| textedit-type-sentence | s1_only | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
