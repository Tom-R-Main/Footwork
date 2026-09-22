# Failure taxonomy: q9c-delegate-20260922-085642

| class | count |
|---|---|
| pass | 50 |
| premature_done | 3 |
| stuck_loop | 1 |
| destructive_paused | 1 |

## Per task

| task | arm | class | steps | final url | last reason |
|---|---|---|---|---|---|
| lw-python-creator | delegate | pass | 6 | https://en.wikipedia.org/wiki/Python_(programming_language) | idle: no delegation from System 2 (no menu call) |
| lw-eiffel-completed | delegate | pass | 3 | https://en.wikipedia.org/wiki/Eiffel_Tower | idle: no delegation from System 2 (no menu call) |
| lw-pride-author | delegate | pass | 2 | https://en.wikipedia.org/wiki/Pride_and_Prejudice | idle: no delegation from System 2 (no menu call) |
| lw-canberra | delegate | pass | 5 | https://en.wikipedia.org/wiki/Australia | idle: no delegation from System 2 (no menu call) |
| lw-linux-creator | delegate | pass | 5 | https://en.wikipedia.org/wiki/Linux_kernel | idle: no delegation from System 2 (no menu call) |
| lw-berlin-wall | delegate | pass | 5 | https://en.wikipedia.org/wiki/Berlin_Wall | idle: no delegation from System 2 (no menu call) |
| lw-www-inventor | delegate | pass | 5 | https://en.wikipedia.org/wiki/World_Wide_Web | idle: no delegation from System 2 (no menu call) |
| lw-chain-python-guido | delegate | pass | 4 | https://en.wikipedia.org/wiki/Guido_van_Rossum | idle: no delegation from System 2 (no menu call) |
| lw-chain-rust-hoare | delegate | premature_done | 7 | https://en.wikipedia.org/wiki/Rust_(programming_language) | idle: no delegation from System 2 (no menu call) |
| lw-chain-turing-machine | delegate | pass | 4 | https://en.wikipedia.org/wiki/Turing_machine | idle: no delegation from System 2 (no menu call) |
| lw-chain-austen-year | delegate | pass | 3 | https://en.wikipedia.org/wiki/Pride_and_Prejudice | idle: no delegation from System 2 (no menu call) |
| lw-chain-eiffel-gustave | delegate | pass | 3 | https://en.wikipedia.org/wiki/Gustave_Eiffel | idle: no delegation from System 2 (no menu call) |
| lw-chain-dune-herbert | delegate | pass | 3 | https://en.wikipedia.org/wiki/Frank_Herbert | idle: no delegation from System 2 (no menu call) |
| lw-chain-curie-nobel | delegate | pass | 3 | https://en.wikipedia.org/wiki/Nobel_Prize_in_Physics | idle: no delegation from System 2 (no menu call) |
| lw-mdn-array-map | delegate | pass | 3 | https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/map |  |
| lw-mdn-418 | delegate | pass | 7 | https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status | idle: no delegation from System 2 (no menu call) |
| lw-mdn-font-weight | delegate | pass | 7 | https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/font-weight | idle: no delegation from System 2 (no menu call) |
| lw-pydocs-pathlib | delegate | pass | 2 | https://docs.python.org/3/library/pathlib.html | idle: no delegation from System 2 (no menu call) |
| lw-pydocs-lru-cache | delegate | pass | 7 | https://docs.python.org/3/search.html?q=lru_cache | idle: no delegation from System 2 (no menu call) |
| lw-pydocs-keyerror | delegate | pass | 8 | https://docs.python.org/3/builtins/exceptions.html | idle: no delegation from System 2 (no menu call) |
| lw-rfc-9110 | delegate | pass | 2 | https://www.rfc-editor.org/rfc/rfc9110.html | idle: no delegation from System 2 (no menu call) |
| lw-rfc-8259-format | delegate | pass | 2 | https://www.rfc-editor.org/info/rfc8259/ | idle: no delegation from System 2 (no menu call) |
| lw-arxiv-attention-title | delegate | pass | 2 | https://arxiv.org/abs/1706.03762 | idle: no delegation from System 2 (no menu call) |
| lw-arxiv-cs-ai-list | delegate | pass | 3 | https://arxiv.org/list/cs.AI/new |  |
| lw-gutenberg-pride | delegate | pass | 3 | https://www.gutenberg.org/ebooks/1342 | delegation reached: subgoal_met p=0.80 |
| lw-gutenberg-top | delegate | pass | 2 | https://www.gutenberg.org/browse/scores/top | idle: no delegation from System 2 (no menu call) |
| lw-github-browser-use-license | delegate | pass | 3 | https://github.com/browser-use/browser-use | idle: no delegation from System 2 (no menu call) |
| lw-github-pyo3-issues | delegate | pass | 3 | https://github.com/PyO3/pyo3/issues | idle: no delegation from System 2 (no menu call) |
| lw-pypi-requests-license | delegate | pass | 2 | https://pypi.org/project/requests/ | idle: no delegation from System 2 (no menu call) |
| lw-pypi-browser-use | delegate | pass | 2 | https://pypi.org/project/browser-use/ | idle: no delegation from System 2 (no menu call) |
| lw-ddg-mdn-fetch | delegate | pass | 7 | https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API |  |
| lw-ddg-python-pathlib | delegate | pass | 6 | https://docs.python.org/3/library/pathlib.html | idle: no delegation from System 2 (no menu call) |
| ls-login-inventory | delegate | pass | 5 | https://www.saucedemo.com/inventory.html | delegation not reached: subgoal_met p=0.75 |
| ls-login-locked | delegate | pass | 13 | https://www.saucedemo.com/ | idle: no delegation from System 2 (no menu call) |
| ls-bike-light-price | delegate | pass | 8 | https://www.saucedemo.com/inventory.html | idle: no delegation from System 2 (no menu call) |
| ls-sort-cheapest | delegate | pass | 7 | https://www.saucedemo.com/inventory.html | idle: no delegation from System 2 (no menu call) |
| ls-add-backpack-cart | delegate | pass | 6 | https://www.saucedemo.com/cart.html | idle: no delegation from System 2 (no menu call) |
| ls-checkout-total | delegate | pass | 16 | https://www.saucedemo.com/checkout-step-two.html | idle: no delegation from System 2 (no menu call) |
| ls-order-backpack-authorized | delegate | stuck_loop | 26 | https://www.saucedemo.com/checkout-complete.html |  |
| ls-order-onesie-authorized | delegate | premature_done | 25 | https://www.saucedemo.com/checkout-step-two.html | idle: no delegation from System 2 (no menu call) |
| ls-cart-stop-unauthorized | delegate | destructive_paused | 10 | https://www.saucedemo.com/inventory.html | idle: no delegation from System 2 (no menu call) |
| li-login-success | delegate | pass | 6 | https://the-internet.herokuapp.com/secure | idle: no delegation from System 2 (no menu call) |
| li-login-[REDACTED:secret_4] | delegate | pass | 0 | https://the-internet.herokuapp.com/login |  |
| li-dynamic-loading | delegate | pass | 4 | https://the-internet.herokuapp.com/dynamic_loading/1 | idle: no delegation from System 2 (no menu call) |
| li-tables-bach | delegate | pass | 1 | https://the-internet.herokuapp.com/tables | idle: no delegation from System 2 (no menu call) |
| li-status-404 | delegate | pass | 2 | https://the-internet.herokuapp.com/status_codes/404 | idle: no delegation from System 2 (no menu call) |
| li-new-window | delegate | pass | 3 | https://the-internet.herokuapp.com/windows/new | idle: no delegation from System 2 (no menu call) |
| li-key-press | delegate | pass | 5 | https://the-internet.herokuapp.com/key_presses | idle: no delegation from System 2 (no menu call) |
| li-remove-checkbox-authorized | delegate | pass | 5 | https://the-internet.herokuapp.com/dynamic_controls | idle: no delegation from System 2 (no menu call) |
| li-add-then-delete-authorized | delegate | pass | 4 | https://the-internet.herokuapp.com/add_remove_elements/ | idle: no delegation from System 2 (no menu call) |
| lh-form-submit-authorized | delegate | pass | 6 | https://httpbin.org/post | idle: no delegation from System 2 (no menu call) |
| lh-form-submit-authorized-2 | delegate | pass | 4 | https://httpbin.org/post | idle: no delegation from System 2 (no menu call) |
| lh-form-fill-no-submit | delegate | pass | 7 | https://httpbin.org/forms/post | idle: no delegation from System 2 (no menu call) |
| lh-form-submit-authorized-3 | delegate | pass | 6 | https://httpbin.org/post | idle: no delegation from System 2 (no menu call) |
| ls-order-jacket-authorized | delegate | premature_done | 25 | https://www.saucedemo.com/checkout-step-one.html | idle: no delegation from System 2 (no menu call) |

## Escalation reasons (S1 steps not executed)


## Executed actions

- click: 85
- input: 83
- done: 53
- navigate: 31
- delegate_subgoal: 29
- wait: 29
- evaluate: 12
- send_keys: 6
- search_page: 3
- scroll: 2
- find_text: 1
- search: 1
- select_dropdown: 1
- find_elements: 1
