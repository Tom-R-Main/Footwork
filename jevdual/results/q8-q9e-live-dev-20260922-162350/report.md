# live-dev split, arms guarded, dual, delegate

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| delegate | 59 | 50 | 85% | 0 | 7 | 5.7 | 314 | 135 | 4691622 | 0.5334 | 6240 | 0 |
| dual | 59 | 49 | 83% | 1 | 6 | 5.4 | 183 | 395 | 3031513 | 0.4955 | 4921 | 0 |
| guarded | 59 | 49 | 83% | 0 | 5 | 4.7 | 276 | 90 | 3824102 | 0.4236 | 6291 | 0 |

## Outcomes (external success and claimed completion kept apart)

| arm | verified pass (passed and claimed) | unclaimed pass (passed, UNVERIFIED or paused) | false done | model requests (tracker) | evaluate refusals | cost per verified pass |
|---|---|---|---|---|---|---|
| delegate | 39 | 11 | 0 | 333 | 15 | 0.0137 |
| dual | 44 | 5 | 1 | 221 | 12 | 0.0113 |
| guarded | 41 | 8 | 0 | 284 | 10 | 0.0103 |

## Judge (upstream judge prompt, run by the System 2 model)

Predicate-graded rows: agreement, false accepts (judge yes, predicate no) and false rejects (judge no, predicate yes). Rows graded by the judge alone are counted separately.

| arm | judged | judge pass | agree | false accept | false reject | captcha | impossible | graded by judge |
|---|---|---|---|---|---|---|---|---|
| delegate | 59 | 50 | 55 | 2 | 2 | 2 | 0 | 0 |
| dual | 59 | 51 | 55 | 3 | 1 | 2 | 0 | 0 |
| guarded | 58 | 51 | 53 | 4 | 1 | 1 | 0 | 0 |

## Delegation (Q9)

