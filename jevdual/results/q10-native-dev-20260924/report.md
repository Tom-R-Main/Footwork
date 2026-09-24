# native dev split, arms s1_only, dual, guarded

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dual | 21 | 12 | 57% | 0 | 0 | 8.9 | 79 | 271 | 181545 | 0.0648 | 894 | 15 |
| guarded | 21 | 17 | 81% | 0 | 0 | 9.1 | 192 | 114 | 355429 | 0.0521 | 1023 | 10 |
| s1_only | 21 | 11 | 52% | 0 | 0 | 4.4 | 0 | 101 | 0 | 0.0210 | 202 | 15 |

## Outcomes (external success and claimed completion kept apart)

| arm | verified pass (passed and claimed) | unclaimed pass (passed, UNVERIFIED or paused) | false done | model requests (tracker) | evaluate refusals | cost per verified pass |
|---|---|---|---|---|---|---|
| dual | 0 | 12 | 0 | 0 | 0 | 0.0000 |
| guarded | 0 | 17 | 0 | 0 | 0 | 0.0000 |
| s1_only | 0 | 11 | 0 | 0 | 0 | 0.0000 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | deleg. | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|---|
| calc-multiply | dual | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0021 | 15 |  |
| calc-multiply | dual | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0021 | 15 |  |
| calc-multiply | dual | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0021 | 15 |  |
| calc-multiply | guarded | yes | predicate | - | 8 | 0/8 | 0/0 | 0.0027 | 32 |  |
| calc-multiply | guarded | yes | predicate | - | 8 | 0/8 | 0/0 | 0.0027 | 29 |  |
| calc-multiply | guarded | yes | predicate | - | 8 | 0/8 | 0/0 | 0.0027 | 30 |  |
| calc-multiply | s1_only | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0021 | 15 |  |
| calc-multiply | s1_only | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0021 | 15 |  |
| calc-multiply | s1_only | yes | predicate | - | 8 | 8/0 | 0/0 | 0.0021 | 15 |  |
| calc-percent | dual | no | predicate | - | 25 | 11/14 | 0/0 | 0.0109 | 115 | budget_exhausted: 25 steps |
| calc-percent | dual | no | predicate | - | 25 | 19/6 | 0/0 | 0.0084 | 62 | budget_exhausted: 25 steps |
| calc-percent | dual | no | predicate | - | 25 | 9/16 | 0/0 | 0.0119 | 136 | budget_exhausted: 25 steps |
| calc-percent | guarded | yes | predicate | - | 11 | 0/11 | 0/0 | 0.0040 | 54 |  |
| calc-percent | guarded | yes | predicate | - | 11 | 0/11 | 0/0 | 0.0040 | 46 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| calc-percent | guarded | yes | predicate | - | 11 | 0/11 | 0/0 | 0.0040 | 50 |  |
| calc-percent | s1_only | no | predicate | - | 8 | 8/0 | 0/0 | 0.0021 | 15 | escalated: stuck: stuck 0.93 >= 0.85 at step 8 |
| calc-percent | s1_only | no | predicate | - | 3 | 3/0 | 0/0 | 0.0008 | 7 | escalated: target_confidence: target confidence 0.43 < 0.45 |
| calc-percent | s1_only | no | predicate | - | 6 | 6/0 | 0/0 | 0.0016 | 12 | escalated: target_confidence: target confidence 0.38 < 0.45 |
| calc-read-result | dual | no | predicate | - | 7 | 5/2 | 0/0 | 0.0023 | 16 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| calc-read-result | dual | no | predicate | - | 7 | 5/2 | 0/0 | 0.0023 | 15 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| calc-read-result | dual | no | predicate | - | 2 | 0/2 | 0/0 | 0.0011 | 11 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| calc-read-result | guarded | yes | predicate | - | 6 | 0/6 | 0/0 | 0.0020 | 23 |  |
| calc-read-result | guarded | yes | predicate | - | 6 | 0/6 | 0/0 | 0.0020 | 21 |  |
| calc-read-result | guarded | yes | predicate | - | 6 | 0/6 | 0/0 | 0.0020 | 30 |  |
| calc-read-result | s1_only | no | predicate | - | 6 | 6/0 | 0/0 | 0.0015 | 11 | escalated: done without an answer on an answer task; not ver |
| calc-read-result | s1_only | no | predicate | - | 6 | 6/0 | 0/0 | 0.0015 | 12 | escalated: done without an answer on an answer task; not ver |
| calc-read-result | s1_only | no | predicate | - | 1 | 1/0 | 0/0 | 0.0003 | 5 | escalated: done without an answer on an answer task; not ver |
| calc-subtract | dual | yes | predicate | - | 10 | 8/2 | 0/0 | 0.0032 | 23 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| calc-subtract | dual | yes | predicate | - | 10 | 8/2 | 0/0 | 0.0032 | 24 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| calc-subtract | dual | yes | predicate | - | 10 | 8/2 | 0/0 | 0.0032 | 23 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| calc-subtract | guarded | yes | predicate | - | 10 | 0/10 | 0/0 | 0.0036 | 53 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| calc-subtract | guarded | yes | predicate | - | 10 | 0/10 | 0/0 | 0.0036 | 42 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| calc-subtract | guarded | yes | predicate | - | 10 | 0/10 | 0/0 | 0.0037 | 42 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| calc-subtract | s1_only | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0023 | 16 | escalated: verification verify: uncertain: complete p=0.71,  |
| calc-subtract | s1_only | yes | predicate | - | 9 | 9/0 | 0/0 | 0.0023 | 16 | escalated: verification verify: uncertain: complete p=0.73,  |
| calc-subtract | s1_only | no | predicate | - | 3 | 3/0 | 0/0 | 0.0008 | 10 | escalated: target_confidence: target confidence 0.43 < 0.45 |
| textedit-append-and-save | dual | yes | predicate | - | 5 | 2/3 | 0/0 | 0.0010 | 31 | error: observation failed: Tool: tool='get_window_state', me |
| textedit-append-and-save | dual | yes | predicate | - | 19 | 1/18 | 0/0 | 0.0081 | 294 | error: s2 fatal: done refused 2 times; The document was save |
| textedit-append-and-save | dual | yes | predicate | - | 6 | 2/4 | 0/0 | 0.0013 | 57 | error: observation failed: Tool: tool='get_window_state', me |
| textedit-append-and-save | guarded | no | predicate | - | 25 | 0/25 | 0/0 | 0.0042 | 134 | budget_exhausted: 25 steps |
| textedit-append-and-save | guarded | yes | predicate | - | 25 | 0/25 | 0/0 | 0.0045 | 161 | budget_exhausted: 25 steps |
| textedit-append-and-save | guarded | yes | predicate | - | 25 | 0/25 | 0/0 | 0.0042 | 218 | budget_exhausted: 25 steps |
| textedit-append-and-save | s1_only | yes | predicate | - | 3 | 3/0 | 0/0 | 0.0002 | 8 | blocked: blocked: no offered operation can make progress |
| textedit-append-and-save | s1_only | yes | predicate | - | 3 | 3/0 | 0/0 | 0.0002 | 6 | blocked: blocked: no offered operation can make progress |
| textedit-append-and-save | s1_only | yes | predicate | - | 3 | 3/0 | 0/0 | 0.0002 | 7 | blocked: blocked: no offered operation can make progress |
| textedit-read-word-count | dual | no | predicate | - | 2 | 0/2 | 0/0 | 0.0004 | 8 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| textedit-read-word-count | dual | no | predicate | - | 2 | 0/2 | 0/0 | 0.0004 | 10 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| textedit-read-word-count | dual | no | predicate | - | 2 | 0/2 | 0/0 | 0.0004 | 9 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| textedit-read-word-count | guarded | no | predicate | - | 2 | 0/2 | 0/0 | 0.0004 | 8 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| textedit-read-word-count | guarded | no | predicate | - | 2 | 0/2 | 0/0 | 0.0004 | 8 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| textedit-read-word-count | guarded | no | predicate | - | 2 | 0/2 | 0/0 | 0.0004 | 10 | error: s2 fatal: done refused 2 times; uncertain: complete p |
| textedit-read-word-count | s1_only | no | predicate | - | 1 | 1/0 | 0/0 | 0.0001 | 5 | escalated: done without an answer on an answer task; not ver |
| textedit-read-word-count | s1_only | no | predicate | - | 1 | 1/0 | 0/0 | 0.0001 | 5 | escalated: done without an answer on an answer task; not ver |
| textedit-read-word-count | s1_only | no | predicate | - | 1 | 1/0 | 0/0 | 0.0001 | 5 | escalated: done without an answer on an answer task; not ver |
| textedit-type-sentence | dual | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
| textedit-type-sentence | dual | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
| textedit-type-sentence | dual | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
| textedit-type-sentence | guarded | yes | predicate | - | 2 | 0/2 | 0/0 | 0.0003 | 10 |  |
| textedit-type-sentence | guarded | yes | predicate | - | 2 | 0/2 | 0/0 | 0.0003 | 9 |  |
| textedit-type-sentence | guarded | yes | predicate | - | 2 | 0/2 | 0/0 | 0.0003 | 12 |  |
| textedit-type-sentence | s1_only | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
| textedit-type-sentence | s1_only | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
| textedit-type-sentence | s1_only | yes | predicate | - | 2 | 2/0 | 0/0 | 0.0002 | 6 |  |
