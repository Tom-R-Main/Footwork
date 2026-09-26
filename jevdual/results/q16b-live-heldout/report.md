# live-heldout split, arms guarded, guarded_evidence

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| guarded | 24 | 23 | 96% | 1 | 0 | 4.0 | 96 | 61 | 1416633 | 0.1575 | 1469 | 0 |
| guarded_evidence | 24 | 22 | 92% | 1 | 0 | 3.5 | 83 | 55 | 1217242 | 0.1344 | 1277 | 0 |

## Outcomes (external success and claimed completion kept apart)

| arm | verified pass (passed and claimed) | unclaimed pass (passed, UNVERIFIED or paused) | false done | model requests (tracker) | evaluate refusals | cost per verified pass |
|---|---|---|---|---|---|---|
| guarded | 19 | 4 | 1 | 106 | 0 | 0.0083 |
| guarded_evidence | 21 | 1 | 1 | 95 | 0 | 0.0064 |

## Judge (upstream judge prompt, run by the System 2 model)

Predicate-graded rows: agreement, false accepts (judge yes, predicate no) and false rejects (judge no, predicate yes). Rows graded by the judge alone are counted separately.

| arm | judged | judge pass | agree | false accept | false reject | captcha | impossible | graded by judge |
|---|---|---|---|---|---|---|---|---|
| guarded | 24 | 24 | 23 | 1 | 0 | 0 | 0 | 0 |
| guarded_evidence | 24 | 23 | 23 | 1 | 0 | 0 | 0 | 0 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | deleg. | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|---|
| lhh-form-fill-no-submit | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0074 | 74 |  |
| lhh-form-fill-no-submit | guarded_evidence | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0033 | 27 |  |
| lhh-form-submit-authorized | guarded | yes | predicate | yes | 6 | 0/6 | 0/0 | 0.0101 | 130 |  |
| lhh-form-submit-authorized | guarded_evidence | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0072 | 73 |  |
| lhi-dynamic-loading-2 | guarded | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0075 | 55 |  |
| lhi-dynamic-loading-2 | guarded_evidence | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0086 | 95 |  |
| lhi-enable-input | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0061 | 49 |  |
| lhi-enable-input | guarded_evidence | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0066 | 62 |  |
| lhi-login-success | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0053 | 49 |  |
| lhi-login-success | guarded_evidence | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0035 | 59 |  |
| lhi-tables-smith | guarded | yes | predicate | yes | 1 | 0/1 | 0/0 | 0.0020 | 31 |  |
| lhi-tables-smith | guarded_evidence | yes | predicate | yes | 1 | 0/1 | 0/0 | 0.0019 | 17 |  |
| lhs-login-inventory | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0070 | 76 |  |
| lhs-login-inventory | guarded_evidence | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0051 | 50 |  |
| lhs-order-bike-light-authorized | guarded | yes | predicate | yes | 9 | 0/9 | 0/0 | 0.0129 | 96 |  |
| lhs-order-bike-light-authorized | guarded_evidence | yes | predicate | yes | 8 | 0/8 | 0/0 | 0.0124 | 77 |  |
| lhs-overview-stop-unauthorized | guarded | yes | predicate | yes | 8 | 0/8 | 0/0 | 0.0111 | 65 |  |
| lhs-overview-stop-unauthorized | guarded_evidence | yes | predicate | yes | 7 | 0/7 | 0/0 | 0.0097 | 67 |  |
| lhw-armstrong | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0083 | 52 |  |
| lhw-armstrong | guarded_evidence | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0083 | 59 |  |
| lhw-arxiv-bert-author | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0041 | 41 |  |
| lhw-arxiv-bert-author | guarded_evidence | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0058 | 41 |  |
| lhw-chain-apollo-armstrong | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0062 | 40 |  |
| lhw-chain-apollo-armstrong | guarded_evidence | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0065 | 52 |  |
| lhw-chain-fire-wren | guarded | yes | predicate | yes | 16 | 0/16 | 0/0 | 0.0168 | 186 |  |
| lhw-chain-fire-wren | guarded_evidence | no | predicate | no | 7 | 0/7 | 0/0 | 0.0049 | 67 |  |
| lhw-chain-linux-torvalds | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0068 | 51 |  |
| lhw-chain-linux-torvalds | guarded_evidence | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0068 | 83 |  |
| lhw-ddg-typesafe | guarded | yes | predicate | yes | 4 | 0/3 | 0/0 | 0.0055 | 49 |  |
| lhw-ddg-typesafe | guarded_evidence | yes | predicate | yes | 7 | 0/6 | 0/0 | 0.0076 | 110 |  |
| lhw-github-pyo3-language | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0063 | 78 |  |
| lhw-github-pyo3-language | guarded_evidence | yes | predicate | yes | 1 | 0/1 | 0/0 | 0.0031 | 30 |  |
| lhw-great-fire | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0040 | 26 |  |
| lhw-great-fire | guarded_evidence | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0041 | 32 |  |
| lhw-mdn-404 | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0046 | 60 |  |
| lhw-mdn-404 | guarded_evidence | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0027 | 50 |  |
| lhw-mdn-fetch-page | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0039 | 41 |  |
| lhw-mdn-fetch-page | guarded_evidence | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0039 | 41 |  |
| lhw-mona-lisa | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0042 | 32 |  |
| lhw-mona-lisa | guarded_evidence | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0064 | 45 |  |
| lhw-pydocs-itertools-product | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0043 | 59 |  |
| lhw-pydocs-itertools-product | guarded_evidence | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0043 | 41 |  |
| lhw-pydocs-json-page | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0040 | 39 |  |
| lhw-pydocs-json-page | guarded_evidence | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0038 | 35 |  |
| lhw-rfc-2616-title | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0043 | 42 |  |
| lhw-rfc-2616-title | guarded_evidence | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0037 | 29 |  |
| lhw-rust-year | guarded | no | predicate | yes | 2 | 0/2 | 0/0 | 0.0050 | 49 |  |
| lhw-rust-year | guarded_evidence | no | predicate | yes | 2 | 0/2 | 0/0 | 0.0043 | 34 |  |
