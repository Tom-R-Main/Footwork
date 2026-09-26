# native dev split, arms s1_only, dual, guarded

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dual | 18 | 18 | 100% | 0 | 0 | 8.0 | 36 | 181 | 62709 | 0.0284 | 558 | 3 |
| guarded | 18 | 18 | 100% | 0 | 0 | 7.6 | 137 | 21 | 205121 | 0.0264 | 808 | 3 |
| s1_only | 18 | 9 | 50% | 0 | 0 | 5.5 | 0 | 108 | 0 | 0.0138 | 202 | 9 |

## Outcomes (external success and claimed completion kept apart)

| arm | verified pass (passed and claimed) | unclaimed pass (passed, UNVERIFIED or paused) | false done | model requests (tracker) | evaluate refusals | cost per verified pass |
|---|---|---|---|---|---|---|
| dual | 0 | 18 | 0 | 0 | 0 | 0.0000 |
| guarded | 0 | 18 | 0 | 0 | 0 | 0.0000 |
| s1_only | 0 | 9 | 0 | 0 | 0 | 0.0000 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | deleg. | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|---|
| calc-multiply | dual | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 15 |  |
| calc-multiply | dual | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 15 |  |
| calc-multiply | dual | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 15 |  |
| calc-multiply | guarded | yes | predicate | - | 8 | 0/8 | 0/0 | 0.0014 | 34 |  |
| calc-multiply | guarded | yes | predicate | - | 8 | 0/8 | 0/0 | 0.0014 | 31 |  |
| calc-multiply | guarded | yes | predicate | - | 8 | 0/8 | 0/0 | 0.0014 | 31 |  |
| calc-multiply | s1_only | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 15 |  |
| calc-multiply | s1_only | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 15 |  |
| calc-multiply | s1_only | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 15 |  |
| calc-percent | dual | yes | predicate | - | 10 | 8/2 | 0/0 | 0.0020 | 32 |  |
| calc-percent | dual | yes | predicate | - | 22 | 11/11 | 0/0 | 0.0059 | 111 |  |
| calc-percent | dual | yes | predicate | - | 17 | 14/3 | 0/0 | 0.0032 | 42 |  |
| calc-percent | guarded | yes | predicate | - | 10 | 0/10 | 0/0 | 0.0020 | 54 |  |
| calc-percent | guarded | yes | predicate | - | 10 | 0/10 | 0/0 | 0.0020 | 55 |  |
| calc-percent | guarded | yes | predicate | - | 18 | 0/18 | 0/0 | 0.0038 | 149 |  |
| calc-percent | s1_only | no | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 15 | escalated: operation_confidence: operation confidence 0.54 < |
| calc-percent | s1_only | no | predicate | - | 4 | 4/0 | 0/0 | 0.0006 | 9 | escalated: target_confidence: target confidence 0.38 < 0.45 |
| calc-percent | s1_only | no | predicate | - | 6 | 6/0 | 0/0 | 0.0009 | 12 | escalated: target_confidence: target confidence 0.31 < 0.45 |
| calc-read-result | dual | yes | predicate | - | 7 | 5/2 | 0/0 | 0.0014 | 18 |  |
| calc-read-result | dual | yes | predicate | - | 6 | 5/1 | 0/0 | 0.0011 | 15 |  |
| calc-read-result | dual | yes | predicate | - | 6 | 5/1 | 0/0 | 0.0011 | 16 |  |
| calc-read-result | guarded | yes | predicate | - | 6 | 0/6 | 0/0 | 0.0010 | 23 |  |
| calc-read-result | guarded | yes | predicate | - | 6 | 0/6 | 0/0 | 0.0010 | 23 |  |
| calc-read-result | guarded | yes | predicate | - | 6 | 0/6 | 0/0 | 0.0010 | 26 |  |
| calc-read-result | s1_only | no | predicate | - | 6 | 6/0 | 0/0 | 0.0009 | 12 | escalated: done without an answer on an answer task; not ver |
| calc-read-result | s1_only | no | predicate | - | 6 | 6/0 | 0/0 | 0.0009 | 12 | escalated: done without an answer on an answer task; not ver |
| calc-read-result | s1_only | no | predicate | - | 6 | 6/0 | 0/0 | 0.0009 | 12 | escalated: done without an answer on an answer task; not ver |
| calc-subtract | dual | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0013 | 16 |  |
| calc-subtract | dual | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0013 | 16 |  |
| calc-subtract | dual | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0013 | 16 |  |
| calc-subtract | guarded | yes | predicate | - | 9 | 0/9 | 0/0 | 0.0015 | 35 |  |
| calc-subtract | guarded | yes | predicate | - | 9 | 0/9 | 0/0 | 0.0016 | 34 |  |
| calc-subtract | guarded | yes | predicate | - | 9 | 0/9 | 0/0 | 0.0016 | 34 |  |
| calc-subtract | s1_only | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0013 | 17 |  |
| calc-subtract | s1_only | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0013 | 17 |  |
| calc-subtract | s1_only | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0013 | 17 |  |
| textedit-append-line | dual | yes | predicate | - | 5 | 1/4 | 0/0 | 0.0014 | 48 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| textedit-append-line | dual | yes | predicate | - | 7 | 1/6 | 0/0 | 0.0021 | 75 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| textedit-append-line | dual | yes | predicate | - | 7 | 1/6 | 0/0 | 0.0022 | 90 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| textedit-append-line | guarded | yes | predicate | - | 8 | 0/8 | 0/0 | 0.0018 | 77 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| textedit-append-line | guarded | yes | predicate | - | 10 | 0/10 | 0/0 | 0.0025 | 116 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| textedit-append-line | guarded | yes | predicate | - | 6 | 0/6 | 0/0 | 0.0014 | 57 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| textedit-append-line | s1_only | no | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 8 | blocked: blocked: no offered operation can make progress |
| textedit-append-line | s1_only | no | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 5 | blocked: blocked: no offered operation can make progress |
| textedit-append-line | s1_only | no | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 4 | blocked: blocked: no offered operation can make progress |
| textedit-type-sentence | dual | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
| textedit-type-sentence | dual | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
| textedit-type-sentence | dual | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
| textedit-type-sentence | guarded | yes | predicate | - | 2 | 0/2 | 0/0 | 0.0003 | 10 |  |
| textedit-type-sentence | guarded | yes | predicate | - | 2 | 0/2 | 0/0 | 0.0003 | 11 |  |
| textedit-type-sentence | guarded | yes | predicate | - | 2 | 0/2 | 0/0 | 0.0003 | 10 |  |
| textedit-type-sentence | s1_only | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
| textedit-type-sentence | s1_only | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
| textedit-type-sentence | s1_only | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
