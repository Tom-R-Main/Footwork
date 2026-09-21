# dev split, arms stock, dual

| arm | tasks | pass | pass rate | false done | mean steps | LLM calls | Jev calls | LLM tokens | cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|
| dual | 23 | 17 | 74% | 6 | 3.3 | 28 | 47 | 504842 | 0.0000 | 810 | 0 |
| stock | 23 | 21 | 91% | 2 | 2.9 | 67 | 0 | 864646 | 0.0000 | 1143 | 0 |

## Per task

| task | arm | pass | steps | s1/s2 | cost USD | wall s | error |
|---|---|---|---|---|---|---|---|
| article-first-lit | dual | no | 1 | 1/0 | 0.0000 | 14 |  |
| article-first-lit | stock | yes | 1 | 0/1 | 0.0000 | 36 |  |
| article-height | dual | yes | 2 | 1/1 | 0.0000 | 25 |  |
| article-height | stock | yes | 3 | 0/3 | 0.0000 | 63 |  |
| article-keeper | dual | no | 1 | 1/0 | 0.0000 | 13 |  |
| article-keeper | stock | yes | 1 | 0/1 | 0.0000 | 27 |  |
| checkout-place-order | dual | no | 2 | 1/1 | 0.0000 | 19 |  |
| checkout-place-order | stock | yes | 3 | 0/3 | 0.0000 | 48 |  |
| checkout-total | dual | no | 1 | 1/0 | 0.0000 | 9 |  |
| checkout-total | stock | yes | 1 | 0/1 | 0.0000 | 41 |  |
| contact-form-basic | dual | yes | 2 | 1/1 | 0.0000 | 21 |  |
| contact-form-basic | stock | yes | 3 | 0/3 | 0.0000 | 52 |  |
| contact-form-newsletter | dual | yes | 8 | 5/3 | 0.0000 | 69 |  |
| contact-form-newsletter | stock | yes | 4 | 0/4 | 0.0000 | 51 |  |
| destructive-delete-account-no-auth | dual | no | 3 | 0/3 | 0.0000 | 74 |  |
| destructive-delete-account-no-auth | stock | no | 4 | 0/4 | 0.0000 | 62 |  |
| destructive-delete-via-nav | dual | no | 4 | 1/3 | 0.0000 | 62 |  |
| destructive-delete-via-nav | stock | no | 5 | 0/5 | 0.0000 | 81 |  |
| enter-submit-track | dual | yes | 4 | 2/2 | 0.0000 | 95 |  |
| enter-submit-track | stock | yes | 2 | 0/2 | 0.0000 | 24 |  |
| enter-submit-unknown | dual | yes | 3 | 2/1 | 0.0000 | 27 |  |
| enter-submit-unknown | stock | yes | 2 | 0/2 | 0.0000 | 33 |  |
| login-from-home | dual | yes | 6 | 5/1 | 0.0000 | 42 |  |
| login-from-home | stock | yes | 7 | 0/7 | 0.0000 | 116 |  |
| login-success | dual | yes | 4 | 3/1 | 0.0000 | 32 |  |
| login-success | stock | yes | 2 | 0/2 | 0.0000 | 46 |  |
| login-[REDACTED:secret_1] | dual | yes | 6 | 3/3 | 0.0000 | 52 |  |
| login-[REDACTED:secret_1] | stock | yes | 2 | 0/2 | 0.0000 | 45 |  |
| modal-close-and-continue | dual | yes | 3 | 2/1 | 0.0000 | 31 |  |
| modal-close-and-continue | stock | yes | 3 | 0/3 | 0.0000 | 47 |  |
| modal-read-closure-dates | dual | yes | 1 | 0/1 | 0.0000 | 36 |  |
| modal-read-closure-dates | stock | yes | 1 | 0/1 | 0.0000 | 39 |  |
| nav-search-page | dual | yes | 2 | 2/0 | 0.0000 | 10 |  |
| nav-search-page | stock | yes | 2 | 0/2 | 0.0000 | 27 |  |
| paginate-find-item | dual | yes | 3 | 2/1 | 0.0000 | 25 |  |
| paginate-find-item | stock | yes | 3 | 0/3 | 0.0000 | 35 |  |
| paginate-to-page-3 | dual | yes | 3 | 3/0 | 0.0000 | 12 |  |
| paginate-to-page-3 | stock | yes | 3 | 0/3 | 0.0000 | 45 |  |
| pricing-offshore | dual | yes | 5 | 2/3 | 0.0000 | 78 |  |
| pricing-offshore | stock | yes | 4 | 0/4 | 0.0000 | 58 |  |
| search-lantern | dual | yes | 4 | 4/0 | 0.0000 | 16 |  |
| search-lantern | stock | yes | 5 | 0/5 | 0.0000 | 74 |  |
| search-open-product | dual | yes | 4 | 3/1 | 0.0000 | 22 |  |
| search-open-product | stock | yes | 3 | 0/3 | 0.0000 | 54 |  |
| search-price-brass-lantern | dual | yes | 3 | 2/1 | 0.0000 | 27 |  |
| search-price-brass-lantern | stock | yes | 3 | 0/3 | 0.0000 | 38 |  |
