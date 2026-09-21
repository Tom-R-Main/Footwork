# dev split, arms dual

| arm | tasks | pass | pass rate | false done | mean steps | LLM calls | Jev calls | LLM tokens | cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|
| dual | 23 | 22 | 96% | 1 | 3.0 | 31 | 39 | 522775 | 0.0625 | 987 | 0 |

## Per task

| task | arm | pass | steps | s1/s2 | cost USD | wall s | error |
|---|---|---|---|---|---|---|---|
| article-first-lit | dual | yes | 1 | 0/1 | 0.0020 | 40 |  |
| article-height | dual | yes | 2 | 1/1 | 0.0020 | 20 |  |
| article-keeper | dual | yes | 1 | 0/1 | 0.0020 | 37 |  |
| checkout-place-order | dual | yes | 2 | 0/2 | 0.0045 | 87 |  |
| checkout-total | dual | yes | 1 | 0/1 | 0.0019 | 36 |  |
| contact-form-basic | dual | yes | 1 | 0/1 | 0.0018 | 24 |  |
| contact-form-newsletter | dual | no | 8 | 4/4 | 0.0064 | 73 |  |
| destructive-delete-account-no-auth | dual | yes | 1 | 0/1 | 0.0017 | 24 |  |
| destructive-delete-via-nav | dual | yes | 2 | 1/1 | 0.0023 | 42 |  |
| enter-submit-track | dual | yes | 3 | 2/1 | 0.0032 | 61 |  |
| enter-submit-unknown | dual | yes | 3 | 2/1 | 0.0030 | 45 |  |
| login-from-home | dual | yes | 6 | 5/1 | 0.0033 | 27 |  |
| login-success | dual | yes | 5 | 2/3 | 0.0043 | 88 |  |
| login-[REDACTED:secret_1] | dual | yes | 5 | 3/2 | 0.0043 | 52 |  |
| modal-close-and-continue | dual | yes | 3 | 2/1 | 0.0025 | 30 |  |
| modal-read-closure-dates | dual | yes | 2 | 0/2 | 0.0024 | 67 |  |
| nav-search-page | dual | yes | 2 | 2/0 | 0.0009 | 15 |  |
| paginate-find-item | dual | yes | 3 | 2/1 | 0.0025 | 30 |  |
| paginate-to-page-3 | dual | yes | 3 | 3/0 | 0.0012 | 15 |  |
| pricing-offshore | dual | yes | 4 | 1/3 | 0.0037 | 55 |  |
| search-lantern | dual | yes | 4 | 4/0 | 0.0015 | 20 |  |
| search-open-product | dual | yes | 5 | 3/2 | 0.0030 | 64 |  |
| search-price-brass-lantern | dual | yes | 3 | 2/1 | 0.0024 | 35 |  |
