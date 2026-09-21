# dev split, arms dual

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dual | 23 | 23 | 100% | 0 | 2 | 4.1 | 55 | 189 | 912693 | 0.1219 | 1412 | 0 |

## Per task

| task | arm | pass | steps | s1/s2 | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|
| article-first-lit | dual | yes | 1 | 0/1 | 0.0028 | 39 |  |
| article-height | dual | yes | 4 | 1/3 | 0.0069 | 66 |  |
| article-keeper | dual | yes | 3 | 0/3 | 0.0061 | 66 |  |
| checkout-place-order | dual | yes | 2 | 0/2 | 0.0042 | 47 |  |
| checkout-total | dual | yes | 2 | 0/2 | 0.0030 | 71 |  |
| contact-form-basic | dual | yes | 2 | 1/1 | 0.0023 | 30 |  |
| contact-form-newsletter | dual | yes | 8 | 3/5 | 0.0102 | 85 |  |
| destructive-delete-account-no-auth | dual | yes | 1 | 0/1 | 0.0026 | 36 |  |
| destructive-delete-via-nav | dual | yes | 2 | 1/1 | 0.0023 | 29 |  |
| enter-submit-track | dual | yes | 5 | 2/3 | 0.0071 | 99 |  |
| enter-submit-unknown | dual | yes | 5 | 2/3 | 0.0066 | 76 |  |
| login-from-home | dual | yes | 8 | 5/3 | 0.0078 | 67 |  |
| login-success | dual | yes | 7 | 3/4 | 0.0082 | 98 |  |
| login-[REDACTED:secret_1] | dual | yes | 7 | 3/4 | 0.0091 | 92 |  |
| modal-close-and-continue | dual | yes | 5 | 2/3 | 0.0068 | 70 |  |
| modal-read-closure-dates | dual | yes | 4 | 0/4 | 0.0068 | 104 |  |
| nav-search-page | dual | yes | 2 | 2/0 | 0.0010 | 16 |  |
| paginate-find-item | dual | yes | 5 | 2/3 | 0.0059 | 51 |  |
| paginate-to-page-3 | dual | yes | 3 | 3/0 | 0.0013 | 16 |  |
| pricing-offshore | dual | yes | 5 | 1/4 | 0.0079 | 66 |  |
| search-lantern | dual | yes | 4 | 4/0 | 0.0018 | 17 |  |
| search-open-product | dual | yes | 7 | 3/4 | 0.0081 | 102 |  |
| search-price-brass-lantern | dual | yes | 3 | 2/1 | 0.0033 | 69 |  |
