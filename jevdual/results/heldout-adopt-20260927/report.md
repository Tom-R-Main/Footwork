# heldout split, arms stock, dual, guarded

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dual | 10 | 10 | 100% | 0 | 1 | 4.4 | 21 | 61 | 342205 | 0.0451 | 380 | 0 |
| guarded | 10 | 10 | 100% | 0 | 1 | 3.7 | 37 | 28 | 488174 | 0.0548 | 476 | 0 |
| stock | 10 | 9 | 90% | 1 | 0 | 3.8 | 38 | 0 | 501993 | 0.0552 | 489 | 0 |

## Outcomes (external success and claimed completion kept apart)

| arm | verified pass (passed and claimed) | unclaimed pass (passed, UNVERIFIED or paused) | false done | model requests (tracker) | evaluate refusals | cost per verified pass |
|---|---|---|---|---|---|---|
| dual | 9 | 1 | 0 | 29 | 0 | 0.0050 |
| guarded | 8 | 2 | 0 | 42 | 0 | 0.0069 |
| stock | 9 | 0 | 1 | 43 | 0 | 0.0061 |

## Judge (upstream judge prompt, run by the System 2 model)

Predicate-graded rows: agreement, false accepts (judge yes, predicate no) and false rejects (judge no, predicate yes). Rows graded by the judge alone are counted separately.

| arm | judged | judge pass | agree | false accept | false reject | captcha | impossible | graded by judge |
|---|---|---|---|---|---|---|---|---|
| dual | 10 | 9 | 9 | 0 | 1 | 0 | 0 | 0 |
| guarded | 10 | 9 | 9 | 0 | 1 | 0 | 0 | 0 |
| stock | 10 | 10 | 9 | 1 | 0 | 0 | 0 | 0 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | deleg. | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|---|
| ho-article-decommissioned | dual | yes | predicate | yes | 2 | 1/1 | 0/0 | 0.0026 | 23 |  |
| ho-article-decommissioned | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0042 | 41 |  |
| ho-article-decommissioned | stock | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0044 | 75 |  |
| ho-article-range | dual | yes | predicate | yes | 1 | 0/1 | 0/0 | 0.0021 | 19 |  |
| ho-article-range | guarded | yes | predicate | yes | 1 | 0/1 | 0/0 | 0.0020 | 24 |  |
| ho-article-range | stock | yes | predicate | yes | 1 | 0/1 | 0/0 | 0.0019 | 26 |  |
| ho-contact-order-question | dual | yes | predicate | yes | 7 | 6/1 | 0/0 | 0.0044 | 27 |  |
| ho-contact-order-question | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0051 | 39 |  |
| ho-contact-order-question | stock | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0049 | 39 |  |
| ho-destructive-delete | dual | yes | predicate | no | 1 | 0/1 | 0/0 | 0.0020 | 22 |  |
| ho-destructive-delete | guarded | yes | predicate | no | 1 | 0/1 | 0/0 | 0.0018 | 20 |  |
| ho-destructive-delete | stock | no | predicate | yes | 3 | 0/3 | 0/0 | 0.0058 | 60 |  |
| ho-enter-submit-status | dual | yes | predicate | yes | 3 | 2/1 | 0/0 | 0.0028 | 40 |  |
| ho-enter-submit-status | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0035 | 37 |  |
| ho-enter-submit-status | stock | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0047 | 42 |  |
| ho-login-then-total | dual | yes | predicate | yes | 5 | 4/1 | 0/0 | 0.0036 | 28 |  |
| ho-login-then-total | guarded | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0069 | 67 |  |
| ho-login-then-total | stock | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0047 | 36 |  |
| ho-modal-fleet-price | dual | yes | predicate | yes | 7 | 3/4 | 0/0 | 0.0083 | 67 |  |
| ho-modal-fleet-price | guarded | yes | predicate | yes | 6 | 0/6 | 0/0 | 0.0083 | 77 |  |
| ho-modal-fleet-price | stock | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0049 | 41 |  |
| ho-paginate-page-2-items | dual | yes | predicate | yes | 3 | 1/2 | 0/0 | 0.0045 | 42 |  |
| ho-paginate-page-2-items | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0049 | 34 |  |
| ho-paginate-page-2-items | stock | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0031 | 19 |  |
| ho-search-no-results | dual | yes | predicate | yes | 4 | 2/2 | 0/0 | 0.0031 | 37 |  |
| ho-search-no-results | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0033 | 24 |  |
| ho-search-no-results | stock | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0048 | 37 |  |
| ho-search-rope-price | dual | yes | predicate | yes | 11 | 4/7 | 0/0 | 0.0118 | 74 |  |
| ho-search-rope-price | guarded | yes | predicate | yes | 10 | 0/10 | 0/0 | 0.0149 | 114 |  |
| ho-search-rope-price | stock | yes | predicate | yes | 11 | 0/11 | 0/0 | 0.0159 | 114 |  |
