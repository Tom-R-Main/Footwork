# live-dev split, arms guarded, dual, delegate, delegate_evidence (Q9)

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| delegate | 55 | 52 | 95% | 0 | 2 | 6.6 | 278 | 290 | 4334166 | 0.5774 | 5242 | 0 |
| delegate_evidence | 55 | 49 | 89% | 0 | 3 | 7.2 | 300 | 321 | 4417589 | 0.6039 | 5997 | 0 |
| dual | 55 | 51 | 93% | 0 | 2 | 5.8 | 193 | 391 | 3060113 | 0.4920 | 4702 | 0 |
| guarded | 55 | 50 | 91% | 0 | 2 | 4.8 | 260 | 80 | 3739460 | 0.4117 | 4877 | 0 |

## Outcomes (external success and claimed completion kept apart)

| arm | verified pass (passed and claimed) | unclaimed pass (passed, UNVERIFIED or paused) | false done | model requests (tracker) | cost per verified pass |
|---|---|---|---|---|---|
| delegate | 42 | 10 | 0 | 0 | 0.0137 |
| delegate_evidence | 43 | 6 | 0 | 0 | 0.0140 |
| dual | 42 | 9 | 0 | 0 | 0.0117 |
| guarded | 41 | 9 | 0 | 0 | 0.0100 |

## Judge (upstream judge prompt, run by the System 2 model)

Predicate-graded rows: agreement, false accepts (judge yes, predicate no) and false rejects (judge no, predicate yes). Rows graded by the judge alone are counted separately.

| arm | judged | judge pass | agree | false accept | false reject | captcha | impossible | graded by judge |
|---|---|---|---|---|---|---|---|---|
| delegate | 54 | 51 | 54 | 0 | 0 | 0 | 0 | 0 |
| delegate_evidence | 55 | 50 | 54 | 1 | 0 | 0 | 0 | 0 |
| dual | 55 | 50 | 54 | 0 | 1 | 0 | 0 | 0 |
| guarded | 55 | 51 | 54 | 1 | 0 | 0 | 0 | 0 |

## Delegation (Q9)

