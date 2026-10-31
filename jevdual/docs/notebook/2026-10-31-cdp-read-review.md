# CDP observation review and installed Linux check

## CR1 · prediction · 2026-10-31 11:59
Question: does the observation composer disclose its coverage limits and redact valid compound autocomplete fields?
Hypothesis: the current prefix-only sensitive-field check exposes credit-card and one-time-code values when autocomplete includes standard section/address tokens; the complete flag also overstates coverage when custom controls are omitted.
Test: compose fixed AX/DOM replies with compound autocomplete values and assert secrets are absent from the complete semantic output; assert an unported custom-control surface makes elements incomplete. Run these before the fix, then rerun with existing real-Chrome checks. Add an installed-wheel Ubuntu check with only the browser effector's dependencies, explicitly without CUA or browser-use; this checks the effector, not the future light installation recipe.
Predicts: compound sensitive-field cases and coverage assertions fail on ee5d010; token-aware redaction and honest completeness fix them without altering the declared fixture controls. The installed Ubuntu wheel observes headless Chrome and refuses mutations before dispatch.
Against: the original composer already redacts those values or reports incomplete coverage; revised code exposes a sensitive value or loses the declared fixture controls; the installed Linux browser check cannot run without CUA or browser-use.
Refs: docs/plans/light-profile-20261030.md; tests/test_cdp_effector.py; python/jevdual/effectors/cdp/snapshot.py; PR 16 review.
