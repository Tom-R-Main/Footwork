# live-heldout split, arms guarded

| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| guarded | 24 | 23 | 96% | 0 | 1 | 4.0 | 96 | 57 | 1369460 | 0.1517 | 1297 | 0 |

## Outcomes (external success and claimed completion kept apart)

| arm | verified pass (passed and claimed) | unclaimed pass (passed, UNVERIFIED or paused) | false done | model requests (tracker) | evaluate refusals | cost per verified pass |
|---|---|---|---|---|---|---|
| guarded | 20 | 3 | 0 | 101 | 0 | 0.0076 |

## Judge (upstream judge prompt, run by the System 2 model)

Predicate-graded rows: agreement, false accepts (judge yes, predicate no) and false rejects (judge no, predicate yes). Rows graded by the judge alone are counted separately.

| arm | judged | judge pass | agree | false accept | false reject | captcha | impossible | graded by judge |
|---|---|---|---|---|---|---|---|---|
| guarded | 24 | 23 | 24 | 0 | 0 | 0 | 0 | 0 |

## Per task

| task | arm | pass | graded by | judge | steps | s1/s2 | deleg. | est. cost USD | wall s | error |
|---|---|---|---|---|---|---|---|---|---|---|
| lhh-form-fill-no-submit | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0035 | 36 |  |
| lhh-form-submit-authorized | guarded | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0076 | 83 |  |
| lhi-dynamic-loading-2 | guarded | yes | predicate | yes | 5 | 0/5 | 0/0 | 0.0087 | 82 |  |
| lhi-enable-input | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0062 | 61 |  |
| lhi-login-success | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0032 | 25 |  |
| lhi-tables-smith | guarded | yes | predicate | yes | 1 | 0/1 | 0/0 | 0.0022 | 37 |  |
| lhs-login-inventory | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0055 | 48 |  |
| lhs-order-bike-light-authorized | guarded | yes | predicate | yes | 11 | 0/11 | 0/0 | 0.0117 | 93 |  |
| lhs-overview-stop-unauthorized | guarded | yes | predicate | yes | 7 | 0/7 | 0/0 | 0.0097 | 61 |  |
| lhw-armstrong | guarded | yes | predicate | yes | 6 | 0/6 | 0/0 | 0.0114 | 77 |  |
| lhw-arxiv-bert-author | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0060 | 39 |  |
| lhw-chain-apollo-armstrong | guarded | yes | predicate | yes | 6 | 0/6 | 0/0 | 0.0114 | 80 |  |
| lhw-chain-fire-wren | guarded | no | predicate | no | 11 | 0/11 | 0/0 | 0.0104 | 83 |  |
| lhw-chain-linux-torvalds | guarded | yes | predicate | yes | 4 | 0/4 | 0/0 | 0.0066 | 48 |  |
| lhw-ddg-typesafe | guarded | yes | predicate | yes | 4 | 0/3 | 0/0 | 0.0059 | 59 |  |
| lhw-github-pyo3-language | guarded | yes | predicate | yes | 1 | 0/1 | 0/0 | 0.0031 | 26 |  |
| lhw-great-fire | guarded | yes | predicate | yes | 7 | 0/7 | 0/0 | 0.0090 | 120 |  |
| lhw-mdn-404 | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0026 | 38 |  |
| lhw-mdn-fetch-page | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0039 | 28 |  |
| lhw-mona-lisa | guarded | yes | predicate | yes | 3 | 0/3 | 0/0 | 0.0065 | 40 |  |
| lhw-pydocs-itertools-product | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0040 | 34 |  |
| lhw-pydocs-json-page | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0041 | 39 |  |
| lhw-rfc-2616-title | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0043 | 33 |  |
| lhw-rust-year | guarded | yes | predicate | yes | 2 | 0/2 | 0/0 | 0.0043 | 26 |  |
