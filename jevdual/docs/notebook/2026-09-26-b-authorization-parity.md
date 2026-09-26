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

## U5 · update · 2026-09-26 12:27
Resolves: B1 = held
Observed: before the change the browser path let every malformed case through (all five parametrized cases failed) and the native path paused on an exception and on non-numeric text (`float("high")` raises inside its try) but allowed [], a short list and NaN. After: both surfaces pause on all five, through one `checked_probabilities`; a working judge below the floor still allows; no existing test relied on the fallback (525 pass). The audit probe now returns a pause.
Inferred: the fallback was not load-bearing in any test. It may have been in live runs: failures were logged, not recorded in `gate_judgments`, so how often Q8 to Q12 runs passed a step on a failed judgment cannot be counted from their results. From now on a failure is recorded with its error and pauses, so a browser run with a flaky judge ends paused where it used to continue; that is a configuration change for any future Q run.
Next: B2.
Refs: tests/test_authorization_parity.py; agent.py _destructive_judgment; authorize.py checked_probabilities

## U6 · update · 2026-09-26 12:27
Resolves: B2 = held
Observed: before, click, menu and hotkey return paused on a "Submit order" judged at 0.9, while `enter` and `key return` did not. After judging the buttons a key, chord or Return can reach, all five pause, a grant for "Submit order" clears all five, and a key on a window of harmless buttons does not pause. Writing the test for B3's clause about printed grants showed the new pause named the key ("confirm the default button") first, so the grant it suggested authorized the key rather than the button; the reason now names the button first.
Inferred: the Against case is not settled: every scenario in test_session_scenarios.py runs `do` with `--no-judge`, so the calculator scenarios could not have shown a new pause, and the cost of one judged call per System 2 key press (all visible buttons in one request) is unmeasured.
Changes: a scenario with the judge on is owed before this is called parity in practice; Q10b's guarded arm is where the added call would show in cost.
Next: B3.

## U7 · update · 2026-09-26 12:27
Resolves: B3 = held
Observed: on cc5b038's code, "Delete" cleared "Delete account", "Save" cleared "Don't Save" and "Trash" cleared "File > Move to Trash". After: a grant matches the whole label (case and spacing aside), a menu path's whole path or final item, or a route-prefixed form; all nine cases pass; the operator scenario that authorizes "Delete" for the button "Delete" passes; for every route in the parity table, the grant `_paused_label` extracts from the pause clears that action. No native task or Q15 case uses grants, so no measured configuration changed. Browser task grants (keyword scopes such as `[submit]`) are unchanged by design.
Inferred: operator grants are now names of actions, not fragments; the browser path still grants by keyword and is the remaining half of "a grant names one action".
Next: summary.

## S2 · summary · 2026-09-26 12:27
Established: a judgment that cannot answer withholds the step on both surfaces; on the native path the same effect gets the same decision by click, menu, hotkey, key or Return; an operator grant clears only the action it names, and the pause prints that name. All seven audit probes now report corrected behaviour.
Uncertain: the added judge call per System 2 key press is unmeasured in cost; no scenario runs with the judge on; browser grants remain keyword scopes; how often past browser runs continued past a failed judgment is unrecoverable.
Decision: adopt. Package C (trusted input after navigation) is next and needs a local Chromium fixture, not a paid run.
Refs: tests/test_authorization_parity.py
