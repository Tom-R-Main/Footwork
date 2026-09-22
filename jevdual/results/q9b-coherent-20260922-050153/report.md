# live-dev split, arms guarded, dual, delegate

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| delegate | 55 | 50 | 91% | 0 | 3 | 4.4 | 237 | 80 | 3511973 | 0.3842 | 4815 | 0 |
| dual | 55 | 52 | 95% | 0 | 2 | 5.2 | 161 | 360 | 2736852 | 0.4485 | 4386 | 0 |
| guarded | 55 | 52 | 95% | 0 | 2 | 4.2 | 226 | 84 | 3489728 | 0.3853 | 4789 | 0 |

## Outcomes (external success and claimed completion kept apart)

| arm | verified pass (passed and claimed) | unclaimed pass (passed, UNVERIFIED or paused) | false done | model requests (tracker) | cost per verified pass |
|---|---|---|---|---|---|
| delegate | 43 | 7 | 0 | 260 | 0.0089 |
| dual | 45 | 7 | 0 | 203 | 0.0100 |
| guarded | 45 | 7 | 0 | 264 | 0.0086 |

## Judge (upstream judge prompt, run by the System 2 model)

Predicate-graded rows: agreement, false accepts (judge yes, predicate no) and false rejects (judge no, predicate yes). Rows graded by the judge alone are counted separately.

