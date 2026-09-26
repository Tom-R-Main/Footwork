# Package B: authorization parity

Opened at `27c320b`. The audit's fourth probe (`browser_use_judge_failure`) and its note that "one
boundary" is a routing property, not a guarantee that each route's meaning is judged. Browser task
grants (`authorized_actions: [submit]`, `[delete]`) are keyword scopes the Q experiments froze;
changing their semantics changes those experiments' configuration, so B3 is scoped to the operator and
native paths.

## B1 · prediction · 2026-09-26 12:23
Question: what happens on each surface when the destructive judgment cannot give an answer?
Hypothesis: the browser path returns no pause on any judge exception (`DualProcessAgent._destructive_judgment` catches and returns None); the native `Authorizer` pauses on an exception but treats an empty result as p=0.0, an allow; a result of the wrong length crashes the browser step (`zip(strict=True)` outside the try) rather than pausing.
Alternatives: judge implementations never return malformed output in practice, so only the exception case matters.
Test: unit tests with fake judges on both surfaces: raising, returning [], returning fewer probabilities than targets, returning NaN or a string.
Predicts: before the fix, browser: exception and [] allow, short list raises; native: exception pauses, [] and NaN allow. After: every case pauses with a reason naming the failure, and a working judge below the floor still allows.
Against: an existing browser test or arm relies on the fallback allowing (a failing test in test_agent_loop.py or the Q arms' tests), which would mean the fallback is load-bearing somewhere and needs a stated policy rather than a flip.
Refs: results/status-audit-20260926/probes.json (browser_use_judge_failure); agent.py _destructive_judgment; authorize.py Authorizer.check

## B2 · prediction · 2026-09-26 12:23
Question: does the same effect get the same decision whichever native route produces it?
Hypothesis: no. The judgment runs only on System 2's click, menu and hotkey routes; `enter` and `key` routes check keywords on reachable buttons but are never judged, so a default button the keyword list misses (Q8: "Submit order", "Finish") pauses when clicked and not when confirmed by Return.
Alternatives: the keyword list alone already catches the realistic default buttons, so the gap is theoretical.
Test: a parity table test: one window whose default button is "Submit order" (keyword-free, judged at 0.9 by a fake judge), acted on by click, menu item, Return, and hotkey return, all as System 2, on the native Authorizer.
Predicts: before: click, menu and hotkey pause; Return (enter route) does not. After judging the buttons a key or Return can reach: all four pause, and an authorized "Submit order" clears all four.
Against: the calculator scenarios or Q10b-style key presses start pausing (the judge sees Calculator's buttons, all harmless at low p, so they should not), or the extra judge call per key press shows up as a cost the scenarios make visible.
Refs: authorize.py Authorizer.check, _keyword

## B3 · prediction · 2026-09-26 12:23
Question: can an operator's grant for one action clear a different one?
Hypothesis: yes: `Authorizer.is_authorized` matches a grant as a substring of the label, so `--authorize Delete` clears "Delete account", and `--authorize Save` clears "Don't Save".
Alternatives: labels in practice are distinct enough that substring grants never collide.
Test: Authorizer tests: a grant "Delete" against labels "Delete" and "Delete account"; "Save" against "Save" and "Don't Save"; the special "replace" grant; the `authorize_all` flag unchanged. Fix: a grant matches the whole label (casefolded, whitespace-normalised), optionally prefixed by a route (`menu:File > Move to Trash`).
Predicts: before, both collisions clear; after, only the exact label clears, the existing operator scenarios (`test_delete_pauses_until_authorized...`, which authorizes "Delete" for the button "Delete") still pass, and `_paused_label` still prints a grant that clears the paused action.
Against: an existing scenario or Q15 case authorizes by a fragment (for example "Trash" for "File > Move to Trash") and breaks, which would mean operators rely on fragments and the change needs the pause message to print the exact grant (it already prints the label) and a migration note.
Refs: authorize.py is_authorized; cli.py _paused_label
