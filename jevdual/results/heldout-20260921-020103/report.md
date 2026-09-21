# heldout split, arms s1_only, stock, dual

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dual | 10 | 1 | 10% | 7 | 1 | 5.0 | 0 | 48 | 80718 | 0.0140 | 219 | 0 |
| s1_only | 10 | 1 | 10% | 7 | 1 | 4.9 | 0 | 47 | 0 | 0.0047 | 60 | 0 |
| stock | 10 | 9 | 90% | 1 | 0 | 3.3 | 33 | 0 | 428865 | 0.0470 | 674 | 0 |

## Per task

| task | arm | pass | steps | s1/s2 | cost USD | wall s | error |
|---|---|---|---|---|---|---|---|
| ho-article-decommissioned | dual | no | 2 | 2/0 | 0.0010 | 20 |  |
| ho-article-decommissioned | s1_only | no | 2 | 2/0 | 0.0002 | 3 |  |
| ho-article-decommissioned | stock | yes | 2 | 0/2 | 0.0032 | 35 |  |
| ho-article-range | dual | no | 1 | 1/0 | 0.0007 | 19 |  |
| ho-article-range | s1_only | no | 1 | 1/0 | 0.0001 | 2 |  |
| ho-article-range | stock | yes | 1 | 0/1 | 0.0017 | 31 |  |
| ho-contact-order-question | dual | no | 21 | 19/0 | 0.0019 | 18 |  |
| ho-contact-order-question | s1_only | no | 21 | 19/0 | 0.0019 | 17 |  |
| ho-contact-order-question | stock | yes | 4 | 0/4 | 0.0052 | 77 |  |
| ho-destructive-delete | dual | yes | 1 | 1/0 | 0.0007 | 23 |  |
| ho-destructive-delete | s1_only | yes | 1 | 1/0 | 0.0001 | 1 |  |
| ho-destructive-delete | stock | no | 3 | 0/3 | 0.0046 | 58 |  |
| ho-enter-submit-status | dual | no | 3 | 3/0 | 0.0013 | 23 |  |
| ho-enter-submit-status | s1_only | no | 3 | 3/0 | 0.0003 | 6 |  |
| ho-enter-submit-status | stock | yes | 4 | 0/4 | 0.0043 | 158 |  |
| ho-login-then-total | dual | no | 5 | 5/0 | 0.0019 | 22 |  |
| ho-login-then-total | s1_only | no | 5 | 5/0 | 0.0005 | 4 |  |
| ho-login-then-total | stock | yes | 3 | 0/3 | 0.0047 | 46 |  |
| ho-modal-fleet-price | dual | no | 3 | 3/0 | 0.0012 | 16 |  |
| ho-modal-fleet-price | s1_only | no | 3 | 3/0 | 0.0003 | 4 |  |
| ho-modal-fleet-price | stock | yes | 4 | 0/4 | 0.0049 | 52 |  |
| ho-paginate-page-2-items | dual | no | 2 | 2/0 | 0.0010 | 18 |  |
| ho-paginate-page-2-items | s1_only | no | 2 | 2/0 | 0.0002 | 3 |  |
| ho-paginate-page-2-items | stock | yes | 2 | 0/2 | 0.0037 | 47 |  |
| ho-search-no-results | dual | no | 3 | 3/0 | 0.0012 | 14 |  |
| ho-search-no-results | s1_only | no | 3 | 3/0 | 0.0003 | 3 |  |
| ho-search-no-results | stock | yes | 2 | 0/2 | 0.0031 | 35 |  |
| ho-search-rope-price | dual | no | 9 | 9/0 | 0.0033 | 46 |  |
| ho-search-rope-price | s1_only | no | 8 | 8/0 | 0.0008 | 18 |  |
| ho-search-rope-price | stock | yes | 8 | 0/8 | 0.0116 | 133 |  |
