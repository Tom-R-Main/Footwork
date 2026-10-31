# CDP input targeting before the mutation slice

## LCDI1 · prediction · 2026-10-31 12:08
Question: does checking the focused field before a separate Input.insertText command ensure target-local delivery?
Hypothesis: page script can change focus after a correct check but before insertion; Input.insertText follows the new focus and changes the wrong field. Exact post-readback detects damage afterwards but does not prevent it.
Test: in a disposable headless Chrome with two ordinary local fixture fields, focus the intended field and read document.activeElement, then run a page timer that redirects focus to a sentinel. After independently observing the timer completed, issue one Input.insertText on that target session and read both exact values. This is a protocol qualification probe outside the disabled Footwork mutation effector, not an agent-authorized product action.
Predicts: the initial focus check is correct but only the sentinel receives the probe text; neither a successful acknowledgement nor checking the intended field after the send establishes safe targeted delivery.
Against: insertion stays attached to the previously checked field despite the independently observed focus change, or the protocol refuses without changing either field.
Refs: docs/plans/light-profile-20261030.md (L3a Actions); python/jevdual/effectors/cdp/operations.py (mutations remain refused).
