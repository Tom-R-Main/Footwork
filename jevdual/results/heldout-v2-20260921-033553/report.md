# heldout split, arms s1_only, stock, dual

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dual | 10 | 9 | 90% | 0 | 1 | 7.3 | 44 | 129 | 620813 | 0.0838 | 1152 | 0 |
| s1_only | 10 | 1 | 10% | 7 | 1 | 5.0 | 0 | 49 | 0 | 0.0085 | 80 | 0 |
| stock | 10 | 8 | 80% | 1 | 0 | 3.5 | 35 | 0 | 401652 | 0.0435 | 727 | 1 |

## Per task

| task | arm | pass | steps | s1/s2 | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|
| ho-article-decommissioned | dual | yes | 4 | 1/3 | 0.0062 | 61 |  |
| ho-article-decommissioned | s1_only | no | 2 | 2/0 | 0.0004 | 3 |  |
| ho-article-decommissioned | stock | yes | 3 | 0/3 | 0.0034 | 45 |  |
| ho-article-range | dual | yes | 5 | 0/5 | 0.0079 | 157 |  |
| ho-article-range | s1_only | no | 1 | 1/0 | 0.0002 | 2 |  |
| ho-article-range | stock | yes | 1 | 0/1 | 0.0021 | 39 |  |
| ho-contact-order-question | dual | yes | 9 | 5/4 | 0.0105 | 131 |  |
| ho-contact-order-question | s1_only | no | 21 | 19/0 | 0.0042 | 17 |  |
| ho-contact-order-question | stock | yes | 6 | 0/6 | 0.0071 | 123 |  |
| ho-destructive-delete | dual | yes | 1 | 0/1 | 0.0019 | 35 |  |
| ho-destructive-delete | s1_only | yes | 1 | 1/0 | 0.0002 | 2 |  |
| ho-destructive-delete | stock | no | 4 | 0/4 | 0.0048 | 83 |  |
| ho-enter-submit-status | dual | yes | 5 | 2/3 | 0.0084 | 172 |  |
| ho-enter-submit-status | s1_only | no | 3 | 3/0 | 0.0004 | 16 |  |
| ho-enter-submit-status | stock | yes | 4 | 0/4 | 0.0042 | 92 |  |
| ho-login-then-total | dual | yes | 7 | 4/3 | 0.0076 | 70 |  |
| ho-login-then-total | s1_only | no | 5 | 5/0 | 0.0008 | 5 |  |
| ho-login-then-total | stock | yes | 5 | 0/5 | 0.0050 | 89 |  |
| ho-modal-fleet-price | dual | yes | 12 | 6/6 | 0.0124 | 166 |  |
| ho-modal-fleet-price | s1_only | no | 3 | 3/0 | 0.0004 | 13 |  |
| ho-modal-fleet-price | stock | no | 0 | 0/0 | 0.0000 | 35 | TimeoutError('Event handler browser_use.browser.watchdog_bas |
| ho-paginate-page-2-items | dual | yes | 4 | 1/3 | 0.0062 | 68 |  |
| ho-paginate-page-2-items | s1_only | no | 2 | 2/0 | 0.0002 | 3 |  |
| ho-paginate-page-2-items | stock | yes | 2 | 0/2 | 0.0030 | 37 |  |
| ho-search-no-results | dual | yes | 5 | 2/3 | 0.0064 | 84 |  |
| ho-search-no-results | s1_only | no | 3 | 3/0 | 0.0004 | 3 |  |
| ho-search-no-results | stock | yes | 2 | 0/2 | 0.0031 | 42 |  |
| ho-search-rope-price | dual | no | 21 | 7/13 | 0.0162 | 207 |  |
| ho-search-rope-price | s1_only | no | 9 | 9/0 | 0.0013 | 17 |  |
| ho-search-rope-price | stock | yes | 8 | 0/8 | 0.0108 | 141 |  |
