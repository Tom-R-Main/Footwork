# Guarded foreground selection focus preparation

## RFP1 · prediction · 2026-11-10 18:44
Hypothesis: one explicit AXFocused preparation followed by independent application-focused-element and exact-window proof can expose selection evidence for an otherwise unfocused native web field without weakening selected-range identity/value guards.
Test: public CLI simulated-Mac scenarios where selected text is unreadable until focused, setter acknowledgement does not establish focus, focus points to a sibling/wrong window, and focusing changes field identity/value/selection. Verify single focus attempt, no key/pixel action, exact post-focus rematch and distinct preparation versus text-dispatch evidence.
Predicts: a successful independently proven focus and unchanged field permits one guarded selected-range text call; failed/unknown focus or changed field withholds all text. A preparation attempt is preserved as input uncertainty while code-boundary evidence records zero text characters when type_text was never reached.
Against: setter success alone permits text, a sibling/changed target is edited, whitespace is normalized, focus or text is retried, default whole-field behavior changes, or a preparation attempt is reported as proven no input.
Refs: docs/notebook/2026-11-10-suno-end-to-end.md; output/suno-20261110/range-edit-signal.txt; results/foreground-web-selection-20261110/report.md

## RFP2 · update · 2026-11-10 18:48
Resolves: RFP1 = held
Observed: eight public CLI cases failed before source repair; 43 focus/selection scenarios and 695 affected source/contract tests now pass. Setter acknowledgement alone, wrong/missing focus, changed raw whitespace/value/identity/selection and stolen focus withhold text. Preparation attempts retain overall input uncertainty while the unreachable type_text boundary supplies separate zero-text evidence. Actual host bridge symbols import successfully without UI reads or input.
Inferred: bounded independent focus proof plus post-focus requalification can expose an unfocused field's selection without treating missing selected text as empty or normalizing its terminal LF.
Changes: RFP1's heading was entered one minute ahead of the observed clock (18:44 versus 18:43); preregistration order is established by f7dcb32, before the baseline. No earlier entry was rewritten.
Next: freeze source for parent-owned live qualification using the unchanged project-local SDK overlay.
Refs: results/range-focus-preparation-20261110/report.md; results/range-focus-preparation-20261110/baseline.txt; results/range-focus-preparation-20261110/focused.txt

## RFP3 · summary · 2026-11-10 18:48
Established: explicit foreground range edits perform one focus setter, independent application element/key-window proof, fresh unchanged identity/value revalidation and exact selection proof before one paced text call. Focus preparation, genuine SDK no-text refusals and uncertain text dispatch remain distinct evidence.
Uncertain: no worker live UI qualification occurred. Sequential AX/focus/selection checks do not create an atomic renderer transaction or establish DOM/server acceptance. Existing whole-field selection semantics and historical unknown receipts remain unchanged.
Decision: hand off frozen source with no SDK rebuild/global installation; parent must inspect actual rendered results before claiming successful song editing.
Refs: results/range-focus-preparation-20261110/report.md
