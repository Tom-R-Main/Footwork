# native dev split, arms s1_only, dual, guarded, bounded

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bounded | 18 | 18 | 100% | 0 | 0 | 6.5 | 93 | 49 | 141247 | 0.0193 | 559 | 1 |
| dual | 18 | 17 | 94% | 0 | 0 | 8.6 | 37 | 177 | 63592 | 0.0299 | 462 | 2 |
| guarded | 18 | 16 | 89% | 0 | 0 | 6.3 | 113 | 17 | 160660 | 0.0200 | 530 | 2 |
| s1_only | 18 | 9 | 50% | 0 | 0 | 5.4 | 0 | 108 | 0 | 0.0137 | 191 | 9 |

## Outcomes (external success and claimed completion kept apart)

| arm | verified pass (passed and claimed) | unclaimed pass (passed, UNVERIFIED or paused) | false done | model requests (tracker) | evaluate refusals | cost per verified pass |
|---|---|---|---|---|---|---|
| bounded | 17 | 1 | 0 | 0 | 0 | 0.0011 |
| dual | 16 | 1 | 0 | 0 | 0 | 0.0019 |
| guarded | 16 | 0 | 0 | 0 | 0 | 0.0012 |
| s1_only | 9 | 0 | 0 | 0 | 0 | 0.0015 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | deleg. | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|---|
| calc-multiply | bounded | yes | predicate | - | 8 | 1/7 | 0/0 | 0.0014 | 31 |  |
| calc-multiply | bounded | yes | predicate | - | 8 | 1/7 | 0/0 | 0.0013 | 32 |  |
| calc-multiply | bounded | yes | predicate | - | 8 | 1/7 | 0/0 | 0.0013 | 29 |  |
| calc-multiply | dual | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 14 |  |
| calc-multiply | dual | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 14 |  |
| calc-multiply | dual | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 14 |  |
| calc-multiply | guarded | yes | predicate | - | 8 | 0/8 | 0/0 | 0.0014 | 30 |  |
| calc-multiply | guarded | yes | predicate | - | 8 | 0/8 | 0/0 | 0.0014 | 31 |  |
| calc-multiply | guarded | yes | predicate | - | 8 | 0/8 | 0/0 | 0.0014 | 31 |  |
| calc-multiply | s1_only | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 15 |  |
| calc-multiply | s1_only | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 14 |  |
| calc-multiply | s1_only | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0012 | 14 |  |
| calc-percent | bounded | yes | predicate | - | 10 | 1/9 | 0/0 | 0.0018 | 45 |  |
| calc-percent | bounded | yes | predicate | - | 10 | 1/9 | 0/0 | 0.0019 | 115 | error: observation failed: Tool: tool='get_window_state', me |
| calc-percent | bounded | yes | predicate | - | 10 | 1/9 | 0/0 | 0.0019 | 50 |  |
| calc-percent | dual | no | predicate | - | 25 | 18/7 | 0/0 | 0.0054 | 91 | budget_exhausted: 25 steps |
| calc-percent | dual | yes | predicate | - | 25 | 11/14 | 0/0 | 0.0070 | 103 |  |
| calc-percent | dual | yes | predicate | - | 18 | 11/7 | 0/0 | 0.0043 | 63 |  |
| calc-percent | guarded | yes | predicate | - | 10 | 0/10 | 0/0 | 0.0019 | 45 |  |
| calc-percent | guarded | no | predicate | - | 6 | 0/6 | 0/0 | 0.0011 | 69 | error: observation failed: Tool: tool='get_window_state', me |
| calc-percent | guarded | yes | predicate | - | 10 | 0/10 | 0/0 | 0.0020 | 53 |  |
| calc-percent | s1_only | no | predicate | - | 6 | 6/0 | 0/0 | 0.0009 | 12 | escalated: target_confidence: target confidence 0.37 < 0.45 |
| calc-percent | s1_only | no | predicate | - | 6 | 6/0 | 0/0 | 0.0009 | 11 | escalated: target_confidence: target confidence 0.36 < 0.45 |
| calc-percent | s1_only | no | predicate | - | 5 | 5/0 | 0/0 | 0.0007 | 10 | escalated: target_confidence: target confidence 0.39 < 0.45 |
| calc-read-result | bounded | yes | predicate | - | 6 | 1/5 | 0/0 | 0.0010 | 31 |  |
| calc-read-result | bounded | yes | predicate | - | 6 | 1/5 | 0/0 | 0.0009 | 19 |  |
| calc-read-result | bounded | yes | predicate | - | 6 | 1/5 | 0/0 | 0.0010 | 30 |  |
| calc-read-result | dual | yes | predicate | - | 7 | 5/2 | 0/0 | 0.0014 | 16 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| calc-read-result | dual | yes | predicate | - | 6 | 5/1 | 0/0 | 0.0011 | 15 |  |
| calc-read-result | dual | yes | predicate | - | 6 | 5/1 | 0/0 | 0.0011 | 14 |  |
| calc-read-result | guarded | yes | predicate | - | 6 | 0/6 | 0/0 | 0.0010 | 21 |  |
| calc-read-result | guarded | yes | predicate | - | 6 | 0/6 | 0/0 | 0.0010 | 22 |  |
| calc-read-result | guarded | yes | predicate | - | 6 | 0/6 | 0/0 | 0.0010 | 24 |  |
| calc-read-result | s1_only | no | predicate | - | 6 | 6/0 | 0/0 | 0.0009 | 12 | escalated: done without an answer on an answer task; not ver |
| calc-read-result | s1_only | no | predicate | - | 6 | 6/0 | 0/0 | 0.0009 | 12 | escalated: done without an answer on an answer task; not ver |
| calc-read-result | s1_only | no | predicate | - | 6 | 6/0 | 0/0 | 0.0009 | 11 | escalated: done without an answer on an answer task; not ver |
| calc-subtract | bounded | yes | predicate | - | 9 | 1/8 | 0/0 | 0.0015 | 29 |  |
| calc-subtract | bounded | yes | predicate | - | 9 | 1/8 | 0/0 | 0.0015 | 30 |  |
| calc-subtract | bounded | yes | predicate | - | 9 | 1/8 | 0/0 | 0.0015 | 39 |  |
| calc-subtract | dual | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0013 | 16 |  |
| calc-subtract | dual | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0013 | 16 |  |
| calc-subtract | dual | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0013 | 16 |  |
| calc-subtract | guarded | yes | predicate | - | 9 | 0/9 | 0/0 | 0.0016 | 31 |  |
| calc-subtract | guarded | yes | predicate | - | 9 | 0/9 | 0/0 | 0.0016 | 33 |  |
| calc-subtract | guarded | yes | predicate | - | 9 | 0/9 | 0/0 | 0.0016 | 32 |  |
| calc-subtract | s1_only | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0013 | 16 |  |
| calc-subtract | s1_only | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0013 | 16 |  |
| calc-subtract | s1_only | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0013 | 16 |  |
| textedit-append-line | bounded | yes | predicate | - | 6 | 2/4 | 0/0 | 0.0011 | 38 |  |
| textedit-append-line | bounded | yes | predicate | - | 3 | 2/1 | 0/0 | 0.0004 | 11 |  |
| textedit-append-line | bounded | yes | predicate | - | 3 | 2/1 | 0/0 | 0.0004 | 14 |  |
| textedit-append-line | dual | yes | predicate | - | 3 | 2/1 | 0/0 | 0.0004 | 10 |  |
| textedit-append-line | dual | yes | predicate | - | 4 | 2/2 | 0/0 | 0.0007 | 21 |  |
| textedit-append-line | dual | yes | predicate | - | 4 | 2/2 | 0/0 | 0.0007 | 21 |  |
| textedit-append-line | guarded | yes | predicate | - | 6 | 0/6 | 0/0 | 0.0012 | 44 |  |
| textedit-append-line | guarded | no | predicate | - | 3 | 0/3 | 0/0 | 0.0004 | 19 | error: observation failed: NativeBridgeError: the screen is  |
| textedit-append-line | guarded | yes | predicate | - | 3 | 0/3 | 0/0 | 0.0005 | 18 |  |
| textedit-append-line | s1_only | no | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 4 | blocked: blocked: no offered operation can make progress |
| textedit-append-line | s1_only | no | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 4 | blocked: blocked: no offered operation can make progress |
| textedit-append-line | s1_only | no | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 5 | escalated: verification reject: The document was saved with  |
| textedit-type-sentence | bounded | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
| textedit-type-sentence | bounded | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
| textedit-type-sentence | bounded | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
| textedit-type-sentence | dual | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
| textedit-type-sentence | dual | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 7 |  |
| textedit-type-sentence | dual | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
| textedit-type-sentence | guarded | yes | predicate | - | 2 | 0/2 | 0/0 | 0.0003 | 10 |  |
| textedit-type-sentence | guarded | yes | predicate | - | 2 | 0/2 | 0/0 | 0.0003 | 10 |  |
| textedit-type-sentence | guarded | yes | predicate | - | 2 | 0/2 | 0/0 | 0.0003 | 10 |  |
| textedit-type-sentence | s1_only | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
| textedit-type-sentence | s1_only | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
| textedit-type-sentence | s1_only | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
