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

## U17 · update · 2026-09-26 13:37
Observed: the Q12 receipt browser test was already failing before D (`interacted_element` None): browser-use gave the button index 7 in one launch and 8 in the next, and the test hard-coded 8. With D's first rule the no-handler click read `confirmed` ("focus moved to button#add"): a click focuses its own target. After the correction below, `tests/test_agent_loop.py` passes 10 of 10, twice: the no-handler click reads `suspected_noop`, delivery `delivered`; with `Input.setIgnoreInputEvents` on, `suspected_noop`, delivery `not_delivered`, "the page received none of it" in the driver's memory and `input: not_delivered` on the verifier's line.
Inferred: the delivery split works on both sides of D1 in a controlled page. Alternative (a) was half right: the browser's own consequences of dispatch (focus on the clicked target, scrollIntoView before a click) do move focus and scroll, so neither can confirm a click. Only the saucedemo part of D1 is open; the C7 run started before D, so it lands with Q12b's smoke.
Changes: scroll and focus are reported as "also ..." facts and confirm only a step made entirely of scroll actions that scrolled; a navigation between steps is reported on the next receipt and never credited to it. The receipt tests read the button's index from a live selector map.
Next: C7's outcome, then pre-register Q12b.

## U19 · update · 2026-09-26 13:46
Resolves: D1 = held
Observed: Q12b smoke (`results/q12b-smoke-20260926`, two tasks, both arms): on saucedemo every input step's receipt reads `delivered` (the login and the add-to-cart plus cart-link step) and no receipt reads `not_delivered`; both arms pass both tasks. The docs task's receipt arm got four `suspected_noop` receipts on `search_page`, `extract` and `wait` steps, and the saucedemo receipt arm two on `wait` steps.
Inferred: delivery separates lost from ignored input in the agent loop as in the controlled tests. A "no change" receipt on a step that dispatches nothing is true and says nothing; it inflated Q12's no-op counts on docs pages as well.
Changes: steps made only of read-only actions (`jevdual.delivery.READ_ONLY_ACTIONS`) get no receipt. Applied before Q12b run 1; amendment appended to Q12b.md.
Next: Q12b runs 1 to 3.

## U26 · update · 2026-09-26 15:48
Observed: Q12b (`results/q12b-live-dev.md`): H0(c) by the rule. The delivery guardrail was not zero: every `ls-sort-cheapest` run on both arms had one `not_delivered` receipt on `select_dropdown`, a step that changed the page. A browser test with a dropdown on a page that does not otherwise react read `not_delivered` and `suspected_noop` on the old probe.
Inferred: two false receipts, both from the probe's model of input: browser-use sets a dropdown by script (untrusted `input` and `change`), which the probe did not count, and a selected value is invisible to the element diff.
Changes: every untrusted event counts as `by_script`; a `change` event is recorded ("a form control's value changed") and confirms a step made of dropdown or input actions, never a click. Browser test `test_a_dropdown_set_by_script_is_not_called_undelivered` fails on the old probe and passes on the new.
Next: D closes; receipts on the driver's side wait for Q16's claim check.

## S6 · summary · 2026-09-26 15:48
Established: receipts now say whether the page received the input (delivered, not delivered, by script, new document) separately from what changed, and report scroll, focus, value changes and navigation between steps; that field found the one false `not_delivered` pattern in 354 rows, and it is fixed. Q12b: on the repaired input path, delivering receipts lowered requests per unit of progress (−0.28 [−0.69, −0.01]) and cost 4 verified passes pooled with no-fact refusals up (H0(c)); the input fix itself moved verified passes 121 to 137 on `guarded`.
Uncertain: why no-fact refusals rise on the receipt arm (refused done texts were not recorded in this build; narrated process claims are the visible candidate).
Decision: receipts stay recorded on every arm and are not delivered to the driver by default. Re-measure delivery only on the claim check Q16 settles.
Refs: results/q12b-live-dev.md; python/jevdual/delivery.py