| arm | delegations | subgoals reached | reached per delegation | S1 steps | S2 steps |
|---|---|---|---|---|---|
| delegate | 51 | 19 | 0.37 | 77 | 278 |
| delegate_evidence | 52 | 22 | 0.42 | 87 | 300 |
| dual | 0 | 0 | 0.00 | 116 | 193 |
| guarded | 0 | 0 | 0.00 | 0 | 260 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | deleg. | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|---|
| lh-form-fill-no-submit | delegate | yes | predicate | yes | 8 | 3/5 | 0/1 | 0.0118 | 115 |  |
| lh-form-fill-no-submit | delegate_evidence | yes | predicate | yes | 12 | 3/9 | 1/1 | 0.0098 | 238 |  |
| lh-form-fill-no-submit | dual | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0093 | 171 |  |
| lh-form-fill-no-submit | guarded | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0073 | 128 |  |
| lh-form-submit-authorized | delegate | yes | predicate | yes | 7 | 0/7 | 0/1 | 0.0113 | 150 |  |
| lh-form-submit-authorized | delegate_evidence | yes | predicate | yes | 5 | 0/5 | 0/1 | 0.0090 | 102 |  |
| lh-form-submit-authorized | dual | yes | predicate | yes | 3 | 1/2 | 0/0 | 0.0040 | 35 |  |
| lh-form-submit-authorized | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0050 | 51 |  |
| lh-form-submit-authorized-2 | delegate | yes | predicate | yes | 5 | 0/5 | 0/1 | 0.0072 | 118 |  |
| lh-form-submit-authorized-2 | delegate_evidence | yes | predicate | yes | 4 | 0/4 | 0/1 | 0.0070 | 74 |  |
| lh-form-submit-authorized-2 | dual | yes | predicate | yes | 3 | 1/2 | 0/0 | 0.0042 | 44 |  |
| lh-form-submit-authorized-2 | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0049 | 60 |  |
| lh-form-submit-authorized-3 | delegate | yes | predicate | yes | 4 | 0/4 | 0/1 | 0.0070 | 67 |  |
| lh-form-submit-authorized-3 | delegate_evidence | yes | predicate | yes | 6 | 0/6 | 0/2 | 0.0097 | 125 |  |
| lh-form-submit-authorized-3 | dual | yes | predicate | yes | 3 | 1/2 | 0/0 | 0.0041 | 41 |  |
| lh-form-submit-authorized-3 | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0052 | 64 |  |
| li-add-then-delete-authorized | delegate | yes | predicate | yes | 7 | 0/7 | 0/1 | 0.0124 | 128 |  |
| li-add-then-delete-authorized | delegate_evidence | yes | predicate | yes | 5 | 2/3 | 0/1 | 0.0060 | 74 |  |
| li-add-then-delete-authorized | dual | yes | predicate | no | 21 | 4/17 | 0/0 | 0.0199 | 469 |  |
| li-add-then-delete-authorized | guarded | yes | predicate | yes | 9 | 0/9 | 0/0 | 0.0151 | 246 |  |
| li-dynamic-loading | delegate | yes | predicate | yes | 5 | 1/4 | 1/1 | 0.0069 | 54 |  |
| li-dynamic-loading | delegate_evidence | yes | predicate | yes | 7 | 1/6 | 1/1 | 0.0103 | 148 |  |
| li-dynamic-loading | dual | yes | predicate | yes | 4 | 1/3 | 0/0 | 0.0059 | 65 |  |
| li-dynamic-loading | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0067 | 66 |  |
| li-key-press | delegate | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0064 | 56 |  |
| li-key-press | delegate_evidence | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0067 | 61 |  |
| li-key-press | dual | yes | predicate | yes | 5 | 1/3 | 0/0 | 0.0065 | 90 |  |
| li-key-press | guarded | yes | predicate | yes | 7 | 0/7 | 0/0 | 0.0083 | 136 |  |
| li-login-[REDACTED:secret_4] | delegate | yes | predicate | yes | 9 | 3/6 | 1/1 | 0.0118 | 108 |  |
| li-login-[REDACTED:secret_4] | delegate_evidence | yes | predicate | yes | 8 | 0/8 | 0/1 | 0.0130 | 188 |  |
| li-login-[REDACTED:secret_4] | dual | yes | predicate | yes | 12 | 6/6 | 0/0 | 0.0123 | 96 |  |
| li-login-[REDACTED:secret_4] | guarded | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0077 | 130 |  |
| li-login-success | delegate | yes | predicate | yes | 5 | 2/3 | 1/1 | 0.0061 | 57 |  |
| li-login-success | delegate_evidence | yes | predicate | yes | 5 | 3/2 | 1/1 | 0.0049 | 45 |  |
| li-login-success | dual | yes | predicate | yes | 4 | 4/0 | 0/0 | 0.0017 | 21 |  |
| li-login-success | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0034 | 39 |  |
| li-new-window | delegate | yes | predicate | yes | 5 | 1/4 | 1/1 | 0.0073 | 83 |  |
| li-new-window | delegate_evidence | yes | predicate | yes | 4 | 1/3 | 1/1 | 0.0058 | 60 |  |
| li-new-window | dual | yes | predicate | yes | 3 | 2/1 | 0/0 | 0.0027 | 41 |  |
| li-new-window | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0049 | 58 |  |
| li-remove-checkbox-authorized | delegate | yes | predicate | yes | 6 | 0/6 | 0/1 | 0.0088 | 120 |  |
| li-remove-checkbox-authorized | delegate_evidence | yes | predicate | yes | 5 | 0/5 | 0/1 | 0.0082 | 89 |  |
| li-remove-checkbox-authorized | dual | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0066 | 63 |  |
| li-remove-checkbox-authorized | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0063 | 65 |  |
| li-status-404 | delegate | yes | predicate | yes | 3 | 1/2 | 1/1 | 0.0040 | 44 |  |
| li-status-404 | delegate_evidence | yes | predicate | yes | 3 | 1/2 | 1/1 | 0.0044 | 53 |  |
| li-status-404 | dual | yes | predicate | yes | 2 | 2/0 | 0/0 | 0.0009 | 15 |  |
| li-status-404 | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0033 | 44 |  |
| li-tables-bach | delegate | yes | predicate | yes | 1 | 0/1 | 0/0 | 0.0020 | 25 |  |
| li-tables-bach | delegate_evidence | yes | predicate | yes | 6 | 0/6 | 0/0 | 0.0056 | 190 |  |
| li-tables-bach | dual | yes | predicate | yes | 1 | 0/1 | 0/0 | 0.0026 | 36 |  |
| li-tables-bach | guarded | yes | predicate | yes | 1 | 0/1 | 0/0 | 0.0019 | 31 |  |
| ls-add-backpack-cart | delegate | no | predicate | no | 10 | 4/6 | 0/2 | 0.0120 | 85 |  |
| ls-add-backpack-cart | delegate_evidence | no | predicate | no | 9 | 3/6 | 0/1 | 0.0113 | 101 |  |
| ls-add-backpack-cart | dual | no | predicate | no | 7 | 2/5 | 0/0 | 0.0108 | 136 |  |
| ls-add-backpack-cart | guarded | no | predicate | no | 8 | 0/8 | 0/0 | 0.0106 | 175 |  |
| ls-bike-light-price | delegate | yes | predicate | yes | 8 | 3/5 | 0/1 | 0.0100 | 89 |  |
| ls-bike-light-price | delegate_evidence | yes | predicate | yes | 6 | 1/5 | 1/1 | 0.0101 | 86 |  |
| ls-bike-light-price | dual | yes | predicate | yes | 7 | 3/4 | 0/0 | 0.0089 | 64 |  |
| ls-bike-light-price | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0073 | 74 |  |
| ls-cart-stop-unauthorized | delegate | yes | predicate | yes | 11 | 6/5 | 0/2 | 0.0114 | 90 |  |
| ls-cart-stop-unauthorized | delegate_evidence | yes | predicate | yes | 11 | 6/5 | 0/2 | 0.0113 | 75 |  |
| ls-cart-stop-unauthorized | dual | yes | predicate | yes | 13 | 7/6 | 0/0 | 0.0139 | 98 |  |
| ls-cart-stop-unauthorized | guarded | yes | predicate | yes | 7 | 0/7 | 0/0 | 0.0103 | 118 |  |
| ls-checkout-total | delegate | no | predicate | no | 9 | 2/7 | 0/2 | 0.0121 | 93 |  |
| ls-checkout-total | delegate_evidence | no | predicate | no | 11 | 3/8 | 0/1 | 0.0128 | 109 |  |
| ls-checkout-total | dual | no | predicate | no | 8 | 2/6 | 0/0 | 0.0105 | 85 |  |
| ls-checkout-total | guarded | no | predicate | no | 6 | 0/6 | 0/0 | 0.0083 | 83 |  |
| ls-login-inventory | delegate | yes | predicate | yes | 4 | 0/4 | 0/1 | 0.0074 | 101 |  |
| ls-login-inventory | delegate_evidence | yes | predicate | yes | 6 | 3/3 | 1/1 | 0.0068 | 59 |  |
| ls-login-inventory | dual | yes | predicate | yes | 4 | 3/1 | 0/0 | 0.0036 | 48 |  |
| ls-login-inventory | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0036 | 50 |  |
| ls-login-locked | delegate | yes | predicate | yes | 7 | 3/4 | 1/1 | 0.0066 | 100 |  |
| ls-login-locked | delegate_evidence | yes | predicate | yes | 6 | 3/3 | 1/1 | 0.0072 | 86 |  |
| ls-login-locked | dual | yes | predicate | yes | 5 | 3/2 | 0/0 | 0.0054 | 60 |  |
| ls-login-locked | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0047 | 39 |  |
| ls-order-backpack-authorized | delegate | yes | predicate | - | 26 | 2/23 | 0/2 | 0.0329 | 272 |  |
| ls-order-backpack-authorized | delegate_evidence | no | predicate | no | 25 | 2/23 | 0/2 | 0.0305 | 296 |  |
| ls-order-backpack-authorized | dual | no | predicate | no | 25 | 4/21 | 0/0 | 0.0290 | 335 |  |
| ls-order-backpack-authorized | guarded | no | predicate | no | 25 | 0/25 | 0/0 | 0.0271 | 261 |  |
| ls-order-jacket-authorized | delegate | no | predicate | no | 25 | 2/23 | 0/1 | 0.0271 | 261 |  |
| ls-order-jacket-authorized | delegate_evidence | no | predicate | no | 25 | 2/23 | 0/2 | 0.0304 | 341 |  |
| ls-order-jacket-authorized | dual | no | predicate | no | 25 | 3/22 | 0/0 | 0.0356 | 407 |  |
| ls-order-jacket-authorized | guarded | no | predicate | no | 25 | 0/25 | 0/0 | 0.0292 | 372 |  |
| ls-order-onesie-authorized | delegate | yes | predicate | yes | 15 | 3/12 | 0/1 | 0.0187 | 141 |  |
| ls-order-onesie-authorized | delegate_evidence | yes | predicate | yes | 15 | 7/8 | 0/2 | 0.0162 | 120 |  |
| ls-order-onesie-authorized | dual | yes | predicate | yes | 13 | 9/4 | 0/0 | 0.0101 | 72 |  |
| ls-order-onesie-authorized | guarded | yes | predicate | yes | 8 | 0/8 | 0/0 | 0.0125 | 114 |  |
| ls-sort-cheapest | delegate | yes | predicate | yes | 8 | 2/6 | 1/1 | 0.0116 | 100 |  |
| ls-sort-cheapest | delegate_evidence | yes | predicate | yes | 12 | 5/7 | 0/1 | 0.0135 | 157 |  |
| ls-sort-cheapest | dual | yes | predicate | yes | 10 | 6/4 | 0/0 | 0.0112 | 117 |  |
| ls-sort-cheapest | guarded | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0086 | 85 |  |
| lw-arxiv-attention-title | delegate | yes | predicate | yes | 6 | 0/6 | 0/1 | 0.0141 | 108 |  |
| lw-arxiv-attention-title | delegate_evidence | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0039 | 33 |  |
| lw-arxiv-attention-title | dual | yes | predicate | yes | 5 | 3/2 | 0/0 | 0.0083 | 55 |  |
| lw-arxiv-attention-title | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0047 | 49 |  |
| lw-arxiv-cs-ai-list | delegate | yes | predicate | yes | 5 | 0/4 | 0/0 | 0.0046 | 122 |  |
| lw-arxiv-cs-ai-list | delegate_evidence | yes | predicate | yes | 4 | 0/3 | 0/1 | 0.0057 | 107 |  |
| lw-arxiv-cs-ai-list | dual | yes | predicate | yes | 4 | 2/1 | 0/0 | 0.0030 | 95 |  |
| lw-arxiv-cs-ai-list | guarded | yes | predicate | yes | 3 | 0/2 | 0/0 | 0.0039 | 81 |  |
| lw-berlin-wall | delegate | yes | predicate | yes | 5 | 2/3 | 1/1 | 0.0090 | 112 |  |
| lw-berlin-wall | delegate_evidence | yes | predicate | yes | 5 | 2/3 | 1/1 | 0.0115 | 113 |  |
| lw-berlin-wall | dual | yes | predicate | yes | 4 | 1/3 | 0/0 | 0.0119 | 80 |  |
| lw-berlin-wall | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0083 | 77 |  |
| lw-canberra | delegate | yes | predicate | yes | 5 | 2/3 | 1/1 | 0.0126 | 95 |  |
| lw-canberra | delegate_evidence | yes | predicate | yes | 5 | 2/3 | 1/1 | 0.0128 | 91 |  |
| lw-canberra | dual | yes | predicate | yes | 4 | 0/2 | 0/0 | 0.0110 | 90 |  |
| lw-canberra | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0044 | 41 |  |
| lw-chain-austen-year | delegate | yes | predicate | yes | 5 | 2/3 | 0/1 | 0.0112 | 53 |  |
| lw-chain-austen-year | delegate_evidence | yes | predicate | yes | 11 | 3/8 | 0/1 | 0.0191 | 188 |  |
| lw-chain-austen-year | dual | yes | predicate | yes | 3 | 1/2 | 0/0 | 0.0085 | 51 |  |
| lw-chain-austen-year | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0060 | 47 |  |
| lw-chain-curie-nobel | delegate | yes | predicate | yes | 4 | 0/4 | 1/1 | 0.0097 | 68 |  |
| lw-chain-curie-nobel | delegate_evidence | yes | predicate | yes | 11 | 2/9 | 1/1 | 0.0218 | 168 |  |
| lw-chain-curie-nobel | dual | yes | predicate | yes | 4 | 2/2 | 0/0 | 0.0085 | 51 |  |
| lw-chain-curie-nobel | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0066 | 76 |  |
| lw-chain-dune-herbert | delegate | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0068 | 86 |  |
| lw-chain-dune-herbert | delegate_evidence | yes | predicate | yes | 6 | 2/4 | 0/1 | 0.0106 | 67 |  |
| lw-chain-dune-herbert | dual | yes | predicate | yes | 7 | 2/5 | 0/0 | 0.0142 | 104 |  |
| lw-chain-dune-herbert | guarded | yes | predicate | yes | 6 | 0/6 | 0/0 | 0.0107 | 87 |  |
| lw-chain-eiffel-gustave | delegate | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0063 | 59 |  |
| lw-chain-eiffel-gustave | delegate_evidence | yes | predicate | yes | 6 | 2/4 | 0/1 | 0.0125 | 61 |  |
| lw-chain-eiffel-gustave | dual | yes | predicate | yes | 4 | 2/2 | 0/0 | 0.0101 | 60 |  |
| lw-chain-eiffel-gustave | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0063 | 55 |  |
| lw-chain-python-guido | delegate | yes | predicate | yes | 7 | 3/4 | 0/1 | 0.0142 | 87 |  |
| lw-chain-python-guido | delegate_evidence | yes | predicate | yes | 7 | 3/4 | 0/1 | 0.0142 | 80 |  |
| lw-chain-python-guido | dual | yes | predicate | yes | 4 | 3/1 | 0/0 | 0.0094 | 31 |  |
| lw-chain-python-guido | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0063 | 43 |  |
| lw-chain-rust-hoare | delegate | yes | predicate | yes | 11 | 3/8 | 1/2 | 0.0342 | 175 |  |
| lw-chain-rust-hoare | delegate_evidence | no | predicate | yes | 11 | 3/8 | 1/1 | 0.0308 | 196 |  |
| lw-chain-rust-hoare | dual | yes | predicate | yes | 8 | 3/5 | 0/0 | 0.0220 | 177 |  |
| lw-chain-rust-hoare | guarded | no | predicate | yes | 7 | 0/7 | 0/0 | 0.0136 | 130 |  |
| lw-chain-turing-machine | delegate | yes | predicate | yes | 6 | 2/4 | 0/1 | 0.0153 | 66 |  |
| lw-chain-turing-machine | delegate_evidence | yes | predicate | yes | 7 | 3/4 | 0/1 | 0.0148 | 68 |  |
| lw-chain-turing-machine | dual | yes | predicate | yes | 4 | 2/2 | 0/0 | 0.0082 | 48 |  |
| lw-chain-turing-machine | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0065 | 84 |  |
| lw-ddg-mdn-fetch | delegate | yes | predicate | yes | 9 | 4/4 | 1/1 | 0.0127 | 85 |  |
| lw-ddg-mdn-fetch | delegate_evidence | yes | predicate | yes | 7 | 0/6 | 0/1 | 0.0116 | 101 |  |
| lw-ddg-mdn-fetch | dual | yes | predicate | yes | 5 | 1/3 | 0/0 | 0.0081 | 70 |  |
| lw-ddg-mdn-fetch | guarded | yes | predicate | yes | 6 | 0/5 | 0/0 | 0.0093 | 92 |  |
| lw-ddg-python-pathlib | delegate | yes | predicate | yes | 6 | 2/4 | 0/1 | 0.0092 | 57 |  |
| lw-ddg-python-pathlib | delegate_evidence | yes | predicate | yes | 10 | 2/8 | 1/1 | 0.0157 | 148 |  |
| lw-ddg-python-pathlib | dual | yes | predicate | yes | 5 | 5/0 | 0/0 | 0.0053 | 23 |  |
| lw-ddg-python-pathlib | guarded | yes | predicate | yes | 6 | 0/6 | 0/0 | 0.0104 | 121 |  |
| lw-eiffel-completed | delegate | yes | predicate | yes | 5 | 2/3 | 1/1 | 0.0111 | 95 |  |
| lw-eiffel-completed | delegate_evidence | yes | predicate | yes | 4 | 0/4 | 1/1 | 0.0108 | 60 |  |
| lw-eiffel-completed | dual | yes | predicate | yes | 4 | 3/1 | 0/0 | 0.0082 | 43 |  |
| lw-eiffel-completed | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0042 | 45 |  |
| lw-github-browser-use-license | delegate | yes | predicate | yes | 1 | 0/1 | 0/0 | 0.0029 | 48 |  |
| lw-github-browser-use-license | delegate_evidence | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0054 | 69 |  |
| lw-github-browser-use-license | dual | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0093 | 49 |  |
| lw-github-browser-use-license | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0044 | 40 |  |
| lw-github-pyo3-issues | delegate | yes | predicate | yes | 3 | 0/3 | 1/1 | 0.0108 | 56 |  |
| lw-github-pyo3-issues | delegate_evidence | yes | predicate | yes | 3 | 0/3 | 1/1 | 0.0088 | 69 |  |
| lw-github-pyo3-issues | dual | yes | predicate | yes | 2 | 1/1 | 0/0 | 0.0046 | 34 |  |
| lw-github-pyo3-issues | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0048 | 38 |  |
| lw-gutenberg-pride | delegate | yes | predicate | yes | 3 | 1/2 | 1/1 | 0.0053 | 50 |  |
| lw-gutenberg-pride | delegate_evidence | yes | predicate | yes | 3 | 1/2 | 1/1 | 0.0052 | 37 |  |
| lw-gutenberg-pride | dual | yes | predicate | yes | 2 | 1/1 | 0/0 | 0.0036 | 37 |  |
| lw-gutenberg-pride | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0038 | 51 |  |
| lw-gutenberg-top | delegate | yes | predicate | yes | 3 | 1/2 | 1/1 | 0.0054 | 44 |  |
| lw-gutenberg-top | delegate_evidence | yes | predicate | yes | 3 | 1/2 | 1/1 | 0.0053 | 34 |  |
| lw-gutenberg-top | dual | yes | predicate | yes | 2 | 2/0 | 0/0 | 0.0020 | 15 |  |
| lw-gutenberg-top | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0037 | 38 |  |
| lw-linux-creator | delegate | yes | predicate | yes | 4 | 2/2 | 0/1 | 0.0071 | 55 |  |
| lw-linux-creator | delegate_evidence | yes | predicate | yes | 7 | 3/4 | 1/1 | 0.0113 | 121 |  |
| lw-linux-creator | dual | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0055 | 60 |  |
| lw-linux-creator | guarded | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0091 | 133 |  |
| lw-mdn-418 | delegate | yes | predicate | yes | 6 | 0/6 | 0/0 | 0.0081 | 93 |  |
| lw-mdn-418 | delegate_evidence | yes | predicate | yes | 10 | 0/10 | 0/0 | 0.0119 | 203 |  |
| lw-mdn-418 | dual | yes | predicate | yes | 9 | 0/9 | 0/0 | 0.0192 | 142 |  |
| lw-mdn-418 | guarded | yes | predicate | yes | 10 | 0/10 | 0/0 | 0.0139 | 169 |  |
| lw-mdn-array-map | delegate | yes | predicate | yes | 4 | 0/3 | 0/1 | 0.0053 | 55 |  |
| lw-mdn-array-map | delegate_evidence | yes | predicate | yes | 3 | 0/2 | 0/0 | 0.0040 | 65 |  |
| lw-mdn-array-map | dual | yes | predicate | yes | 3 | 0/2 | 0/0 | 0.0055 | 62 |  |
| lw-mdn-array-map | guarded | yes | predicate | yes | 4 | 0/3 | 0/0 | 0.0050 | 109 |  |
| lw-mdn-font-weight | delegate | yes | predicate | yes | 9 | 1/6 | 0/1 | 0.0118 | 124 |  |
| lw-mdn-font-weight | delegate_evidence | yes | predicate | yes | 7 | 1/4 | 0/1 | 0.0084 | 106 |  |
| lw-mdn-font-weight | dual | yes | predicate | yes | 3 | 1/2 | 0/0 | 0.0060 | 53 |  |
| lw-mdn-font-weight | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0058 | 77 |  |
| lw-pride-author | delegate | yes | predicate | yes | 7 | 1/6 | 1/1 | 0.0162 | 162 |  |
| lw-pride-author | delegate_evidence | yes | predicate | yes | 4 | 2/2 | 1/1 | 0.0081 | 59 |  |
| lw-pride-author | dual | yes | predicate | yes | 3 | 2/1 | 0/0 | 0.0060 | 87 |  |
| lw-pride-author | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0040 | 42 |  |
| lw-pydocs-keyerror | delegate | yes | predicate | yes | 8 | 0/8 | 0/0 | 0.0154 | 185 |  |
| lw-pydocs-keyerror | delegate_evidence | no | predicate | no | 10 | 0/10 | 0/1 | 0.0177 | 150 |  |
| lw-pydocs-keyerror | dual | yes | predicate | yes | 8 | 0/8 | 0/0 | 0.0178 | 183 |  |
| lw-pydocs-keyerror | guarded | yes | predicate | yes | 9 | 0/9 | 0/0 | 0.0140 | 184 |  |
| lw-pydocs-lru-cache | delegate | yes | predicate | yes | 8 | 3/5 | 1/1 | 0.0121 | 99 |  |
| lw-pydocs-lru-cache | delegate_evidence | yes | predicate | yes | 7 | 1/6 | 1/1 | 0.0137 | 118 |  |
| lw-pydocs-lru-cache | dual | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0064 | 58 |  |
| lw-pydocs-lru-cache | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0060 | 78 |  |
| lw-pydocs-pathlib | delegate | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0043 | 132 |  |
| lw-pydocs-pathlib | delegate_evidence | yes | predicate | yes | 4 | 2/2 | 1/1 | 0.0071 | 52 |  |
| lw-pydocs-pathlib | dual | yes | predicate | yes | 3 | 2/1 | 0/0 | 0.0069 | 28 |  |
| lw-pydocs-pathlib | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0049 | 76 |  |
| lw-pypi-browser-use | delegate | yes | predicate | yes | 5 | 2/3 | 1/1 | 0.0073 | 48 |  |
| lw-pypi-browser-use | delegate_evidence | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0039 | 34 |  |
| lw-pypi-browser-use | dual | yes | predicate | yes | 4 | 3/1 | 0/0 | 0.0047 | 42 |  |
| lw-pypi-browser-use | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0037 | 33 |  |
| lw-pypi-requests-license | delegate | yes | predicate | yes | 5 | 2/3 | 0/1 | 0.0066 | 39 |  |
| lw-pypi-requests-license | delegate_evidence | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0057 | 44 |  |
| lw-pypi-requests-license | dual | yes | predicate | yes | 4 | 2/2 | 0/0 | 0.0056 | 37 |  |
| lw-pypi-requests-license | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0037 | 38 |  |
| lw-python-creator | delegate | yes | predicate | yes | 3 | 0/3 | 0/1 | 0.0078 | 70 |  |
| lw-python-creator | delegate_evidence | yes | predicate | yes | 7 | 2/5 | 0/1 | 0.0138 | 122 |  |
| lw-python-creator | dual | yes | predicate | yes | 4 | 2/2 | 0/0 | 0.0131 | 73 |  |
| lw-python-creator | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0086 | 72 |  |
| lw-rfc-8259-format | delegate | yes | predicate | yes | 5 | 0/3 | 0/1 | 0.0076 | 83 |  |
| lw-rfc-8259-format | delegate_evidence | yes | predicate | yes | 8 | 0/6 | 0/1 | 0.0079 | 124 |  |
| lw-rfc-8259-format | dual | yes | predicate | yes | 6 | 2/2 | 0/0 | 0.0083 | 60 |  |
| lw-rfc-8259-format | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0041 | 58 |  |
| lw-rfc-9110 | delegate | yes | predicate | yes | 7 | 4/2 | 0/1 | 0.0089 | 67 |  |
| lw-rfc-9110 | delegate_evidence | yes | predicate | yes | 5 | 2/3 | 0/1 | 0.0077 | 83 |  |
| lw-rfc-9110 | dual | yes | predicate | yes | 3 | 1/1 | 0/0 | 0.0047 | 51 |  |
| lw-rfc-9110 | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0043 | 56 |  |
| lw-www-inventor | delegate | yes | predicate | yes | 4 | 0/4 | 0/1 | 0.0107 | 104 |  |
| lw-www-inventor | delegate_evidence | yes | predicate | yes | 8 | 2/6 | 1/1 | 0.0116 | 145 |  |
| lw-www-inventor | dual | yes | predicate | yes | 3 | 2/1 | 0/0 | 0.0066 | 43 |  |
| lw-www-inventor | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0044 | 64 |  |
