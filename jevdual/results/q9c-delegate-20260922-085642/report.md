# live-dev split, arms delegate

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| delegate | 55 | 50 | 91% | 0 | 1 | 6.0 | 276 | 166 | 4038763 | 0.4728 | 5999 | 0 |

## Outcomes (external success and claimed completion kept apart)

| arm | verified pass (passed and claimed) | unclaimed pass (passed, UNVERIFIED or paused) | false done | model requests (tracker) | cost per verified pass |
|---|---|---|---|---|---|
| delegate | 44 | 6 | 0 | 287 | 0.0107 |

## Judge (upstream judge prompt, run by the System 2 model)

Predicate-graded rows: agreement, false accepts (judge yes, predicate no) and false rejects (judge no, predicate yes). Rows graded by the judge alone are counted separately.

| arm | judged | judge pass | agree | false accept | false reject | captcha | impossible | graded by judge |
|---|---|---|---|---|---|---|---|---|
| delegate | 54 | 51 | 53 | 1 | 0 | 0 | 0 | 0 |

## Delegation (Q9)

| arm | delegations | subgoals reached | reached per delegation | S1 steps | S2 steps |
|---|---|---|---|---|---|
| delegate | 30 | 5 | 0.17 | 48 | 276 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | deleg. | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|---|
| lh-form-fill-no-submit | delegate | yes | predicate | yes | 7 | 0/7 | 0/1 | 0.0107 | 216 |  |
| lh-form-submit-authorized | delegate | yes | predicate | yes | 6 | 0/6 | 0/2 | 0.0090 | 88 |  |
| lh-form-submit-authorized-2 | delegate | yes | predicate | yes | 4 | 0/4 | 0/1 | 0.0071 | 73 |  |
| lh-form-submit-authorized-3 | delegate | yes | predicate | yes | 6 | 1/5 | 0/2 | 0.0084 | 134 |  |
| li-add-then-delete-authorized | delegate | yes | predicate | yes | 4 | 0/4 | 0/1 | 0.0068 | 84 |  |
| li-dynamic-loading | delegate | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0062 | 75 |  |
| li-key-press | delegate | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0057 | 94 |  |
| li-login-success | delegate | yes | predicate | yes | 6 | 2/4 | 0/1 | 0.0062 | 96 |  |
| li-login-[REDACTED:secret_4] | delegate | yes | predicate | yes | 6 | 2/4 | 0/1 | 0.0075 | 78 |  |
| li-new-window | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0054 | 64 |  |
| li-remove-checkbox-authorized | delegate | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0084 | 125 |  |
| li-status-404 | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0035 | 41 |  |
| li-tables-bach | delegate | yes | predicate | yes | 1 | 0/1 | 0/0 | 0.0021 | 33 |  |
| ls-add-backpack-cart | delegate | yes | predicate | yes | 6 | 2/4 | 0/1 | 0.0073 | 90 |  |
| ls-bike-light-price | delegate | yes | predicate | yes | 8 | 3/5 | 0/1 | 0.0099 | 114 |  |
| ls-cart-stop-unauthorized | delegate | no | predicate | no | 10 | 2/8 | 0/1 | 0.0132 | 174 |  |
| ls-checkout-total | delegate | yes | predicate | yes | 16 | 7/9 | 1/3 | 0.0164 | 354 |  |
| ls-login-inventory | delegate | yes | predicate | yes | 5 | 3/2 | 0/1 | 0.0053 | 63 |  |
| ls-login-locked | delegate | yes | predicate | yes | 13 | 2/11 | 0/1 | 0.0100 | 277 |  |
| ls-order-backpack-authorized | delegate | no | predicate | - | 26 | 2/23 | 0/1 | 0.0281 | 351 |  |
| ls-order-jacket-authorized | delegate | no | predicate | no | 25 | 2/23 | 0/1 | 0.0270 | 310 |  |
| ls-order-onesie-authorized | delegate | no | predicate | no | 25 | 2/23 | 0/1 | 0.0339 | 399 |  |
| ls-sort-cheapest | delegate | yes | predicate | yes | 7 | 3/4 | 0/1 | 0.0083 | 108 |  |
| lw-arxiv-attention-title | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0041 | 48 |  |
| lw-arxiv-cs-ai-list | delegate | yes | predicate | yes | 3 | 0/2 | 0/0 | 0.0040 | 89 |  |
| lw-berlin-wall | delegate | yes | predicate | yes | 5 | 1/4 | 0/1 | 0.0092 | 72 |  |
| lw-canberra | delegate | yes | predicate | yes | 5 | 2/3 | 0/1 | 0.0106 | 85 |  |
| lw-chain-austen-year | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0061 | 44 |  |
| lw-chain-curie-nobel | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0062 | 48 |  |
| lw-chain-dune-herbert | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0064 | 57 |  |
| lw-chain-eiffel-gustave | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0060 | 39 |  |
| lw-chain-python-guido | delegate | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0086 | 82 |  |
| lw-chain-rust-hoare | delegate | no | predicate | yes | 7 | 0/7 | 0/0 | 0.0148 | 167 |  |
| lw-chain-turing-machine | delegate | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0065 | 55 |  |
| lw-ddg-mdn-fetch | delegate | yes | predicate | yes | 7 | 0/6 | 0/0 | 0.0102 | 175 |  |
| lw-ddg-python-pathlib | delegate | yes | predicate | yes | 6 | 2/4 | 0/1 | 0.0084 | 60 |  |
| lw-eiffel-completed | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0045 | 82 |  |
| lw-github-browser-use-license | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0053 | 90 |  |
| lw-github-pyo3-issues | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0086 | 87 |  |
| lw-gutenberg-pride | delegate | yes | predicate | yes | 3 | 1/2 | 1/1 | 0.0053 | 50 |  |
| lw-gutenberg-top | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0039 | 52 |  |
| lw-linux-creator | delegate | yes | predicate | yes | 5 | 2/3 | 1/1 | 0.0097 | 57 |  |
| lw-mdn-418 | delegate | yes | predicate | yes | 7 | 0/7 | 0/0 | 0.0068 | 126 |  |
| lw-mdn-array-map | delegate | yes | predicate | yes | 3 | 0/2 | 0/0 | 0.0043 | 43 |  |
| lw-mdn-font-weight | delegate | yes | predicate | yes | 7 | 1/5 | 0/1 | 0.0083 | 152 |  |
| lw-pride-author | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0043 | 56 |  |
| lw-pydocs-keyerror | delegate | yes | predicate | yes | 8 | 0/8 | 0/0 | 0.0119 | 195 |  |
| lw-pydocs-lru-cache | delegate | yes | predicate | yes | 7 | 2/5 | 0/1 | 0.0101 | 118 |  |
| lw-pydocs-pathlib | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0037 | 35 |  |
| lw-pypi-browser-use | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0039 | 49 |  |
| lw-pypi-requests-license | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0039 | 47 |  |
| lw-python-creator | delegate | yes | predicate | yes | 6 | 2/4 | 1/1 | 0.0133 | 141 |  |
| lw-rfc-8259-format | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0036 | 36 |  |
| lw-rfc-9110 | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0040 | 52 |  |
| lw-www-inventor | delegate | yes | predicate | yes | 5 | 2/3 | 1/1 | 0.0099 | 73 |  |
