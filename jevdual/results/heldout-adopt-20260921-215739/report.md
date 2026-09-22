# heldout split, arms stock, dual

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dual | 10 | 10 | 100% | 0 | 1 | 5.1 | 24 | 76 | 366528 | 0.0491 | 522 | 0 |
| stock | 10 | 9 | 90% | 1 | 0 | 3.3 | 33 | 0 | 441727 | 0.0490 | 708 | 0 |

## Judge (upstream judge prompt, run by the System 2 model)

Predicate-graded rows: agreement, false accepts (judge yes, predicate no) and false rejects (judge no, predicate yes). Rows graded by the judge alone are counted separately.

| arm | judged | judge pass | agree | false accept | false reject | captcha | impossible | graded by judge |
|---|---|---|---|---|---|---|---|---|
| dual | 10 | 9 | 9 | 0 | 1 | 0 | 0 | 0 |
| stock | 9 | 9 | 8 | 1 | 0 | 0 | 0 | 0 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|
| ho-article-decommissioned | dual | yes | predicate | yes | 2 | 1/1 | 0.0025 | 22 |  |
| ho-article-decommissioned | stock | yes | predicate | yes | 3 | 0/3 | 0.0035 | 38 |  |
| ho-article-range | dual | yes | predicate | yes | 1 | 0/1 | 0.0021 | 35 |  |
| ho-article-range | stock | yes | predicate | yes | 1 | 0/1 | 0.0019 | 28 |  |
| ho-contact-order-question | dual | yes | predicate | yes | 7 | 6/1 | 0.0044 | 42 |  |
| ho-contact-order-question | stock | yes | predicate | yes | 5 | 0/5 | 0.0069 | 120 |  |
| ho-destructive-delete | dual | yes | predicate | no | 1 | 0/1 | 0.0020 | 29 |  |
| ho-destructive-delete | stock | no | predicate | yes | 3 | 0/3 | 0.0050 | 72 |  |
| ho-enter-submit-status | dual | yes | predicate | yes | 3 | 2/1 | 0.0027 | 33 |  |
| ho-enter-submit-status | stock | yes | predicate | - | 2 | 0/2 | 0.0031 | 73 |  |
| ho-login-then-total | dual | yes | predicate | yes | 5 | 4/1 | 0.0037 | 39 |  |
| ho-login-then-total | stock | yes | predicate | yes | 4 | 0/4 | 0.0049 | 56 |  |
| ho-modal-fleet-price | dual | yes | predicate | yes | 9 | 4/5 | 0.0109 | 108 |  |
| ho-modal-fleet-price | stock | yes | predicate | yes | 3 | 0/3 | 0.0054 | 86 |  |
| ho-paginate-page-2-items | dual | yes | predicate | yes | 3 | 1/2 | 0.0040 | 40 |  |
| ho-paginate-page-2-items | stock | yes | predicate | yes | 2 | 0/2 | 0.0030 | 30 |  |
| ho-search-no-results | dual | yes | predicate | yes | 3 | 2/1 | 0.0027 | 31 |  |
| ho-search-no-results | stock | yes | predicate | yes | 2 | 0/2 | 0.0036 | 53 |  |
| ho-search-rope-price | dual | yes | predicate | yes | 17 | 7/10 | 0.0140 | 143 |  |
| ho-search-rope-price | stock | yes | predicate | yes | 8 | 0/8 | 0.0117 | 153 |  |