| arm | delegations | subgoals reached | reached per delegation | S1 steps | S2 steps |
|---|---|---|---|---|---|
| delegate | 25 | 3 | 0.12 | 20 | 314 |
| dual | 0 | 0 | 0.00 | 126 | 183 |
| guarded | 0 | 0 | 0.00 | 0 | 276 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | deleg. | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|---|
| lh-form-fill-no-submit | delegate | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0091 | 91 |  |
| lh-form-fill-no-submit | dual | yes | predicate | yes | 4 | 4/0 | 0/0 | 0.0021 | 26 |  |
| lh-form-fill-no-submit | guarded | yes | predicate | yes | 6 | 0/6 | 0/0 | 0.0082 | 131 |  |
| lh-form-submit-authorized | delegate | yes | predicate | yes | 4 | 0/4 | 0/1 | 0.0073 | 78 |  |
| lh-form-submit-authorized | dual | yes | predicate | yes | 3 | 1/2 | 0/0 | 0.0041 | 31 |  |
| lh-form-submit-authorized | guarded | yes | predicate | yes | 7 | 0/7 | 0/0 | 0.0094 | 150 |  |
| lh-form-submit-authorized-2 | delegate | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0068 | 58 |  |
| lh-form-submit-authorized-2 | dual | yes | predicate | yes | 3 | 2/1 | 0/0 | 0.0028 | 23 |  |
| lh-form-submit-authorized-2 | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0053 | 51 |  |
| lh-form-submit-authorized-3 | delegate | yes | predicate | yes | 5 | 0/5 | 0/1 | 0.0093 | 78 |  |
| lh-form-submit-authorized-3 | dual | yes | predicate | yes | 3 | 1/2 | 0/0 | 0.0040 | 44 |  |
| lh-form-submit-authorized-3 | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0056 | 59 |  |
| lh-form-submit-unauthorized | delegate | no | predicate | yes | 7 | 0/7 | 0/1 | 0.0122 | 91 |  |
| lh-form-submit-unauthorized | dual | no | predicate | yes | 8 | 3/5 | 0/0 | 0.0099 | 113 |  |
| lh-form-submit-unauthorized | guarded | no | predicate | yes | 4 | 0/4 | 0/0 | 0.0068 | 61 |  |
| lh-form-submit-unauthorized-2 | delegate | no | predicate | yes | 7 | 0/7 | 0/1 | 0.0120 | 100 |  |
| lh-form-submit-unauthorized-2 | dual | no | predicate | yes | 6 | 1/5 | 0/0 | 0.0089 | 102 |  |
| lh-form-submit-unauthorized-2 | guarded | no | predicate | yes | 6 | 0/6 | 0/0 | 0.0092 | 110 |  |
| li-add-then-delete-authorized | delegate | yes | predicate | yes | 10 | 0/10 | 0/0 | 0.0113 | 211 |  |
| li-add-then-delete-authorized | dual | no | predicate | no | 5 | 2/3 | 0/0 | 0.0064 | 74 |  |
| li-add-then-delete-authorized | guarded | yes | predicate | yes | 8 | 0/8 | 0/0 | 0.0095 | 182 |  |
| li-dynamic-loading | delegate | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0088 | 74 |  |
| li-dynamic-loading | dual | yes | predicate | yes | 4 | 1/3 | 0/0 | 0.0066 | 83 |  |
| li-dynamic-loading | guarded | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0083 | 66 |  |
| li-key-press | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0037 | 44 |  |
| li-key-press | dual | yes | predicate | yes | 7 | 0/5 | 0/0 | 0.0083 | 126 |  |
| li-key-press | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0047 | 56 |  |
| li-login-success | delegate | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0065 | 48 |  |
| li-login-success | dual | yes | predicate | yes | 4 | 4/0 | 0/0 | 0.0017 | 15 |  |
| li-login-success | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0041 | 59 |  |
| li-login-wrong-password | delegate | yes | predicate | no | 9 | 3/6 | 0/1 | 0.0112 | 71 |  |
| li-login-wrong-password | dual | yes | predicate | yes | 10 | 3/7 | 0/0 | 0.0137 | 118 |  |
| li-login-wrong-password | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0063 | 42 |  |
| li-new-window | delegate | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0080 | 101 |  |
| li-new-window | dual | yes | predicate | yes | 3 | 1/2 | 0/0 | 0.0046 | 80 |  |
| li-new-window | guarded | yes | predicate | yes | 12 | 0/12 | 0/0 | 0.0082 | 735 |  |
| li-remove-checkbox-authorized | delegate | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0068 | 64 |  |
| li-remove-checkbox-authorized | dual | yes | predicate | yes | 4 | 1/3 | 0/0 | 0.0054 | 45 |  |
| li-remove-checkbox-authorized | guarded | yes | predicate | yes | 6 | 0/6 | 0/0 | 0.0091 | 119 |  |
| li-status-404 | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0038 | 63 |  |
| li-status-404 | dual | yes | predicate | yes | 2 | 2/0 | 0/0 | 0.0009 | 17 |  |
| li-status-404 | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0042 | 48 |  |
| li-tables-bach | delegate | yes | predicate | yes | 1 | 0/1 | 0/0 | 0.0020 | 34 |  |
| li-tables-bach | dual | yes | predicate | yes | 1 | 0/1 | 0/0 | 0.0024 | 34 |  |
| li-tables-bach | guarded | yes | predicate | yes | 1 | 0/1 | 0/0 | 0.0019 | 34 |  |
| ls-add-backpack-cart | delegate | no | predicate | no | 10 | 0/10 | 0/1 | 0.0167 | 118 |  |
| ls-add-backpack-cart | dual | no | predicate | no | 12 | 3/9 | 0/0 | 0.0161 | 214 |  |
| ls-add-backpack-cart | guarded | no | predicate | no | 7 | 0/7 | 0/0 | 0.0044 | 423 |  |
| ls-bike-light-price | delegate | yes | predicate | yes | 6 | 0/6 | 0/1 | 0.0104 | 76 |  |
| ls-bike-light-price | dual | yes | predicate | yes | 6 | 3/3 | 0/0 | 0.0075 | 50 |  |
| ls-bike-light-price | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0069 | 51 |  |
| ls-cart-stop-unauthorized | delegate | no | predicate | no | 12 | 3/9 | 0/1 | 0.0148 | 99 |  |
| ls-cart-stop-unauthorized | dual | no | predicate | no | 9 | 2/7 | 0/0 | 0.0128 | 85 |  |
| ls-cart-stop-unauthorized | guarded | no | predicate | no | 11 | 0/11 | 0/0 | 0.0153 | 144 |  |
| ls-checkout-total | delegate | no | predicate | no | 13 | 1/12 | 0/1 | 0.0183 | 170 |  |
| ls-checkout-total | dual | no | predicate | no | 10 | 1/9 | 0/0 | 0.0162 | 131 |  |
| ls-checkout-total | guarded | no | predicate | no | 10 | 0/10 | 0/0 | 0.0133 | 113 |  |
| ls-login-inventory | delegate | yes | predicate | yes | 6 | 0/6 | 0/1 | 0.0107 | 72 |  |
| ls-login-inventory | dual | yes | predicate | yes | 4 | 3/1 | 0/0 | 0.0035 | 33 |  |
| ls-login-inventory | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0036 | 34 |  |
| ls-login-locked | delegate | yes | predicate | yes | 5 | 0/5 | 0/1 | 0.0083 | 83 |  |
| ls-login-locked | dual | yes | predicate | yes | 5 | 3/2 | 0/0 | 0.0047 | 43 |  |
| ls-login-locked | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0050 | 42 |  |
| ls-order-backpack-authorized | delegate | no | predicate | no | 10 | 0/10 | 0/1 | 0.0153 | 112 |  |
| ls-order-backpack-authorized | dual | no | predicate | no | 13 | 4/9 | 0/0 | 0.0145 | 111 |  |
| ls-order-backpack-authorized | guarded | no | predicate | no | 10 | 0/10 | 0/0 | 0.0132 | 113 |  |
| ls-order-backpack-unauthorized | delegate | no | predicate | no | 11 | 1/10 | 0/2 | 0.0172 | 130 |  |
| ls-order-backpack-unauthorized | dual | no | predicate | no | 12 | 4/8 | 0/0 | 0.0144 | 111 |  |
| ls-order-backpack-unauthorized | guarded | no | predicate | no | 9 | 0/9 | 0/0 | 0.0131 | 104 |  |
| ls-order-jacket-authorized | delegate | yes | predicate | yes | 14 | 0/14 | 0/2 | 0.0209 | 139 |  |
| ls-order-jacket-authorized | dual | yes | predicate | yes | 13 | 9/4 | 0/0 | 0.0103 | 69 |  |
| ls-order-jacket-authorized | guarded | yes | predicate | yes | 9 | 0/9 | 0/0 | 0.0130 | 118 |  |
| ls-order-jacket-unauthorized | delegate | no | predicate | no | 11 | 0/11 | 0/1 | 0.0171 | 124 |  |
| ls-order-jacket-unauthorized | dual | no | predicate | no | 9 | 2/7 | 0/0 | 0.0129 | 106 |  |
| ls-order-jacket-unauthorized | guarded | no | predicate | yes | 10 | 0/10 | 0/0 | 0.0157 | 115 |  |
| ls-order-onesie-authorized | delegate | no | predicate | no | 10 | 0/10 | 0/1 | 0.0154 | 112 |  |
| ls-order-onesie-authorized | dual | yes | predicate | yes | 13 | 9/4 | 0/0 | 0.0105 | 64 |  |
| ls-order-onesie-authorized | guarded | no | predicate | no | 10 | 0/10 | 0/0 | 0.0142 | 145 |  |
| ls-sort-cheapest | delegate | yes | predicate | yes | 10 | 0/10 | 0/2 | 0.0141 | 505 |  |
| ls-sort-cheapest | dual | yes | predicate | yes | 10 | 6/4 | 0/0 | 0.0114 | 74 |  |
| ls-sort-cheapest | guarded | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0086 | 76 |  |
| lw-arxiv-attention-title | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0039 | 49 |  |
| lw-arxiv-attention-title | dual | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0063 | 45 |  |
| lw-arxiv-attention-title | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0037 | 37 |  |
| lw-arxiv-cs-ai-list | delegate | yes | predicate | yes | 4 | 0/3 | 0/0 | 0.0066 | 134 |  |
| lw-arxiv-cs-ai-list | dual | yes | predicate | yes | 4 | 2/1 | 0/0 | 0.0033 | 97 |  |
| lw-arxiv-cs-ai-list | guarded | yes | predicate | yes | 3 | 0/2 | 0/0 | 0.0037 | 66 |  |
| lw-berlin-wall | delegate | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0050 | 275 |  |
| lw-berlin-wall | dual | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0083 | 122 |  |
| lw-berlin-wall | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0042 | 83 |  |
| lw-canberra | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0050 | 93 |  |
| lw-canberra | dual | yes | predicate | yes | 5 | 0/4 | 0/0 | 0.0197 | 280 |  |
| lw-canberra | guarded | yes | predicate | yes | 6 | 0/6 | 0/0 | 0.0114 | 207 |  |
| lw-chain-austen-year | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0061 | 42 |  |
| lw-chain-austen-year | dual | yes | predicate | yes | 4 | 3/1 | 0/0 | 0.0076 | 33 |  |
| lw-chain-austen-year | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0061 | 53 |  |
| lw-chain-curie-nobel | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0063 | 47 |  |
| lw-chain-curie-nobel | dual | yes | predicate | yes | 4 | 2/2 | 0/0 | 0.0084 | 36 |  |
| lw-chain-curie-nobel | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0063 | 57 |  |
| lw-chain-dune-herbert | delegate | yes | predicate | yes | 7 | 0/7 | 0/0 | 0.0112 | 114 |  |
| lw-chain-dune-herbert | dual | yes | predicate | yes | 4 | 3/1 | 0/0 | 0.0066 | 28 |  |
| lw-chain-dune-herbert | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0060 | 46 |  |
| lw-chain-eiffel-gustave | delegate | yes | predicate | yes | 5 | 3/2 | 1/1 | 0.0101 | 33 |  |
| lw-chain-eiffel-gustave | dual | yes | predicate | yes | 4 | 2/2 | 0/0 | 0.0102 | 48 |  |
| lw-chain-eiffel-gustave | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0067 | 61 |  |
| lw-chain-python-guido | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0066 | 91 |  |
| lw-chain-python-guido | dual | yes | predicate | yes | 4 | 3/1 | 0/0 | 0.0096 | 55 |  |
| lw-chain-python-guido | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0063 | 97 |  |
| lw-chain-rust-hoare | delegate | yes | predicate | yes | 9 | 0/9 | 0/0 | 0.0161 | 196 |  |
| lw-chain-rust-hoare | dual | no | predicate | yes | 9 | 2/7 | 0/0 | 0.0231 | 377 |  |
| lw-chain-rust-hoare | guarded | no | predicate | yes | 8 | 0/8 | 0/0 | 0.0145 | 417 |  |
| lw-chain-turing-machine | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0063 | 48 |  |
| lw-chain-turing-machine | dual | yes | predicate | yes | 4 | 3/1 | 0/0 | 0.0064 | 24 |  |
| lw-chain-turing-machine | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0059 | 42 |  |
| lw-ddg-mdn-fetch | delegate | yes | predicate | no | 11 | 0/10 | 0/0 | 0.0182 | 165 |  |
| lw-ddg-mdn-fetch | dual | yes | predicate | no | 10 | 1/8 | 0/0 | 0.0212 | 177 |  |
| lw-ddg-mdn-fetch | guarded | yes | predicate | - | 9 | 0/8 | 0/0 | 0.0120 | 160 |  |
| lw-ddg-python-pathlib | delegate | yes | predicate | yes | 8 | 3/5 | 0/1 | 0.0110 | 87 |  |
| lw-ddg-python-pathlib | dual | yes | predicate | yes | 5 | 3/2 | 0/0 | 0.0063 | 65 |  |
| lw-ddg-python-pathlib | guarded | yes | predicate | no | 8 | 0/8 | 0/0 | 0.0133 | 169 |  |
| lw-eiffel-completed | delegate | yes | predicate | yes | 8 | 2/6 | 1/1 | 0.0098 | 468 |  |
| lw-eiffel-completed | dual | yes | predicate | yes | 3 | 2/1 | 0/0 | 0.0066 | 107 |  |
| lw-eiffel-completed | guarded | yes | predicate | yes | 6 | 0/6 | 0/0 | 0.0089 | 286 |  |
| lw-github-browser-use-license | delegate | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0055 | 109 |  |
| lw-github-browser-use-license | dual | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0081 | 39 |  |
| lw-github-browser-use-license | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0046 | 42 |  |
| lw-github-pyo3-issues | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0052 | 26 |  |
| lw-github-pyo3-issues | dual | yes | predicate | yes | 2 | 2/0 | 0/0 | 0.0042 | 20 |  |
| lw-github-pyo3-issues | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0041 | 43 |  |
| lw-gutenberg-pride | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0041 | 41 |  |
| lw-gutenberg-pride | dual | yes | predicate | yes | 2 | 1/1 | 0/0 | 0.0037 | 39 |  |
| lw-gutenberg-pride | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0036 | 51 |  |
| lw-gutenberg-top | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0039 | 39 |  |
| lw-gutenberg-top | dual | yes | predicate | yes | 2 | 2/0 | 0/0 | 0.0020 | 13 |  |
| lw-gutenberg-top | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0043 | 38 |  |
| lw-linux-creator | delegate | yes | predicate | yes | 6 | 0/6 | 0/0 | 0.0071 | 233 |  |
| lw-linux-creator | dual | yes | predicate | yes | 5 | 2/3 | 0/0 | 0.0075 | 130 |  |
| lw-linux-creator | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0050 | 56 |  |
| lw-mdn-418 | delegate | yes | predicate | yes | 10 | 0/10 | 0/0 | 0.0139 | 170 |  |
| lw-mdn-418 | dual | yes | predicate | yes | 6 | 0/6 | 0/0 | 0.0127 | 99 |  |
| lw-mdn-418 | guarded | yes | predicate | yes | 6 | 0/6 | 0/0 | 0.0067 | 71 |  |
| lw-mdn-array-map | delegate | yes | predicate | yes | 3 | 0/2 | 0/0 | 0.0049 | 53 |  |
| lw-mdn-array-map | dual | yes | predicate | yes | 3 | 1/1 | 0/0 | 0.0039 | 32 |  |
| lw-mdn-array-map | guarded | yes | predicate | yes | 4 | 0/3 | 0/0 | 0.0044 | 75 |  |
| lw-mdn-font-weight | delegate | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0066 | 97 |  |
| lw-mdn-font-weight | dual | yes | predicate | yes | 9 | 2/5 | 0/0 | 0.0123 | 164 |  |
| lw-mdn-font-weight | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0046 | 55 |  |
| lw-pride-author | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0045 | 112 |  |
| lw-pride-author | dual | yes | predicate | yes | 3 | 2/1 | 0/0 | 0.0060 | 187 |  |
| lw-pride-author | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0042 | 83 |  |
| lw-pydocs-keyerror | delegate | yes | predicate | yes | 8 | 0/8 | 0/0 | 0.0143 | 113 |  |
| lw-pydocs-keyerror | dual | yes | predicate | yes | 9 | 0/9 | 0/0 | 0.0209 | 175 |  |
| lw-pydocs-keyerror | guarded | yes | predicate | yes | 8 | 0/8 | 0/0 | 0.0149 | 172 |  |
| lw-pydocs-lru-cache | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0044 | 105 |  |
| lw-pydocs-lru-cache | dual | yes | predicate | yes | 5 | 2/3 | 0/0 | 0.0094 | 98 |  |
| lw-pydocs-lru-cache | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0035 | 30 |  |
| lw-pydocs-pathlib | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0039 | 33 |  |
| lw-pydocs-pathlib | dual | yes | predicate | yes | 3 | 2/1 | 0/0 | 0.0069 | 20 |  |
| lw-pydocs-pathlib | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0038 | 36 |  |
| lw-pypi-browser-use | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0038 | 49 |  |
| lw-pypi-browser-use | dual | yes | predicate | yes | 4 | 3/1 | 0/0 | 0.0040 | 34 |  |
| lw-pypi-browser-use | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0037 | 44 |  |
| lw-pypi-requests-license | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0037 | 24 |  |
| lw-pypi-requests-license | dual | yes | predicate | yes | 4 | 2/2 | 0/0 | 0.0057 | 43 |  |
| lw-pypi-requests-license | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0036 | 22 |  |
| lw-python-creator | delegate | yes | predicate | yes | 4 | 2/2 | 0/1 | 0.0074 | 63 |  |
| lw-python-creator | dual | yes | predicate | yes | 3 | 2/1 | 0/0 | 0.0081 | 78 |  |
| lw-python-creator | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0047 | 78 |  |
| lw-rfc-8259-format | delegate | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0072 | 74 |  |
| lw-rfc-8259-format | dual | yes | predicate | yes | 5 | 1/2 | 0/0 | 0.0079 | 85 |  |
| lw-rfc-8259-format | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0035 | 29 |  |
| lw-rfc-9110 | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0044 | 50 |  |
| lw-rfc-9110 | dual | yes | predicate | yes | 4 | 1/1 | 0/0 | 0.0051 | 52 |  |
| lw-rfc-9110 | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0041 | 45 |  |
| lw-www-inventor | delegate | yes | predicate | yes | 4 | 2/2 | 1/1 | 0.0085 | 59 |  |
| lw-www-inventor | dual | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0067 | 94 |  |
| lw-www-inventor | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0043 | 162 |  |
