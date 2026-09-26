# Package D: receipts that name the effect, then Q12b

Plan: `docs/plans/next-work.md` (D). Package C found that Q11 and Q12's saucedemo no-ops were input
Chrome dropped after a breached-password login (`2026-09-26-c-trusted-input.md`, U16). Receipts said
"suspected no-op" and could not say why; a person reading them could not tell a lost click from an
ignored one.

## D1 · prediction · 2026-09-26 13:34
Question: can a receipt tell a click the page never received from one it received and ignored, and name changes the element diff misses?
Hypothesis: a capture-phase listener on the top document, installed once per document and read before and after each step (`jevdual.delivery`), separates the two: trusted input counted in the step means delivered; none, on the same document, means not delivered.
Alternatives: (a) browser-use's own reads (the DOM snapshot, scrollIntoView, focus calls) generate trusted events and make every step look delivered; (b) the listener misses delivered input that a page handler swallows (stopPropagation in the capture phase on window cannot be beaten by a later listener).
Test: browser tests in `tests/test_agent_loop.py`: the Q12 no-handler button (the click arrives, nothing changes) and the same page with `Input.setIgnoreInputEvents` on (the click is dropped, as the leak warning dropped it); then the C7 agent-loop run's receipts on saucedemo.
Predicts: no-handler button: `suspected_noop` with delivery `delivered`; ignored input: `suspected_noop` with `not_delivered` and the driver's text says the page received none of it; on the fixed saucedemo runs, no `not_delivered` receipt.
Against: the ignored-input case reads `delivered` (a), or the no-handler case reads `not_delivered` (b).
Refs: python/jevdual/delivery.py; tests/test_delivery.py