| arm | judged | judge pass | agree | false accept | false reject | captcha | impossible | graded by judge |
|---|---|---|---|---|---|---|---|---|
| delegate | 55 | 51 | 54 | 1 | 0 | 0 | 0 | 0 |
| dual | 54 | 51 | 54 | 0 | 0 | 0 | 0 | 0 |
| guarded | 55 | 53 | 54 | 1 | 0 | 0 | 0 | 0 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | deleg. | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|---|
| lh-form-fill-no-submit | delegate | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0071 | 95 |  |
| lh-form-fill-no-submit | dual | yes | predicate | yes | 4 | 4/0 | 0/0 | 0.0021 | 27 |  |
| lh-form-fill-no-submit | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0070 | 99 |  |
| lh-form-submit-authorized | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0050 | 55 |  |
| lh-form-submit-authorized | dual | yes | predicate | yes | 3 | 1/2 | 0/0 | 0.0041 | 43 |  |
| lh-form-submit-authorized | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0051 | 72 |  |
| lh-form-submit-authorized-2 | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0049 | 50 |  |
| lh-form-submit-authorized-2 | dual | yes | predicate | yes | 3 | 1/2 | 0/0 | 0.0043 | 60 |  |
| lh-form-submit-authorized-2 | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0051 | 80 |  |
| lh-form-submit-authorized-3 | delegate | yes | predicate | yes | 7 | 0/7 | 0/0 | 0.0094 | 173 |  |
| lh-form-submit-authorized-3 | dual | yes | predicate | yes | 3 | 1/2 | 0/0 | 0.0041 | 47 |  |
| lh-form-submit-authorized-3 | guarded | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0080 | 75 |  |
| li-add-then-delete-authorized | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0049 | 62 |  |
| li-add-then-delete-authorized | dual | yes | predicate | yes | 12 | 2/10 | 0/0 | 0.0169 | 398 |  |
| li-add-then-delete-authorized | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0048 | 87 |  |
| li-dynamic-loading | delegate | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0066 | 86 |  |
| li-dynamic-loading | dual | yes | predicate | yes | 4 | 1/3 | 0/0 | 0.0056 | 78 |  |
| li-dynamic-loading | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0069 | 105 |  |
| li-key-press | delegate | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0069 | 118 |  |
| li-key-press | dual | yes | predicate | yes | 6 | 0/4 | 0/0 | 0.0086 | 136 |  |
| li-key-press | guarded | yes | predicate | yes | 6 | 0/6 | 0/0 | 0.0083 | 111 |  |
| li-login-success | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0033 | 36 |  |
| li-login-success | dual | yes | predicate | yes | 4 | 4/0 | 0/0 | 0.0017 | 24 |  |
| li-login-success | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0049 | 71 |  |
| li-login-[REDACTED:secret_4] | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0050 | 62 |  |
| li-login-[REDACTED:secret_4] | dual | yes | predicate | yes | 7 | 3/4 | 0/0 | 0.0070 | 132 |  |
| li-login-[REDACTED:secret_4] | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0048 | 74 |  |
| li-new-window | delegate | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0076 | 163 |  |
| li-new-window | dual | yes | predicate | yes | 3 | 2/1 | 0/0 | 0.0025 | 33 |  |
| li-new-window | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0068 | 110 |  |
| li-remove-checkbox-authorized | delegate | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0066 | 106 |  |
| li-remove-checkbox-authorized | dual | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0089 | 128 |  |
| li-remove-checkbox-authorized | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0064 | 81 |  |
| li-status-404 | delegate | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0042 | 116 |  |
| li-status-404 | dual | yes | predicate | yes | 2 | 2/0 | 0/0 | 0.0010 | 18 |  |
| li-status-404 | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0038 | 83 |  |
| li-tables-bach | delegate | yes | predicate | yes | 1 | 0/1 | 0/0 | 0.0019 | 30 |  |
| li-tables-bach | dual | yes | predicate | yes | 1 | 0/1 | 0/0 | 0.0025 | 44 |  |
| li-tables-bach | guarded | yes | predicate | yes | 1 | 0/1 | 0/0 | 0.0021 | 44 |  |
| ls-add-backpack-cart | delegate | no | predicate | no | 7 | 0/7 | 0/0 | 0.0105 | 139 |  |
| ls-add-backpack-cart | dual | no | predicate | no | 8 | 1/7 | 0/0 | 0.0127 | 155 |  |
| ls-add-backpack-cart | guarded | no | predicate | no | 5 | 0/5 | 0/0 | 0.0089 | 146 |  |
| ls-bike-light-price | delegate | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0070 | 78 |  |
| ls-bike-light-price | dual | yes | predicate | yes | 7 | 3/4 | 0/0 | 0.0092 | 101 |  |
| ls-bike-light-price | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0070 | 80 |  |
| ls-cart-stop-unauthorized | delegate | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0081 | 74 |  |
| ls-cart-stop-unauthorized | dual | yes | predicate | yes | 12 | 7/5 | 0/0 | 0.0123 | 116 |  |
| ls-cart-stop-unauthorized | guarded | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0077 | 66 |  |
| ls-checkout-total | delegate | no | predicate | no | 6 | 0/6 | 0/0 | 0.0088 | 120 |  |
| ls-checkout-total | dual | no | predicate | no | 7 | 2/5 | 0/0 | 0.0103 | 84 |  |
| ls-checkout-total | guarded | no | predicate | no | 7 | 0/7 | 0/0 | 0.0107 | 134 |  |
| ls-login-inventory | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0037 | 39 |  |
| ls-login-inventory | dual | yes | predicate | yes | 5 | 4/1 | 0/0 | 0.0040 | 42 |  |
| ls-login-inventory | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0054 | 66 |  |
| ls-login-locked | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0051 | 57 |  |
| ls-login-locked | dual | yes | predicate | yes | 5 | 3/2 | 0/0 | 0.0048 | 64 |  |
| ls-login-locked | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0047 | 42 |  |
| ls-order-backpack-authorized | delegate | no | predicate | no | 25 | 0/25 | 0/0 | 0.0298 | 380 |  |
| ls-order-backpack-authorized | dual | no | predicate | no | 25 | 5/20 | 0/0 | 0.0301 | 272 |  |
| ls-order-backpack-authorized | guarded | yes | predicate | yes | 25 | 0/25 | 0/0 | 0.0344 | 362 |  |
| ls-order-jacket-authorized | delegate | yes | predicate | yes | 12 | 0/12 | 0/0 | 0.0152 | 173 |  |
| ls-order-jacket-authorized | dual | yes | predicate | yes | 12 | 5/7 | 0/0 | 0.0116 | 127 |  |
| ls-order-jacket-authorized | guarded | yes | predicate | yes | 9 | 0/9 | 0/0 | 0.0125 | 148 |  |
| ls-order-onesie-authorized | delegate | yes | predicate | yes | 8 | 0/8 | 0/0 | 0.0125 | 81 |  |
| ls-order-onesie-authorized | dual | yes | predicate | yes | 12 | 7/5 | 0/0 | 0.0112 | 77 |  |
| ls-order-onesie-authorized | guarded | yes | predicate | yes | 9 | 0/9 | 0/0 | 0.0143 | 131 |  |
| ls-sort-cheapest | delegate | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0086 | 75 |  |
| ls-sort-cheapest | dual | yes | predicate | yes | 11 | 6/5 | 0/0 | 0.0110 | 123 |  |
| ls-sort-cheapest | guarded | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0084 | 82 |  |
| lw-arxiv-attention-title | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0040 | 44 |  |
| lw-arxiv-attention-title | dual | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0069 | 47 |  |
| lw-arxiv-attention-title | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0037 | 46 |  |
| lw-arxiv-cs-ai-list | delegate | yes | predicate | yes | 3 | 0/2 | 0/0 | 0.0038 | 70 |  |
| lw-arxiv-cs-ai-list | dual | yes | predicate | yes | 4 | 2/1 | 0/0 | 0.0030 | 92 |  |
| lw-arxiv-cs-ai-list | guarded | yes | predicate | yes | 3 | 0/2 | 0/0 | 0.0040 | 89 |  |
| lw-berlin-wall | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0049 | 50 |  |
| lw-berlin-wall | dual | yes | predicate | yes | 3 | 2/1 | 0/0 | 0.0066 | 42 |  |
| lw-berlin-wall | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0043 | 66 |  |
| lw-canberra | delegate | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0100 | 110 |  |
| lw-canberra | dual | yes | predicate | yes | 5 | 0/3 | 0/0 | 0.0157 | 95 |  |
| lw-canberra | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0044 | 45 |  |
| lw-chain-austen-year | delegate | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0064 | 56 |  |
| lw-chain-austen-year | dual | yes | predicate | yes | 3 | 1/2 | 0/0 | 0.0079 | 52 |  |
| lw-chain-austen-year | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0060 | 49 |  |
| lw-chain-curie-nobel | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0062 | 43 |  |
| lw-chain-curie-nobel | dual | yes | predicate | yes | 4 | 2/2 | 0/0 | 0.0084 | 45 |  |
| lw-chain-curie-nobel | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0065 | 73 |  |
| lw-chain-dune-herbert | delegate | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0064 | 56 |  |
| lw-chain-dune-herbert | dual | yes | predicate | yes | 4 | 3/1 | 0/0 | 0.0067 | 44 |  |
| lw-chain-dune-herbert | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0081 | 62 |  |
| lw-chain-eiffel-gustave | delegate | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0080 | 57 |  |
| lw-chain-eiffel-gustave | dual | yes | predicate | yes | 4 | 3/1 | 0/0 | 0.0082 | 56 |  |
| lw-chain-eiffel-gustave | guarded | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0065 | 95 |  |
| lw-chain-python-guido | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0063 | 56 |  |
| lw-chain-python-guido | dual | yes | predicate | yes | 4 | 3/1 | 0/0 | 0.0094 | 32 |  |
| lw-chain-python-guido | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0064 | 55 |  |
| lw-chain-rust-hoare | delegate | no | predicate | yes | 6 | 0/6 | 0/0 | 0.0138 | 142 |  |
| lw-chain-rust-hoare | dual | yes | predicate | - | 8 | 3/5 | 0/0 | 0.0216 | 170 |  |
| lw-chain-rust-hoare | guarded | no | predicate | yes | 6 | 0/6 | 0/0 | 0.0141 | 148 |  |
| lw-chain-turing-machine | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0063 | 71 |  |
| lw-chain-turing-machine | dual | yes | predicate | yes | 4 | 3/1 | 0/0 | 0.0064 | 34 |  |
| lw-chain-turing-machine | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0064 | 67 |  |
| lw-ddg-mdn-fetch | delegate | yes | predicate | yes | 7 | 0/6 | 0/0 | 0.0107 | 157 |  |
| lw-ddg-mdn-fetch | dual | yes | predicate | yes | 5 | 1/3 | 0/0 | 0.0080 | 87 |  |
| lw-ddg-mdn-fetch | guarded | yes | predicate | yes | 6 | 0/5 | 0/0 | 0.0092 | 98 |  |
| lw-ddg-python-pathlib | delegate | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0070 | 56 |  |
| lw-ddg-python-pathlib | dual | yes | predicate | yes | 5 | 2/3 | 0/0 | 0.0075 | 52 |  |
| lw-ddg-python-pathlib | guarded | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0086 | 95 |  |
| lw-eiffel-completed | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0042 | 40 |  |
| lw-eiffel-completed | dual | yes | predicate | yes | 3 | 2/1 | 0/0 | 0.0067 | 45 |  |
| lw-eiffel-completed | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0042 | 42 |  |
| lw-github-browser-use-license | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0058 | 101 |  |
| lw-github-browser-use-license | dual | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0080 | 47 |  |
| lw-github-browser-use-license | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0043 | 48 |  |
| lw-github-pyo3-issues | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0043 | 56 |  |
| lw-github-pyo3-issues | dual | yes | predicate | yes | 4 | 1/3 | 0/0 | 0.0102 | 87 |  |
| lw-github-pyo3-issues | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0106 | 95 |  |
| lw-gutenberg-pride | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0037 | 40 |  |
| lw-gutenberg-pride | dual | yes | predicate | yes | 2 | 1/1 | 0/0 | 0.0035 | 36 |  |
| lw-gutenberg-pride | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0055 | 88 |  |
| lw-gutenberg-top | delegate | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0041 | 111 |  |
| lw-gutenberg-top | dual | yes | predicate | yes | 2 | 2/0 | 0/0 | 0.0020 | 15 |  |
| lw-gutenberg-top | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0037 | 45 |  |
| lw-linux-creator | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0049 | 64 |  |
| lw-linux-creator | dual | yes | predicate | yes | 4 | 2/2 | 0/0 | 0.0082 | 128 |  |
| lw-linux-creator | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0043 | 52 |  |
| lw-mdn-418 | delegate | no | predicate | no | 7 | 0/7 | 0/0 | 0.0085 | 140 |  |
| lw-mdn-418 | dual | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0125 | 75 |  |
| lw-mdn-418 | guarded | yes | predicate | yes | 7 | 0/7 | 0/0 | 0.0099 | 154 |  |
| lw-mdn-array-map | delegate | yes | predicate | yes | 4 | 0/3 | 0/0 | 0.0045 | 77 |  |
| lw-mdn-array-map | dual | yes | predicate | yes | 3 | 1/1 | 0/0 | 0.0039 | 41 |  |
| lw-mdn-array-map | guarded | yes | predicate | yes | 4 | 0/3 | 0/0 | 0.0044 | 95 |  |
| lw-mdn-font-weight | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0041 | 50 |  |
| lw-mdn-font-weight | dual | yes | predicate | yes | 4 | 1/3 | 0/0 | 0.0079 | 107 |  |
| lw-mdn-font-weight | guarded | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0092 | 98 |  |
| lw-pride-author | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0041 | 44 |  |
| lw-pride-author | dual | yes | predicate | yes | 3 | 2/1 | 0/0 | 0.0063 | 53 |  |
| lw-pride-author | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0041 | 43 |  |
| lw-pydocs-keyerror | delegate | yes | predicate | yes | 16 | 0/16 | 0/0 | 0.0249 | 320 |  |
| lw-pydocs-keyerror | dual | yes | predicate | yes | 9 | 0/9 | 0/0 | 0.0216 | 167 |  |
| lw-pydocs-keyerror | guarded | yes | predicate | yes | 9 | 0/9 | 0/0 | 0.0156 | 242 |  |
| lw-pydocs-lru-cache | delegate | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0055 | 57 |  |
| lw-pydocs-lru-cache | dual | yes | predicate | yes | 3 | 1/2 | 0/0 | 0.0081 | 41 |  |
| lw-pydocs-lru-cache | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0047 | 102 |  |
| lw-pydocs-pathlib | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0037 | 44 |  |
| lw-pydocs-pathlib | dual | yes | predicate | yes | 3 | 2/1 | 0/0 | 0.0074 | 63 |  |
| lw-pydocs-pathlib | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0044 | 65 |  |
| lw-pypi-browser-use | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0039 | 35 |  |
| lw-pypi-browser-use | dual | yes | predicate | yes | 4 | 3/1 | 0/0 | 0.0041 | 30 |  |
| lw-pypi-browser-use | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0041 | 49 |  |
| lw-pypi-requests-license | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0037 | 45 |  |
| lw-pypi-requests-license | dual | yes | predicate | yes | 4 | 2/2 | 0/0 | 0.0056 | 48 |  |
| lw-pypi-requests-license | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0036 | 39 |  |
| lw-python-creator | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0052 | 76 |  |
| lw-python-creator | dual | yes | predicate | yes | 3 | 2/1 | 0/0 | 0.0081 | 41 |  |
| lw-python-creator | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0045 | 43 |  |
| lw-rfc-8259-format | delegate | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0044 | 85 |  |
| lw-rfc-8259-format | dual | yes | predicate | yes | 4 | 2/2 | 0/0 | 0.0060 | 49 |  |
| lw-rfc-8259-format | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0038 | 42 |  |
| lw-rfc-9110 | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0039 | 40 |  |
| lw-rfc-9110 | dual | yes | predicate | yes | 4 | 1/1 | 0/0 | 0.0054 | 65 |  |
| lw-rfc-9110 | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0041 | 70 |  |
| lw-www-inventor | delegate | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0042 | 52 |  |
| lw-www-inventor | dual | yes | predicate | yes | 4 | 2/2 | 0/0 | 0.0101 | 68 |  |
| lw-www-inventor | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0042 | 37 |  |
