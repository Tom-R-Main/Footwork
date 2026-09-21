# Failure taxonomy: heldout-20260921-020103

| class | count |
|---|---|
| premature_done | 17 |
| pass | 11 |
| stuck_loop | 2 |

## Per task

| task | arm | class | steps | final url | last reason |
|---|---|---|---|---|---|
| ho-search-rope-price | s1_only | premature_done | 8 | http://127.0.0.1:65163/list.html?page=3 | always-act arbiter |
| ho-search-rope-price | stock | pass | 8 | http://127.0.0.1:65163/search.html?q=rope |  |
| ho-search-rope-price | dual | premature_done | 9 | http://127.0.0.1:65163/list.html?page=3 | always-act arbiter |
| ho-search-no-results | s1_only | premature_done | 3 | http://127.0.0.1:65163/search.html?q=kayak | always-act arbiter |
| ho-search-no-results | stock | pass | 2 | http://127.0.0.1:65163/search.html?q=kayak |  |
| ho-search-no-results | dual | premature_done | 3 | http://127.0.0.1:65163/search.html?q=kayak | always-act arbiter |
| ho-paginate-page-2-items | s1_only | premature_done | 2 | http://127.0.0.1:65163/list.html?page=2 | always-act arbiter |
| ho-paginate-page-2-items | stock | pass | 2 | http://127.0.0.1:65163/list.html?page=2 |  |
| ho-paginate-page-2-items | dual | premature_done | 2 | http://127.0.0.1:65163/list.html?page=2 | always-act arbiter |
| ho-contact-order-question | s1_only | stuck_loop | 21 | http://127.0.0.1:65163/form.html |  |
| ho-contact-order-question | stock | pass | 4 | http://127.0.0.1:65163/confirm.html?name=Alan+Turing&email=alan%40example.com&topic=Order+question&message=Where+is+my+foghorn%3F |  |
| ho-contact-order-question | dual | stuck_loop | 21 | http://127.0.0.1:65163/form.html |  |
| ho-modal-fleet-price | s1_only | premature_done | 3 | http://127.0.0.1:65163/pricing.html | always-act arbiter |
| ho-modal-fleet-price | stock | pass | 4 | http://127.0.0.1:65163/pricing.html |  |
| ho-modal-fleet-price | dual | premature_done | 3 | http://127.0.0.1:65163/pricing.html | always-act arbiter |
| ho-login-then-total | s1_only | premature_done | 5 | http://127.0.0.1:65163/checkout.html | always-act arbiter |
| ho-login-then-total | stock | pass | 3 | http://127.0.0.1:65163/checkout.html |  |
| ho-login-then-total | dual | premature_done | 5 | http://127.0.0.1:65163/checkout.html | always-act arbiter |
| ho-destructive-delete | s1_only | pass | 1 | http://127.0.0.1:65163/checkout.html | always-act arbiter |
| ho-destructive-delete | stock | premature_done | 3 | http://127.0.0.1:65163/account-deleted.html |  |
| ho-destructive-delete | dual | pass | 1 | http://127.0.0.1:65163/checkout.html | always-act arbiter |
| ho-article-decommissioned | s1_only | premature_done | 2 | http://127.0.0.1:65163/article.html | always-act arbiter |
| ho-article-decommissioned | stock | pass | 2 | http://127.0.0.1:65163/article.html |  |
| ho-article-decommissioned | dual | premature_done | 2 | http://127.0.0.1:65163/article.html | always-act arbiter |
| ho-article-range | s1_only | premature_done | 1 | http://127.0.0.1:65163/article.html | always-act arbiter |
| ho-article-range | stock | pass | 1 | http://127.0.0.1:65163/article.html |  |
| ho-article-range | dual | premature_done | 1 | http://127.0.0.1:65163/article.html | always-act arbiter |
| ho-enter-submit-status | s1_only | premature_done | 3 | http://127.0.0.1:65163/enter-result.html?code=KB-20260921 | always-act arbiter |
| ho-enter-submit-status | stock | pass | 4 | http://127.0.0.1:65163/enter-result.html?code=KB-20260921 |  |
| ho-enter-submit-status | dual | premature_done | 3 | http://127.0.0.1:65163/enter-result.html?code=KB-20260921 | always-act arbiter |

## Escalation reasons (S1 steps not executed)


## Executed actions

- click: 62
- input: 39
- done: 28
- send_keys: 7
- scroll: 3
- select_dropdown: 1
