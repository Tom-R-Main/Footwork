# Failure taxonomy: q10-native-dev-20260924

| class | count |
|---|---|
| pass | 40 |
| crash | 23 |

## Per task

| task | arm | class | steps | final url | last reason |
|---|---|---|---|---|---|
| calc-multiply | s1_only | pass | 8 | app://Calculator | verification accept: complete p=0.88, max unmet p=0.11 |
| calc-multiply | dual | pass | 8 | app://Calculator | verification accept: complete p=0.89, max unmet p=0.09 |
| calc-multiply | guarded | pass | 8 | app://Calculator | System 2 done, verification accept: complete p=0.93, max unm |
| calc-subtract | s1_only | pass | 9 | app://Calculator | verification verify: uncertain: complete p=0.71, max unmet p |
| calc-subtract | dual | pass | 10 | app://Calculator | System 2 done refused, verification verify: uncertain: compl |
| calc-subtract | guarded | pass | 10 | app://Calculator | System 2 done refused, verification verify: uncertain: compl |
| calc-percent | s1_only | crash | 8 | app://Calculator | stuck: stuck 0.93 >= 0.85 at step 8 |
| calc-percent | dual | crash | 25 | app://Calculator | act: operation 0.97, target 0.69 |
| calc-percent | guarded | pass | 11 | app://Calculator | System 2 done, verification accept: complete p=0.94, max unm |
| calc-read-result | s1_only | crash | 6 | app://Calculator | done without an answer on an answer task; not verified |
| calc-read-result | dual | crash | 7 | app://Calculator | System 2 done refused, verification verify: uncertain: compl |
| calc-read-result | guarded | pass | 6 | app://Calculator | System 2 done, verification accept: complete p=0.91, max unm |
| textedit-type-sentence | s1_only | pass | 2 | app://TextEdit | verification accept: complete p=0.96, max unmet p=0.07 |
| textedit-type-sentence | dual | pass | 2 | app://TextEdit | verification accept: complete p=0.96, max unmet p=0.07 |
| textedit-type-sentence | guarded | pass | 2 | app://TextEdit | System 2 done, verification accept: complete p=0.97, max unm |
| textedit-append-and-save | s1_only | pass | 3 | app://TextEdit | blocked: no offered operation can make progress |
| textedit-append-and-save | dual | pass | 5 | app://TextEdit | System 2 hotkey cmd+down |
| textedit-append-and-save | guarded | crash | 25 | app://TextEdit | System 2 type [1] (Document is on one line; setting two line |
| textedit-read-word-count | s1_only | crash | 1 | app://TextEdit | done without an answer on an answer task; not verified |
| textedit-read-word-count | dual | crash | 2 | app://TextEdit | System 2 done refused, verification verify: uncertain: compl |
| textedit-read-word-count | guarded | crash | 2 | app://TextEdit | System 2 done refused, verification verify: uncertain: compl |
| calc-multiply | s1_only | pass | 8 | app://Calculator | verification accept: complete p=0.85, max unmet p=0.12 |
| calc-multiply | dual | pass | 8 | app://Calculator | verification accept: complete p=0.86, max unmet p=0.11 |
| calc-multiply | guarded | pass | 8 | app://Calculator | System 2 done, verification accept: complete p=0.96, max unm |
| calc-subtract | s1_only | pass | 9 | app://Calculator | verification verify: uncertain: complete p=0.73, max unmet p |
| calc-subtract | dual | pass | 10 | app://Calculator | System 2 done refused, verification verify: uncertain: compl |
| calc-subtract | guarded | pass | 10 | app://Calculator | System 2 done refused, verification verify: uncertain: compl |
| calc-percent | s1_only | crash | 3 | app://Calculator | target_confidence: target confidence 0.43 < 0.45 |
| calc-percent | dual | crash | 25 | app://Calculator | System 2 click [8] (Clearing the partial '2' entry to restar |
| calc-percent | guarded | pass | 11 | app://Calculator | System 2 done refused, verification verify: uncertain: compl |
| calc-read-result | s1_only | crash | 6 | app://Calculator | done without an answer on an answer task; not verified |
| calc-read-result | dual | crash | 7 | app://Calculator | System 2 done refused, verification verify: uncertain: compl |
| calc-read-result | guarded | pass | 6 | app://Calculator | System 2 done, verification accept: complete p=0.93, max unm |
| textedit-type-sentence | s1_only | pass | 2 | app://TextEdit | verification accept: complete p=0.96, max unmet p=0.07 |
| textedit-type-sentence | dual | pass | 2 | app://TextEdit | verification accept: complete p=0.97, max unmet p=0.08 |
| textedit-type-sentence | guarded | pass | 2 | app://TextEdit | System 2 done, verification accept: complete p=0.95, max unm |
| textedit-append-and-save | s1_only | pass | 3 | app://TextEdit | blocked: no offered operation can make progress |
| textedit-append-and-save | dual | pass | 19 | app://TextEdit | System 2 done refused, verification reject: The document was |
| textedit-append-and-save | guarded | pass | 25 | app://TextEdit | System 2 type [1] (Document is single line; inserting newlin |
| textedit-read-word-count | s1_only | crash | 1 | app://TextEdit | done without an answer on an answer task; not verified |
| textedit-read-word-count | dual | crash | 2 | app://TextEdit | System 2 done refused, verification verify: uncertain: compl |
| textedit-read-word-count | guarded | crash | 2 | app://TextEdit | System 2 done refused, verification verify: uncertain: compl |
| calc-multiply | s1_only | pass | 8 | app://Calculator | verification accept: complete p=0.88, max unmet p=0.10 |
| calc-multiply | dual | pass | 8 | app://Calculator | verification accept: complete p=0.85, max unmet p=0.13 |
| calc-multiply | guarded | pass | 8 | app://Calculator | System 2 done, verification accept: complete p=0.96, max unm |
| calc-subtract | s1_only | crash | 3 | app://Calculator | target_confidence: target confidence 0.43 < 0.45 |
| calc-subtract | dual | pass | 10 | app://Calculator | System 2 done refused, verification verify: uncertain: compl |
| calc-subtract | guarded | pass | 10 | app://Calculator | System 2 done refused, verification verify: uncertain: compl |
| calc-percent | s1_only | crash | 6 | app://Calculator | target_confidence: target confidence 0.38 < 0.45 |
| calc-percent | dual | crash | 25 | app://Calculator | act: operation 0.96, target 0.63 |
| calc-percent | guarded | pass | 11 | app://Calculator | System 2 done, verification accept: complete p=0.93, max unm |
| calc-read-result | s1_only | crash | 1 | app://Calculator | done without an answer on an answer task; not verified |
| calc-read-result | dual | crash | 2 | app://Calculator | System 2 done refused, verification verify: uncertain: compl |
| calc-read-result | guarded | pass | 6 | app://Calculator | System 2 done, verification accept: complete p=0.93, max unm |
| textedit-type-sentence | s1_only | pass | 2 | app://TextEdit | verification accept: complete p=0.97, max unmet p=0.07 |
| textedit-type-sentence | dual | pass | 2 | app://TextEdit | verification accept: complete p=0.95, max unmet p=0.07 |
| textedit-type-sentence | guarded | pass | 2 | app://TextEdit | System 2 done, verification accept: complete p=0.95, max unm |
| textedit-append-and-save | s1_only | pass | 3 | app://TextEdit | blocked: no offered operation can make progress |
| textedit-append-and-save | dual | pass | 6 | app://TextEdit | System 2 hotkey cmd+down |
| textedit-append-and-save | guarded | pass | 25 | app://TextEdit | System 2 type [1] (Fixing document to two lines ending with  |
| textedit-read-word-count | s1_only | crash | 1 | app://TextEdit | done without an answer on an answer task; not verified |
| textedit-read-word-count | dual | crash | 2 | app://TextEdit | System 2 done refused, verification verify: uncertain: compl |
| textedit-read-word-count | guarded | crash | 2 | app://TextEdit | System 2 done refused, verification verify: uncertain: compl |

## Escalation reasons (S1 steps not executed)

- done without an answer on an answer task: 6
- blocked: 3
- target_confidence: 3
- verification verify: 2
- stuck: 1

## Executed actions

- click: 284
- input: 87
- done: 23
- send_keys: 15
- wait: 9
- menu: 3
