# Failure taxonomy: live-dev-post-ledger-20260921-182626

| class | count |
|---|---|
| pass | 113 |
| premature_done | 33 |
| stuck_loop | 9 |
| policy_error | 5 |
| destructive_paused | 2 |
| budget_exhausted | 1 |
| low_confidence | 1 |
| needs_text | 1 |

## Per task

| task | arm | class | steps | final url | last reason |
|---|---|---|---|---|---|
| lw-python-creator | s1_only | premature_done | 3 | https://en.wikipedia.org/wiki/Python_(programming_language) | always-act arbiter |
| lw-python-creator | stock | pass | 3 | https://en.wikipedia.org/wiki/Python_(programming_language) |  |
| lw-python-creator | dual | pass | 3 | https://en.wikipedia.org/wiki/Python_(programming_language) | verification verify: uncertain: complete p=0.59, max unmet p |
| lw-eiffel-completed | s1_only | premature_done | 3 | https://en.wikipedia.org/wiki/Eiffel_Tower | always-act arbiter |
| lw-eiffel-completed | stock | pass | 3 | https://en.wikipedia.org/wiki/Eiffel_Tower |  |
| lw-eiffel-completed | dual | pass | 3 | https://en.wikipedia.org/wiki/Eiffel_Tower | verification verify: uncertain: complete p=0.79, max unmet p |
| lw-pride-author | s1_only | premature_done | 3 | https://en.wikipedia.org/wiki/Pride_and_Prejudice | always-act arbiter |
| lw-pride-author | stock | pass | 2 | https://en.wikipedia.org/wiki/Pride_and_Prejudice |  |
| lw-pride-author | dual | pass | 3 | https://en.wikipedia.org/wiki/Pride_and_Prejudice | verification verify: uncertain: complete p=0.75, max unmet p |
| lw-canberra | s1_only | premature_done | 3 | https://en.wikipedia.org/wiki/Australia | always-act arbiter |
| lw-canberra | stock | pass | 3 | https://en.wikipedia.org/wiki/Australia |  |
| lw-canberra | dual | pass | 2 | https://en.wikipedia.org/wiki/Australia | verification verify: task asks for an answer (answer_require |
| lw-linux-creator | s1_only | premature_done | 4 | https://en.wikipedia.org/wiki/Linux_kernel | always-act arbiter |
| lw-linux-creator | stock | pass | 2 | https://en.wikipedia.org/wiki/Linux_kernel |  |
| lw-linux-creator | dual | pass | 4 | https://en.wikipedia.org/wiki/Linux_kernel | policy error: api error: POST https://api.typesafe.ai/v1/sys |
| lw-berlin-wall | s1_only | premature_done | 3 | https://en.wikipedia.org/wiki/Berlin_Wall | always-act arbiter |
| lw-berlin-wall | stock | pass | 2 | https://en.wikipedia.org/wiki/Berlin_Wall |  |
| lw-berlin-wall | dual | pass | 3 | https://en.wikipedia.org/wiki/Berlin_Wall | verification verify: uncertain: complete p=0.79, max unmet p |
| lw-www-inventor | s1_only | premature_done | 4 | https://en.wikipedia.org/wiki/World_Wide_Web | always-act arbiter |
| lw-www-inventor | stock | pass | 3 | https://en.wikipedia.org/wiki/World_Wide_Web |  |
| lw-www-inventor | dual | pass | 4 | https://en.wikipedia.org/wiki/World_Wide_Web | verification verify: task asks for an answer (answer_require |
| lw-chain-python-guido | s1_only | pass | 4 | https://en.wikipedia.org/wiki/Guido_van_Rossum | always-act arbiter |
| lw-chain-python-guido | stock | pass | 3 | https://en.wikipedia.org/wiki/Guido_van_Rossum |  |
| lw-chain-python-guido | dual | pass | 4 | https://en.wikipedia.org/wiki/Guido_van_Rossum | verification accept: complete p=0.89, max unmet p=0.22 |
| lw-chain-rust-hoare | s1_only | budget_exhausted | 26 | https://en.wikipedia.org/wiki/Rust_(programming_language) |  |
| lw-chain-rust-hoare | stock | premature_done | 5 | https://en.wikipedia.org/wiki/Rust_(programming_language) |  |
| lw-chain-rust-hoare | dual | pass | 8 | https://en.wikipedia.org/w/index.php?title=Graydon_Hoare&redirect=no | verification verify: uncertain: complete p=0.53, max unmet p |
| lw-chain-turing-machine | s1_only | pass | 5 | https://en.wikipedia.org/wiki/Turing_machine | always-act arbiter |
| lw-chain-turing-machine | stock | pass | 3 | https://en.wikipedia.org/wiki/Turing_machine |  |
| lw-chain-turing-machine | dual | pass | 5 | https://en.wikipedia.org/wiki/Turing_machine | verification accept: complete p=0.90, max unmet p=0.29; ledg |
| lw-chain-austen-year | s1_only | premature_done | 4 | https://en.wikipedia.org/wiki/Pride_and_Prejudice | always-act arbiter |
| lw-chain-austen-year | stock | pass | 3 | https://en.wikipedia.org/wiki/Pride_and_Prejudice |  |
| lw-chain-austen-year | dual | pass | 4 | https://en.wikipedia.org/wiki/Pride_and_Prejudice | verification verify: uncertain: complete p=0.63, max unmet p |
| lw-chain-eiffel-gustave | s1_only | premature_done | 4 | https://en.wikipedia.org/wiki/Gustave_Eiffel | always-act arbiter |
| lw-chain-eiffel-gustave | stock | pass | 4 | https://en.wikipedia.org/wiki/Gustave_Eiffel |  |
| lw-chain-eiffel-gustave | dual | pass | 7 | https://en.wikipedia.org/wiki/Gustave_Eiffel | verification verify: uncertain: complete p=0.72, max unmet p |
| lw-chain-dune-herbert | s1_only | policy_error | 9 | https://en.wikipedia.org/wiki/Frank_Herbert | policy error: api error: POST https://api.typesafe.ai/v1/sys |
| lw-chain-dune-herbert | stock | pass | 4 | https://en.wikipedia.org/wiki/Frank_Herbert |  |
| lw-chain-dune-herbert | dual | pass | 4 | https://en.wikipedia.org/wiki/Frank_Herbert | policy error: api error: POST https://api.typesafe.ai/v1/sys |
| lw-chain-curie-nobel | s1_only | policy_error | 8 | https://en.wikipedia.org/wiki/Marie_Curie | policy error: api error: POST https://api.typesafe.ai/v1/sys |
| lw-chain-curie-nobel | stock | pass | 4 | https://en.wikipedia.org/wiki/Nobel_Prize_in_Physics |  |
| lw-chain-curie-nobel | dual | pass | 8 | https://en.wikipedia.org/wiki/Nobel_Prize_in_Physics | verification verify: uncertain: complete p=0.47, max unmet p |
| lw-mdn-array-map | s1_only | premature_done | 2 | https://array.prototype.map/ |  |
| lw-mdn-array-map | stock | pass | 4 | https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/map |  |
| lw-mdn-array-map | dual | pass | 4 | https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/map |  |
| lw-mdn-418 | s1_only | premature_done | 3 | https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/418 | always-act arbiter |
| lw-mdn-418 | stock | pass | 8 | https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status |  |
| lw-mdn-418 | dual | pass | 7 | https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status | verification verify: uncertain: complete p=0.51, max unmet p |
| lw-mdn-font-weight | s1_only | stuck_loop | 7 | https://developer.mozilla.org/en-US/ | always-act arbiter |
| lw-mdn-font-weight | stock | pass | 6 | https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/font-weight |  |
| lw-mdn-font-weight | dual | pass | 8 | https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/font-weight | verification verify: uncertain: complete p=0.64, max unmet p |
| lw-pydocs-pathlib | s1_only | pass | 3 | https://docs.python.org/3/library/pathlib.html | always-act arbiter |
| lw-pydocs-pathlib | stock | pass | 2 | https://docs.python.org/3/library/pathlib.html |  |
| lw-pydocs-pathlib | dual | pass | 3 | https://docs.python.org/3/library/pathlib.html | verification accept: complete p=0.94, max unmet p=0.12 |
| lw-pydocs-lru-cache | s1_only | premature_done | 3 | https://docs.python.org/3/library/functools.html | always-act arbiter |
| lw-pydocs-lru-cache | stock | pass | 3 | https://docs.python.org/3/search.html?q=lru_cache |  |
| lw-pydocs-lru-cache | dual | pass | 6 | https://docs.python.org/3/library/functools.html | verification verify: uncertain: complete p=0.64, max unmet p |
| lw-pydocs-keyerror | s1_only | premature_done | 7 | https://docs.python.org/3/builtins/exceptions.html#KeyError | always-act arbiter |
| lw-pydocs-keyerror | stock | pass | 6 | https://docs.python.org/3/builtins/exceptions.html |  |
| lw-pydocs-keyerror | dual | pass | 8 | https://docs.python.org/3/builtins/exceptions.html | verification reject: complete p=0.24; ledger carried 2 requi |
| lw-rfc-9110 | s1_only | pass | 6 | https://www.rfc-editor.org/info/rfc9110/ | always-act arbiter |
| lw-rfc-9110 | stock | pass | 2 | https://www.rfc-editor.org/rfc/rfc9110.html |  |
| lw-rfc-9110 | dual | pass | 4 | https://www.rfc-editor.org/rfc/rfc9110.html | verification accept: complete p=0.93, max unmet p=0.25 |
| lw-rfc-8259-format | s1_only | premature_done | 5 | https://www.rfc-editor.org/search/?q=8259 | always-act arbiter |
| lw-rfc-8259-format | stock | pass | 2 | https://www.rfc-editor.org/info/rfc8259/ |  |
| lw-rfc-8259-format | dual | pass | 4 | https://www.rfc-editor.org/info/rfc8259/ | verification verify: uncertain: complete p=0.85, max unmet p |
| lw-arxiv-attention-title | s1_only | premature_done | 5 | https://arxiv.org/abs/1706.03762 | always-act arbiter |
| lw-arxiv-attention-title | stock | pass | 2 | https://arxiv.org/abs/1706.03762 |  |
| lw-arxiv-attention-title | dual | pass | 2 | https://arxiv.org/abs/1706.03762 | verification verify: uncertain: complete p=0.74, max unmet p |
| lw-arxiv-cs-ai-list | s1_only | premature_done | 4 | https://cs.ai/ |  |
| lw-arxiv-cs-ai-list | stock | pass | 3 | https://arxiv.org/list/cs.AI/new |  |
| lw-arxiv-cs-ai-list | dual | pass | 4 | https://arxiv.org/list/cs.AI/new |  |
| lw-gutenberg-pride | s1_only | premature_done | 3 | https://www.gutenberg.org/cache/epub/1342/pg1342-images.html | always-act arbiter |
| lw-gutenberg-pride | stock | pass | 2 | https://www.gutenberg.org/ebooks/1342 |  |
| lw-gutenberg-pride | dual | pass | 4 | https://www.gutenberg.org/ebooks/1342 | policy error: api error: POST https://api.typesafe.ai/v1/sys |
| lw-gutenberg-top | s1_only | pass | 2 | https://www.gutenberg.org/browse/scores/top | always-act arbiter |
| lw-gutenberg-top | stock | pass | 2 | https://www.gutenberg.org/browse/scores/top |  |
| lw-gutenberg-top | dual | pass | 2 | https://www.gutenberg.org/browse/scores/top | verification accept: complete p=0.84, max unmet p=0.25 |
| lw-github-browser-use-license | s1_only | premature_done | 1 | https://github.com/browser-use/browser-use | always-act arbiter |
| lw-github-browser-use-license | stock | pass | 2 | https://github.com/browser-use/browser-use |  |
| lw-github-browser-use-license | dual | pass | 1 | https://github.com/browser-use/browser-use | verification verify: uncertain: complete p=0.77, max unmet p |
| lw-github-pyo3-issues | s1_only | policy_error | 6 | https://github.com/PyO3/pyo3 | policy error: api error: POST https://api.typesafe.ai/v1/sys |
| lw-github-pyo3-issues | stock | pass | 3 | https://github.com/PyO3/pyo3/issues |  |
| lw-github-pyo3-issues | dual | pass | 2 | https://github.com/PyO3/pyo3/issues | verification accept: complete p=0.96, max unmet p=0.03 |
| lw-pypi-requests-license | s1_only | premature_done | 4 | https://pypi.org/search/?q=requests | always-act arbiter |
| lw-pypi-requests-license | stock | pass | 2 | https://pypi.org/project/requests/ |  |
| lw-pypi-requests-license | dual | pass | 5 | https://pypi.org/project/requests/ | verification verify: uncertain: complete p=0.78, max unmet p |
| lw-pypi-browser-use | s1_only | premature_done | 6 | https://pypi.org/search/?q=browser-use | always-act arbiter |
| lw-pypi-browser-use | stock | pass | 2 | https://pypi.org/project/browser-use/ |  |
| lw-pypi-browser-use | dual | pass | 4 | https://pypi.org/project/browser-use/ | verification accept: complete p=0.92, max unmet p=0.18 |
| lw-ddg-mdn-fetch | s1_only | premature_done | 7 | https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API |  |
| lw-ddg-mdn-fetch | stock | pass | 4 | https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API |  |
| lw-ddg-mdn-fetch | dual | pass | 5 | https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch |  |
| lw-ddg-python-pathlib | s1_only | policy_error | 9 | https://duckduckgo.com/?ia=web&origin=funnel_home_website_measuresearchesaa_treatment&t=h_&q=python+pathlib+documentation | policy error: api error: POST https://api.typesafe.ai/v1/sys |
| lw-ddg-python-pathlib | stock | premature_done | 5 | https://docs.python.org/3/library/pathlib.html |  |
| lw-ddg-python-pathlib | dual | policy_error | 5 | https://docs.python.org/3/library/pathlib.html | verification verify: uncertain: complete p=0.70, max unmet p |
| ls-login-inventory | s1_only | pass | 4 | https://www.saucedemo.com/inventory.html | always-act arbiter |
| ls-login-inventory | stock | pass | 2 | https://www.saucedemo.com/inventory.html |  |
| ls-login-inventory | dual | pass | 4 | https://www.saucedemo.com/inventory.html | verification verify: uncertain: complete p=0.85, max unmet p |
| ls-login-locked | s1_only | premature_done | 4 | https://www.saucedemo.com/ | always-act arbiter |
| ls-login-locked | stock | pass | 2 | https://www.saucedemo.com/ |  |
| ls-login-locked | dual | pass | 5 | https://www.saucedemo.com/ | verification verify: task asks for an answer (answer_require |
| ls-bike-light-price | s1_only | stuck_loop | 26 | https://www.saucedemo.com/ |  |
| ls-bike-light-price | stock | pass | 3 | https://www.saucedemo.com/inventory.html |  |
| ls-bike-light-price | dual | pass | 5 | https://www.saucedemo.com/inventory.html | verification verify: uncertain: complete p=0.73, max unmet p |
| ls-sort-cheapest | s1_only | premature_done | 7 | https://www.saucedemo.com/inventory.html | always-act arbiter |
| ls-sort-cheapest | stock | pass | 3 | https://www.saucedemo.com/inventory.html |  |
| ls-sort-cheapest | dual | pass | 10 | https://www.saucedemo.com/inventory.html | verification verify: uncertain: complete p=0.71, max unmet p |
| ls-add-backpack-cart | s1_only | stuck_loop | 26 | https://www.saucedemo.com/ |  |
| ls-add-backpack-cart | stock | pass | 9 | https://www.saucedemo.com/cart.html |  |
| ls-add-backpack-cart | dual | destructive_paused | 9 | https://www.saucedemo.com/inventory.html | stuck: stuck 0.94 >= 0.85 at step 9 |
| ls-checkout-total | s1_only | stuck_loop | 26 | https://www.saucedemo.com/ |  |
| ls-checkout-total | stock | premature_done | 24 | https://www.saucedemo.com/checkout-step-one.html |  |
| ls-checkout-total | dual | destructive_paused | 9 | https://www.saucedemo.com/inventory.html | stuck: stuck 0.94 >= 0.85 at step 9 |
| ls-order-backpack-authorized | s1_only | stuck_loop | 26 | https://www.saucedemo.com/ |  |
| ls-order-backpack-authorized | stock | pass | 25 | https://www.saucedemo.com/checkout-complete.html |  |
| ls-order-backpack-authorized | dual | low_confidence | 26 | https://www.saucedemo.com/cart.html |  |
| ls-order-onesie-authorized | s1_only | stuck_loop | 26 | https://www.saucedemo.com/ |  |
| ls-order-onesie-authorized | stock | premature_done | 25 | https://www.saucedemo.com/checkout-step-one.html |  |
| ls-order-onesie-authorized | dual | pass | 13 | https://www.saucedemo.com/checkout-complete.html | verification accept: complete p=0.86, max unmet p=0.12 |
| ls-cart-stop-unauthorized | s1_only | stuck_loop | 26 | https://www.saucedemo.com/ |  |
| ls-cart-stop-unauthorized | stock | pass | 6 | https://www.saucedemo.com/checkout-step-two.html |  |
| ls-cart-stop-unauthorized | dual | pass | 11 | https://www.saucedemo.com/checkout-step-two.html | verification verify: uncertain: complete p=0.83, max unmet p |
| li-login-success | s1_only | pass | 4 | https://the-internet.herokuapp.com/secure | always-act arbiter |
| li-login-success | stock | pass | 3 | https://the-internet.herokuapp.com/secure |  |
| li-login-success | dual | pass | 4 | https://the-internet.herokuapp.com/secure | verification accept: complete p=0.91, max unmet p=0.11 |
| li-login-[REDACTED:secret_4] | s1_only | premature_done | 0 | https://the-internet.herokuapp.com/login |  |
| li-login-[REDACTED:secret_4] | stock | pass | 0 | https://the-internet.herokuapp.com/login |  |
| li-login-[REDACTED:secret_4] | dual | pass | 0 | https://the-internet.herokuapp.com/login |  |
| li-dynamic-loading | s1_only | premature_done | 6 | https://the-internet.herokuapp.com/dynamic_loading/1 | always-act arbiter |
| li-dynamic-loading | stock | pass | 3 | https://the-internet.herokuapp.com/dynamic_loading/1 |  |
| li-dynamic-loading | dual | pass | 4 | https://the-internet.herokuapp.com/dynamic_loading/1 | verification verify: uncertain: complete p=0.74, max unmet p |
| li-tables-bach | s1_only | premature_done | 1 | https://the-internet.herokuapp.com/tables | always-act arbiter |
| li-tables-bach | stock | pass | 1 | https://the-internet.herokuapp.com/tables |  |
| li-tables-bach | dual | pass | 1 | https://the-internet.herokuapp.com/tables | verification reject: Amount reported unmet with p=0.76 |
| li-status-404 | s1_only | pass | 2 | https://the-internet.herokuapp.com/status_codes/404 | always-act arbiter |
| li-status-404 | stock | pass | 2 | https://the-internet.herokuapp.com/status_codes/404 |  |
| li-status-404 | dual | pass | 2 | https://the-internet.herokuapp.com/status_codes/404 | verification accept: complete p=0.94, max unmet p=0.11 |
| li-new-window | s1_only | pass | 2 | https://the-internet.herokuapp.com/windows/new | always-act arbiter |
| li-new-window | stock | pass | 2 | https://the-internet.herokuapp.com/windows/new |  |
| li-new-window | dual | pass | 3 | https://the-internet.herokuapp.com/windows/new | verification accept: complete p=0.91, max unmet p=0.23 |
| li-key-press | s1_only | needs_text | 6 | https://the-internet.herokuapp.com/key_presses | type needs composed text |
| li-key-press | stock | pass | 3 | https://the-internet.herokuapp.com/key_presses |  |
| li-key-press | dual | pass | 4 | https://the-internet.herokuapp.com/key_presses | verification verify: task asks for an answer (answer_require |
| li-remove-checkbox-authorized | s1_only | premature_done | 3 | https://the-internet.herokuapp.com/dynamic_controls | always-act arbiter |
| li-remove-checkbox-authorized | stock | pass | 4 | https://the-internet.herokuapp.com/dynamic_controls |  |
| li-remove-checkbox-authorized | dual | pass | 4 | https://the-internet.herokuapp.com/dynamic_controls | verification verify: uncertain: complete p=0.72, max unmet p |
| li-add-then-delete-authorized | s1_only | pass | 4 | https://the-internet.herokuapp.com/add_remove_elements/ | always-act arbiter |
| li-add-then-delete-authorized | stock | pass | 4 | https://the-internet.herokuapp.com/add_remove_elements/ |  |
| li-add-then-delete-authorized | dual | pass | 21 | https://the-internet.herokuapp.com/add_remove_elements/ | verification reject: One Delete button clicked unmet with p= |
| lh-form-submit-authorized | s1_only | stuck_loop | 26 | https://httpbin.org/forms/post |  |
| lh-form-submit-authorized | stock | pass | 5 | https://httpbin.org/post |  |
| lh-form-submit-authorized | dual | pass | 3 | https://httpbin.org/post | verification accept: complete p=0.95, max unmet p=0.17 |
| lh-form-submit-authorized-2 | s1_only | pass | 7 | https://httpbin.org/post | always-act arbiter |
| lh-form-submit-authorized-2 | stock | pass | 3 | https://httpbin.org/post |  |
| lh-form-submit-authorized-2 | dual | pass | 3 | https://httpbin.org/post | verification accept: complete p=0.93, max unmet p=0.23 |
| lh-form-fill-no-submit | s1_only | pass | 4 | https://httpbin.org/forms/post | always-act arbiter |
| lh-form-fill-no-submit | stock | pass | 2 | https://httpbin.org/forms/post |  |
| lh-form-fill-no-submit | dual | pass | 4 | https://httpbin.org/forms/post | verification accept: complete p=0.87, max unmet p=0.28 |
| lh-form-submit-authorized-3 | s1_only | pass | 7 | https://httpbin.org/post | always-act arbiter |
| lh-form-submit-authorized-3 | stock | pass | 3 | https://httpbin.org/post |  |
| lh-form-submit-authorized-3 | dual | pass | 3 | https://httpbin.org/post | verification accept: complete p=0.92, max unmet p=0.26 |
| ls-order-jacket-authorized | s1_only | stuck_loop | 26 | https://www.saucedemo.com/ |  |
| ls-order-jacket-authorized | stock | premature_done | 25 | https://www.saucedemo.com/checkout-step-one.html |  |
| ls-order-jacket-authorized | dual | premature_done | 25 | https://www.saucedemo.com/checkout-step-one.html | no_effect: 2 consecutive steps with no visible change |

## Escalation reasons (S1 steps not executed)


## Executed actions

- input: 394
- click: 283
- done: 147
- navigate: 61
- send_keys: 41
- wait: 38
- evaluate: 29
- go_back: 12
- search_page: 12
- scroll: 10
- extract: 2
- select_dropdown: 2
- find_elements: 1
- find_text: 1
- search: 1
