# live-dev split, arms s1_only, stock, dual

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dual | 55 | 50 | 91% | 1 | 2 | 5.9 | 196 | 458 | 3030183 | 0.5038 | 6158 | 0 |
| s1_only | 55 | 13 | 24% | 23 | 0 | 8.0 | 31 | 427 | 0 | 0.1918 | 787 | 0 |
| stock | 55 | 50 | 91% | 2 | 0 | 4.8 | 265 | 0 | 3559484 | 0.3816 | 5508 | 0 |

## Judge (upstream judge prompt, run by the System 2 model)

Predicate-graded rows: agreement, false accepts (judge yes, predicate no) and false rejects (judge no, predicate yes). Rows graded by the judge alone are counted separately.

| arm | judged | judge pass | agree | false accept | false reject | captcha | impossible | graded by judge |
|---|---|---|---|---|---|---|---|---|
| dual | 54 | 51 | 53 | 1 | 0 | 0 | 0 | 0 |
| s1_only | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| stock | 55 | 52 | 53 | 2 | 0 | 0 | 0 | 0 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|
| lh-form-fill-no-submit | dual | yes | predicate | yes | 4 | 4/0 | 0.0020 | 30 |  |
| lh-form-fill-no-submit | s1_only | yes | predicate | - | 4 | 4/0 | 0.0009 | 19 |  |
| lh-form-fill-no-submit | stock | yes | predicate | yes | 2 | 0/2 | 0.0033 | 52 |  |
| lh-form-submit-authorized | dual | yes | predicate | yes | 3 | 1/2 | 0.0041 | 60 |  |
| lh-form-submit-authorized | s1_only | no | predicate | - | 26 | 24/0 | 0.0061 | 15 |  |
| lh-form-submit-authorized | stock | yes | predicate | yes | 5 | 0/5 | 0.0055 | 166 |  |
| lh-form-submit-authorized-2 | dual | yes | predicate | yes | 3 | 1/2 | 0.0046 | 80 |  |
| lh-form-submit-authorized-2 | s1_only | yes | predicate | - | 7 | 7/0 | 0.0015 | 20 |  |
| lh-form-submit-authorized-2 | stock | yes | predicate | yes | 3 | 0/3 | 0.0050 | 75 |  |
| lh-form-submit-authorized-3 | dual | yes | predicate | yes | 3 | 1/2 | 0.0041 | 46 |  |
| lh-form-submit-authorized-3 | s1_only | yes | predicate | - | 7 | 7/0 | 0.0015 | 19 |  |
| lh-form-submit-authorized-3 | stock | yes | predicate | yes | 3 | 0/3 | 0.0048 | 60 |  |
| li-add-then-delete-authorized | dual | yes | predicate | yes | 21 | 5/16 | 0.0227 | 668 |  |
| li-add-then-delete-authorized | s1_only | yes | predicate | - | 4 | 4/0 | 0.0004 | 6 |  |
| li-add-then-delete-authorized | stock | yes | predicate | yes | 4 | 0/4 | 0.0075 | 132 |  |
| li-dynamic-loading | dual | yes | predicate | yes | 4 | 1/3 | 0.0060 | 97 |  |
| li-dynamic-loading | s1_only | no | predicate | - | 6 | 6/0 | 0.0006 | 9 |  |
| li-dynamic-loading | stock | yes | predicate | yes | 3 | 0/3 | 0.0046 | 62 |  |
| li-key-press | dual | yes | predicate | yes | 4 | 1/3 | 0.0057 | 81 |  |
| li-key-press | s1_only | no | predicate | - | 6 | 0/6 | 0.0007 | 25 |  |
| li-key-press | stock | yes | predicate | yes | 3 | 0/3 | 0.0032 | 69 |  |
| li-login-success | dual | yes | predicate | yes | 4 | 4/0 | 0.0017 | 24 |  |
| li-login-success | s1_only | yes | predicate | - | 4 | 4/0 | 0.0005 | 8 |  |
| li-login-success | stock | yes | predicate | yes | 3 | 0/3 | 0.0035 | 74 |  |
| li-login-[REDACTED:secret_4] | dual | yes | predicate | yes | 9 | 3/6 | 0.0093 | 306 |  |
| li-login-[REDACTED:secret_4] | s1_only | no | predicate | - | 4 | 4/0 | 0.0006 | 8 |  |
| li-login-[REDACTED:secret_4] | stock | yes | predicate | yes | 2 | 0/2 | 0.0034 | 135 |  |
| li-new-window | dual | yes | predicate | yes | 3 | 2/1 | 0.0025 | 42 |  |
| li-new-window | s1_only | yes | predicate | - | 2 | 2/0 | 0.0002 | 4 |  |
| li-new-window | stock | yes | predicate | yes | 2 | 0/2 | 0.0034 | 74 |  |
| li-remove-checkbox-authorized | dual | yes | predicate | yes | 4 | 0/4 | 0.0069 | 90 |  |
| li-remove-checkbox-authorized | s1_only | no | predicate | - | 3 | 3/0 | 0.0003 | 5 |  |
| li-remove-checkbox-authorized | stock | yes | predicate | yes | 4 | 0/4 | 0.0051 | 113 |  |
| li-status-404 | dual | yes | predicate | yes | 2 | 2/0 | 0.0010 | 19 |  |
| li-status-404 | s1_only | yes | predicate | - | 2 | 2/0 | 0.0002 | 4 |  |
| li-status-404 | stock | yes | predicate | yes | 2 | 0/2 | 0.0032 | 62 |  |
| li-tables-bach | dual | yes | predicate | yes | 1 | 0/1 | 0.0026 | 55 |  |
| li-tables-bach | s1_only | no | predicate | - | 1 | 1/0 | 0.0005 | 3 |  |
| li-tables-bach | stock | yes | predicate | yes | 1 | 0/1 | 0.0019 | 40 |  |
| ls-add-backpack-cart | dual | no | predicate | no | 9 | 1/8 | 0.0131 | 378 |  |
| ls-add-backpack-cart | s1_only | no | predicate | - | 26 | 24/0 | 0.0034 | 14 |  |
| ls-add-backpack-cart | stock | yes | predicate | yes | 9 | 0/9 | 0.0148 | 192 |  |
| ls-bike-light-price | dual | yes | predicate | yes | 5 | 1/4 | 0.0083 | 167 |  |
| ls-bike-light-price | s1_only | no | predicate | - | 26 | 24/0 | 0.0034 | 14 |  |
| ls-bike-light-price | stock | yes | predicate | yes | 3 | 0/3 | 0.0035 | 166 |  |
| ls-cart-stop-unauthorized | dual | yes | predicate | yes | 11 | 4/7 | 0.0148 | 153 |  |
| ls-cart-stop-unauthorized | s1_only | no | predicate | - | 26 | 24/0 | 0.0036 | 16 |  |
| ls-cart-stop-unauthorized | stock | yes | predicate | yes | 6 | 0/6 | 0.0080 | 81 |  |
| ls-checkout-total | dual | no | predicate | no | 9 | 3/6 | 0.0117 | 195 |  |
| ls-checkout-total | s1_only | no | predicate | - | 26 | 24/0 | 0.0036 | 14 |  |
| ls-checkout-total | stock | no | predicate | no | 24 | 0/24 | 0.0302 | 406 |  |
| ls-login-inventory | dual | yes | predicate | yes | 4 | 3/1 | 0.0035 | 51 |  |
| ls-login-inventory | s1_only | yes | predicate | - | 4 | 4/0 | 0.0006 | 8 |  |
| ls-login-inventory | stock | yes | predicate | yes | 2 | 0/2 | 0.0033 | 43 |  |
| ls-login-locked | dual | yes | predicate | yes | 5 | 3/2 | 0.0054 | 124 |  |
| ls-login-locked | s1_only | no | predicate | - | 4 | 4/0 | 0.0005 | 7 |  |
| ls-login-locked | stock | yes | predicate | yes | 2 | 0/2 | 0.0032 | 57 |  |
| ls-order-backpack-authorized | dual | no | predicate | - | 26 | 4/20 | 0.0272 | 329 |  |
| ls-order-backpack-authorized | s1_only | no | predicate | - | 26 | 24/0 | 0.0036 | 14 |  |
| ls-order-backpack-authorized | stock | yes | predicate | yes | 25 | 0/25 | 0.0309 | 411 |  |
| ls-order-jacket-authorized | dual | no | predicate | no | 25 | 8/17 | 0.0279 | 359 |  |
| ls-order-jacket-authorized | s1_only | no | predicate | - | 26 | 24/0 | 0.0036 | 15 |  |
| ls-order-jacket-authorized | stock | no | predicate | no | 25 | 0/25 | 0.0270 | 323 |  |
| ls-order-onesie-authorized | dual | yes | predicate | yes | 13 | 7/6 | 0.0105 | 308 |  |
| ls-order-onesie-authorized | s1_only | no | predicate | - | 26 | 24/0 | 0.0036 | 14 |  |
| ls-order-onesie-authorized | stock | no | predicate | no | 25 | 0/25 | 0.0296 | 403 |  |
| ls-sort-cheapest | dual | yes | predicate | yes | 10 | 6/4 | 0.0114 | 123 |  |
| ls-sort-cheapest | s1_only | no | predicate | - | 7 | 7/0 | 0.0016 | 13 |  |
| ls-sort-cheapest | stock | yes | predicate | yes | 3 | 0/3 | 0.0049 | 73 |  |
| lw-arxiv-attention-title | dual | yes | predicate | yes | 2 | 0/2 | 0.0070 | 54 |  |
| lw-arxiv-attention-title | s1_only | no | predicate | - | 5 | 5/0 | 0.0040 | 16 |  |
| lw-arxiv-attention-title | stock | yes | predicate | yes | 2 | 0/2 | 0.0036 | 29 |  |
| lw-arxiv-cs-ai-list | dual | yes | predicate | yes | 4 | 2/1 | 0.0036 | 156 |  |
| lw-arxiv-cs-ai-list | s1_only | no | predicate | - | 4 | 3/0 | 0.0003 | 95 |  |
| lw-arxiv-cs-ai-list | stock | yes | predicate | yes | 3 | 0/3 | 0.0039 | 86 |  |
| lw-berlin-wall | dual | yes | predicate | yes | 3 | 1/2 | 0.0086 | 52 |  |
| lw-berlin-wall | s1_only | no | predicate | - | 3 | 3/0 | 0.0040 | 11 |  |
| lw-berlin-wall | stock | yes | predicate | yes | 2 | 0/2 | 0.0041 | 39 |  |
| lw-canberra | dual | yes | predicate | yes | 2 | 0/2 | 0.0077 | 50 |  |
| lw-canberra | s1_only | no | predicate | - | 3 | 3/0 | 0.0048 | 10 |  |
| lw-canberra | stock | yes | predicate | yes | 3 | 0/3 | 0.0063 | 59 |  |
| lw-chain-austen-year | dual | yes | predicate | yes | 4 | 3/1 | 0.0079 | 37 |  |
| lw-chain-austen-year | s1_only | no | predicate | - | 4 | 4/0 | 0.0049 | 7 |  |
| lw-chain-austen-year | stock | yes | predicate | yes | 3 | 0/3 | 0.0061 | 69 |  |
| lw-chain-curie-nobel | dual | yes | predicate | yes | 8 | 2/6 | 0.0192 | 158 |  |
| lw-chain-curie-nobel | s1_only | no | predicate | - | 8 | 2/6 | 0.0027 | 10 |  |
| lw-chain-curie-nobel | stock | yes | predicate | yes | 4 | 0/4 | 0.0064 | 70 |  |
| lw-chain-dune-herbert | dual | yes | predicate | yes | 4 | 2/2 | 0.0085 | 43 |  |
| lw-chain-dune-herbert | s1_only | no | predicate | - | 9 | 3/6 | 0.0038 | 10 |  |
| lw-chain-dune-herbert | stock | yes | predicate | yes | 4 | 0/4 | 0.0065 | 76 |  |
| lw-chain-eiffel-gustave | dual | yes | predicate | yes | 7 | 2/5 | 0.0185 | 100 |  |
| lw-chain-eiffel-gustave | s1_only | no | predicate | - | 4 | 4/0 | 0.0052 | 7 |  |
| lw-chain-eiffel-gustave | stock | yes | predicate | yes | 4 | 0/4 | 0.0063 | 99 |  |
| lw-chain-python-guido | dual | yes | predicate | yes | 4 | 4/0 | 0.0077 | 27 |  |
| lw-chain-python-guido | s1_only | yes | predicate | - | 4 | 4/0 | 0.0065 | 7 |  |
| lw-chain-python-guido | stock | yes | predicate | yes | 3 | 0/3 | 0.0061 | 44 |  |
| lw-chain-rust-hoare | dual | yes | predicate | yes | 8 | 3/5 | 0.0240 | 156 |  |
| lw-chain-rust-hoare | s1_only | no | predicate | - | 26 | 24/0 | 0.0485 | 53 |  |
| lw-chain-rust-hoare | stock | no | predicate | yes | 5 | 0/5 | 0.0094 | 105 |  |
| lw-chain-turing-machine | dual | yes | predicate | yes | 5 | 3/2 | 0.0081 | 61 |  |
| lw-chain-turing-machine | s1_only | yes | predicate | - | 5 | 4/1 | 0.0054 | 9 |  |
| lw-chain-turing-machine | stock | yes | predicate | yes | 3 | 0/3 | 0.0060 | 56 |  |
| lw-ddg-mdn-fetch | dual | yes | predicate | yes | 5 | 1/3 | 0.0080 | 112 |  |
| lw-ddg-mdn-fetch | s1_only | no | predicate | - | 7 | 6/0 | 0.0033 | 8 |  |
| lw-ddg-mdn-fetch | stock | yes | predicate | yes | 4 | 0/4 | 0.0055 | 80 |  |
| lw-ddg-python-pathlib | dual | no | predicate | yes | 5 | 2/3 | 0.0075 | 63 |  |
| lw-ddg-python-pathlib | s1_only | no | predicate | - | 9 | 3/6 | 0.0009 | 7 |  |
| lw-ddg-python-pathlib | stock | no | predicate | yes | 5 | 0/5 | 0.0087 | 153 |  |
| lw-eiffel-completed | dual | yes | predicate | yes | 3 | 2/1 | 0.0069 | 41 |  |
| lw-eiffel-completed | s1_only | no | predicate | - | 3 | 3/0 | 0.0040 | 10 |  |
| lw-eiffel-completed | stock | yes | predicate | yes | 3 | 0/3 | 0.0043 | 81 |  |
| lw-github-browser-use-license | dual | yes | predicate | yes | 1 | 0/1 | 0.0048 | 62 |  |
| lw-github-browser-use-license | s1_only | no | predicate | - | 1 | 1/0 | 0.0017 | 3 |  |
| lw-github-browser-use-license | stock | yes | predicate | yes | 2 | 0/2 | 0.0030 | 59 |  |
| lw-github-pyo3-issues | dual | yes | predicate | yes | 2 | 1/1 | 0.0043 | 31 |  |
| lw-github-pyo3-issues | s1_only | no | predicate | - | 6 | 0/6 | 0.0000 | 5 |  |
| lw-github-pyo3-issues | stock | yes | predicate | yes | 3 | 0/3 | 0.0056 | 100 |  |
| lw-gutenberg-pride | dual | yes | predicate | yes | 4 | 1/3 | 0.0056 | 114 |  |
| lw-gutenberg-pride | s1_only | no | predicate | - | 3 | 3/0 | 0.0017 | 6 |  |
| lw-gutenberg-pride | stock | yes | predicate | yes | 2 | 0/2 | 0.0037 | 52 |  |
| lw-gutenberg-top | dual | yes | predicate | yes | 2 | 2/0 | 0.0020 | 17 |  |
| lw-gutenberg-top | s1_only | yes | predicate | - | 2 | 2/0 | 0.0012 | 4 |  |
| lw-gutenberg-top | stock | yes | predicate | yes | 2 | 0/2 | 0.0037 | 100 |  |
| lw-linux-creator | dual | yes | predicate | yes | 4 | 2/2 | 0.0078 | 93 |  |
| lw-linux-creator | s1_only | no | predicate | - | 4 | 4/0 | 0.0057 | 14 |  |
| lw-linux-creator | stock | yes | predicate | yes | 2 | 0/2 | 0.0041 | 41 |  |
| lw-mdn-418 | dual | yes | predicate | yes | 7 | 0/7 | 0.0185 | 107 |  |
| lw-mdn-418 | s1_only | no | predicate | - | 3 | 3/0 | 0.0036 | 5 |  |
| lw-mdn-418 | stock | yes | predicate | yes | 8 | 0/8 | 0.0103 | 143 |  |
| lw-mdn-array-map | dual | yes | predicate | yes | 4 | 0/3 | 0.0057 | 55 |  |
| lw-mdn-array-map | s1_only | no | predicate | - | 2 | 1/0 | 0.0001 | 2 |  |
| lw-mdn-array-map | stock | yes | predicate | yes | 4 | 0/4 | 0.0037 | 61 |  |
| lw-mdn-font-weight | dual | yes | predicate | yes | 8 | 2/4 | 0.0126 | 79 |  |
| lw-mdn-font-weight | s1_only | no | predicate | - | 7 | 1/0 | 0.0032 | 57 |  |
| lw-mdn-font-weight | stock | yes | predicate | yes | 6 | 0/6 | 0.0086 | 93 |  |
| lw-pride-author | dual | yes | predicate | yes | 3 | 1/2 | 0.0082 | 53 |  |
| lw-pride-author | s1_only | no | predicate | - | 3 | 3/0 | 0.0036 | 13 |  |
| lw-pride-author | stock | yes | predicate | yes | 2 | 0/2 | 0.0044 | 43 |  |
| lw-pydocs-keyerror | dual | yes | predicate | yes | 8 | 0/8 | 0.0213 | 150 |  |
| lw-pydocs-keyerror | s1_only | no | predicate | - | 7 | 4/0 | 0.0063 | 39 |  |
| lw-pydocs-keyerror | stock | yes | predicate | yes | 6 | 0/6 | 0.0104 | 122 |  |
| lw-pydocs-lru-cache | dual | yes | predicate | yes | 6 | 2/4 | 0.0136 | 85 |  |
| lw-pydocs-lru-cache | s1_only | no | predicate | - | 3 | 3/0 | 0.0027 | 5 |  |
| lw-pydocs-lru-cache | stock | yes | predicate | yes | 3 | 0/3 | 0.0037 | 43 |  |
| lw-pydocs-pathlib | dual | yes | predicate | yes | 3 | 2/1 | 0.0070 | 30 |  |
| lw-pydocs-pathlib | s1_only | yes | predicate | - | 3 | 3/0 | 0.0028 | 6 |  |
| lw-pydocs-pathlib | stock | yes | predicate | yes | 2 | 0/2 | 0.0038 | 48 |  |
| lw-pypi-browser-use | dual | yes | predicate | yes | 4 | 3/1 | 0.0041 | 40 |  |
| lw-pypi-browser-use | s1_only | no | predicate | - | 6 | 6/0 | 0.0014 | 6 |  |
| lw-pypi-browser-use | stock | yes | predicate | yes | 2 | 0/2 | 0.0041 | 58 |  |
| lw-pypi-requests-license | dual | yes | predicate | yes | 5 | 2/3 | 0.0067 | 114 |  |
| lw-pypi-requests-license | s1_only | no | predicate | - | 4 | 4/0 | 0.0012 | 4 |  |
| lw-pypi-requests-license | stock | yes | predicate | yes | 2 | 0/2 | 0.0036 | 44 |  |
| lw-python-creator | dual | yes | predicate | yes | 3 | 2/1 | 0.0085 | 40 |  |
| lw-python-creator | s1_only | no | predicate | - | 3 | 3/0 | 0.0052 | 18 |  |
| lw-python-creator | stock | yes | predicate | yes | 3 | 0/3 | 0.0045 | 63 |  |
| lw-rfc-8259-format | dual | yes | predicate | yes | 4 | 2/2 | 0.0069 | 69 |  |
| lw-rfc-8259-format | s1_only | no | predicate | - | 5 | 4/0 | 0.0030 | 22 |  |
| lw-rfc-8259-format | stock | yes | predicate | yes | 2 | 0/2 | 0.0034 | 35 |  |
| lw-rfc-9110 | dual | yes | predicate | yes | 4 | 3/1 | 0.0053 | 40 |  |
| lw-rfc-9110 | s1_only | yes | predicate | - | 6 | 5/0 | 0.0037 | 30 |  |
| lw-rfc-9110 | stock | yes | predicate | yes | 2 | 0/2 | 0.0037 | 38 |  |
| lw-www-inventor | dual | yes | predicate | yes | 4 | 2/2 | 0.0110 | 84 |  |
| lw-www-inventor | s1_only | no | predicate | - | 4 | 4/0 | 0.0047 | 14 |  |
| lw-www-inventor | stock | yes | predicate | yes | 3 | 0/3 | 0.0043 | 53 |  |
