# native dev split, arms s1_only, dual, guarded

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dual | 18 | 15 | 83% | 0 | 0 | 8.2 | 28 | 165 | 45476 | 0.0272 | 443 | 6 |
| guarded | 18 | 17 | 94% | 0 | 1 | 7.1 | 128 | 19 | 192077 | 0.0243 | 745 | 2 |
| s1_only | 18 | 12 | 67% | 0 | 0 | 5.5 | 0 | 108 | 0 | 0.0143 | 199 | 9 |

## Outcomes (external success and claimed completion kept apart)

| arm | verified pass (passed and claimed) | unclaimed pass (passed, UNVERIFIED or paused) | false done | model requests (tracker) | evaluate refusals | cost per verified pass |
|---|---|---|---|---|---|---|
| dual | 0 | 15 | 0 | 0 | 0 | 0.0000 |
| guarded | 0 | 17 | 0 | 0 | 0 | 0.0000 |
| s1_only | 0 | 12 | 0 | 0 | 0 | 0.0000 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | deleg. | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|---|
| calc-multiply | dual | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 14 |  |
| calc-multiply | dual | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 14 |  |
| calc-multiply | dual | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 14 |  |
| calc-multiply | guarded | yes | predicate | - | 8 | 0/8 | 0/0 | 0.0014 | 40 |  |
| calc-multiply | guarded | yes | predicate | - | 8 | 0/8 | 0/0 | 0.0014 | 29 |  |
| calc-multiply | guarded | yes | predicate | - | 8 | 0/8 | 0/0 | 0.0014 | 46 |  |
| calc-multiply | s1_only | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 15 |  |
| calc-multiply | s1_only | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 15 |  |
| calc-multiply | s1_only | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 15 |  |
| calc-percent | dual | yes | predicate | - | 25 | 19/6 | 0/0 | 0.0054 | 74 |  |
| calc-percent | dual | yes | predicate | - | 16 | 12/4 | 0/0 | 0.0033 | 42 |  |
| calc-percent | dual | yes | predicate | - | 14 | 11/3 | 0/0 | 0.0029 | 40 |  |
| calc-percent | guarded | yes | predicate | - | 10 | 0/10 | 0/0 | 0.0019 | 54 |  |
| calc-percent | guarded | yes | predicate | - | 10 | 0/10 | 0/0 | 0.0019 | 49 |  |
| calc-percent | guarded | yes | predicate | - | 10 | 0/10 | 0/0 | 0.0019 | 49 |  |
| calc-percent | s1_only | no | predicate | - | 5 | 5/0 | 0/0 | 0.0008 | 10 | escalated: target_confidence: target confidence 0.42 < 0.45 |
| calc-percent | s1_only | no | predicate | - | 6 | 6/0 | 0/0 | 0.0009 | 11 | escalated: target_confidence: target confidence 0.44 < 0.45 |
| calc-percent | s1_only | no | predicate | - | 4 | 4/0 | 0/0 | 0.0006 | 9 | escalated: target_confidence: target confidence 0.36 < 0.45 |
| calc-read-result | dual | no | predicate | - | 7 | 5/2 | 0/0 | 0.0014 | 16 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| calc-read-result | dual | no | predicate | - | 7 | 5/2 | 0/0 | 0.0014 | 16 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| calc-read-result | dual | no | predicate | - | 7 | 5/2 | 0/0 | 0.0014 | 17 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| calc-read-result | guarded | yes | predicate | - | 6 | 0/6 | 0/0 | 0.0010 | 25 |  |
| calc-read-result | guarded | yes | predicate | - | 6 | 0/6 | 0/0 | 0.0010 | 23 |  |
| calc-read-result | guarded | yes | predicate | - | 6 | 0/6 | 0/0 | 0.0010 | 27 |  |
| calc-read-result | s1_only | no | predicate | - | 6 | 6/0 | 0/0 | 0.0009 | 11 | escalated: done without an answer on an answer task; not ver |
| calc-read-result | s1_only | no | predicate | - | 6 | 6/0 | 0/0 | 0.0009 | 12 | escalated: done without an answer on an answer task; not ver |
| calc-read-result | s1_only | no | predicate | - | 6 | 6/0 | 0/0 | 0.0009 | 10 | escalated: done without an answer on an answer task; not ver |
| calc-subtract | dual | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0014 | 15 |  |
| calc-subtract | dual | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0014 | 16 |  |
| calc-subtract | dual | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0014 | 16 |  |
| calc-subtract | guarded | yes | predicate | - | 9 | 0/9 | 0/0 | 0.0016 | 38 |  |
| calc-subtract | guarded | yes | predicate | - | 9 | 0/9 | 0/0 | 0.0016 | 34 |  |
| calc-subtract | guarded | yes | predicate | - | 9 | 0/9 | 0/0 | 0.0016 | 39 |  |
| calc-subtract | s1_only | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0014 | 16 |  |
| calc-subtract | s1_only | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0014 | 16 |  |
| calc-subtract | s1_only | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0014 | 19 |  |
| textedit-append-line | dual | yes | predicate | - | 5 | 2/3 | 0/0 | 0.0010 | 44 | error: observation failed: Tool: tool='get_window_state', me |
| textedit-append-line | dual | yes | predicate | - | 3 | 2/1 | 0/0 | 0.0005 | 17 | error: observation failed: Tool: tool='get_window_state', me |
| textedit-append-line | dual | yes | predicate | - | 6 | 2/4 | 0/0 | 0.0013 | 64 | error: observation failed: Tool: tool='get_window_state', me |
| textedit-append-line | guarded | yes | predicate | - | 9 | 0/9 | 0/0 | 0.0022 | 100 | error: s2 fatal: done refused 2 times; The document was save |
| textedit-append-line | guarded | yes | predicate | - | 9 | 0/9 | 0/0 | 0.0022 | 102 | error: s2 fatal: done refused 2 times; complete p=0.29; ledg |
| textedit-append-line | guarded | no | predicate | - | 5 | 0/5 | 0/0 | 0.0010 | 60 |  |
| textedit-append-line | s1_only | yes | predicate | - | 3 | 3/0 | 0/0 | 0.0003 | 7 | blocked: blocked: no offered operation can make progress |
| textedit-append-line | s1_only | yes | predicate | - | 3 | 3/0 | 0/0 | 0.0003 | 8 | blocked: blocked: no offered operation can make progress |
| textedit-append-line | s1_only | yes | predicate | - | 3 | 3/0 | 0/0 | 0.0003 | 7 | blocked: blocked: no offered operation can make progress |
| textedit-type-sentence | dual | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
| textedit-type-sentence | dual | yes | predicate | - | 2 | 1/1 | 0/0 | 0.0003 | 9 |  |
| textedit-type-sentence | dual | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
| textedit-type-sentence | guarded | yes | predicate | - | 2 | 0/2 | 0/0 | 0.0003 | 10 |  |
| textedit-type-sentence | guarded | yes | predicate | - | 2 | 0/2 | 0/0 | 0.0003 | 11 |  |
| textedit-type-sentence | guarded | yes | predicate | - | 2 | 0/2 | 0/0 | 0.0003 | 10 |  |
| textedit-type-sentence | s1_only | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
| textedit-type-sentence | s1_only | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
| textedit-type-sentence | s1_only | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
