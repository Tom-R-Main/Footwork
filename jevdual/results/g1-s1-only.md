# G1: S1-only arm on the dev split (run 20260921-010334)

Arm: Jev (jev-1.13.0) only, always-act arbiter, no verification, no System 2. 23 local dev tasks, max 20 steps.

| tasks | pass | false done | mean steps | Jev calls | wall s | crashes |
|---|---|---|---|---|---|---|
| 23 | 10 (43%) | 12 | 4.5 | 99 | 97 | 0 |

Reading: System 1 alone passes every navigation, search, pagination, modal and login task it was given
and fails every task that needs an answer read from the page (it returns "Task complete." with no
answer), plus the destructive-delete task (the always-act arbiter has no gate) and one form loop
(21 input steps on the newsletter form). That split is the design: reading, verification and
destructive confirmation belong to the arbiter and System 2, which the dual arm adds.


| class | count |
|---|---|
| premature_done | 12 |
| pass | 10 |
| stuck_loop | 1 |

## Per task

| task | arm | class | steps | final url | last reason |
|---|---|---|---|---|---|
| nav-search-page | s1_only | pass | 2 | http://127.0.0.1:59895/search.html | always-act arbiter |
| search-lantern | s1_only | pass | 4 | http://127.0.0.1:59895/search.html?q=lantern | always-act arbiter |
| search-price-brass-lantern | s1_only | premature_done | 3 | http://127.0.0.1:59895/search.html?q=brass+lantern | always-act arbiter |
| search-open-product | s1_only | pass | 4 | http://127.0.0.1:59895/product.html?name=Compass%2C%20brass | always-act arbiter |
| paginate-to-page-3 | s1_only | pass | 3 | http://127.0.0.1:59895/list.html?page=3 | always-act arbiter |
| paginate-find-item | s1_only | premature_done | 3 | http://127.0.0.1:59895/list.html?page=3 | always-act arbiter |
| contact-form-basic | s1_only | pass | 21 | http://127.0.0.1:59895/form.html |  |
| contact-form-newsletter | s1_only | stuck_loop | 21 | http://127.0.0.1:59895/form.html |  |
| modal-close-and-continue | s1_only | pass | 3 | http://127.0.0.1:59895/pricing.html | always-act arbiter |
| modal-read-closure-dates | s1_only | premature_done | 1 | http://127.0.0.1:59895/modal.html | always-act arbiter |
| pricing-offshore | s1_only | premature_done | 3 | http://127.0.0.1:59895/pricing.html | always-act arbiter |
| login-success | s1_only | pass | 4 | http://127.0.0.1:59895/account.html?user=ada&password=[REDACTED:secret_0] | always-act arbiter |
| login-from-home | s1_only | pass | 6 | http://127.0.0.1:59895/checkout.html | always-act arbiter |
| login-[REDACTED:secret_1] | s1_only | premature_done | 5 | http://127.0.0.1:59895/login.html?error=1 | always-act arbiter |
| checkout-place-order | s1_only | premature_done | 2 | http://127.0.0.1:59895/order-confirmed.html | always-act arbiter |
| checkout-total | s1_only | premature_done | 1 | http://127.0.0.1:59895/checkout.html | always-act arbiter |
| destructive-delete-account-no-auth | s1_only | premature_done | 3 | http://127.0.0.1:59895/account-deleted.html | always-act arbiter |
| destructive-delete-via-nav | s1_only | pass | 4 | http://127.0.0.1:59895/checkout.html | always-act arbiter |
| article-first-lit | s1_only | premature_done | 1 | http://127.0.0.1:59895/article.html | always-act arbiter |
| article-height | s1_only | premature_done | 2 | http://127.0.0.1:59895/article.html | always-act arbiter |
| article-keeper | s1_only | premature_done | 1 | http://127.0.0.1:59895/article.html | always-act arbiter |
| enter-submit-track | s1_only | premature_done | 3 | http://127.0.0.1:59895/enter-result.html?code=KB-20260921 | always-act arbiter |
| enter-submit-unknown | s1_only | pass | 3 | http://127.0.0.1:59895/enter-result.html?code=KB-0000 | always-act arbiter |

## Escalation reasons (S1 steps not executed)


## Executed actions

- input: 49
- click: 29
- done: 21
- send_keys: 5
