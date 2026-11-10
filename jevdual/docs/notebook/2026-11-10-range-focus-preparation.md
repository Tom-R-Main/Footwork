# Guarded foreground selection focus preparation

## RFP1 · prediction · 2026-11-10 18:44
Hypothesis: one explicit AXFocused preparation followed by independent application-focused-element and exact-window proof can expose selection evidence for an otherwise unfocused native web field without weakening selected-range identity/value guards.
Test: public CLI simulated-Mac scenarios where selected text is unreadable until focused, setter acknowledgement does not establish focus, focus points to a sibling/wrong window, and focusing changes field identity/value/selection. Verify single focus attempt, no key/pixel action, exact post-focus rematch and distinct preparation versus text-dispatch evidence.
Predicts: a successful independently proven focus and unchanged field permits one guarded selected-range text call; failed/unknown focus or changed field withholds all text. A preparation attempt is preserved as input uncertainty while code-boundary evidence records zero text characters when type_text was never reached.
Against: setter success alone permits text, a sibling/changed target is edited, whitespace is normalized, focus or text is retried, default whole-field behavior changes, or a preparation attempt is reported as proven no input.
Refs: docs/notebook/2026-11-10-suno-end-to-end.md; output/suno-20261110/range-edit-signal.txt; results/foreground-web-selection-20261110/report.md
