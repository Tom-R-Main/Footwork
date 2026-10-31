# CDP observation review and installed Linux check

## LCDR1 · prediction · 2026-10-31 11:59
Question: does the observation composer disclose its coverage limits and redact valid compound autocomplete fields?
Hypothesis: the current prefix-only sensitive-field check exposes credit-card and one-time-code values when autocomplete includes standard section/address tokens; the complete flag also overstates coverage when custom controls are omitted.
Test: compose fixed AX/DOM replies with compound autocomplete values and assert secrets are absent from the complete semantic output; assert an unported custom-control surface makes elements incomplete. Run these before the fix, then rerun with existing real-Chrome checks. Add an installed-wheel Ubuntu check with only the browser effector's dependencies, explicitly without CUA or browser-use; this checks the effector, not the future light installation recipe.
Predicts: compound sensitive-field cases and coverage assertions fail on ee5d010; token-aware redaction and honest completeness fix them without altering the declared fixture controls. The installed Ubuntu wheel observes headless Chrome and refuses mutations before dispatch.
Against: the original composer already redacts those values or reports incomplete coverage; revised code exposes a sensitive value or loses the declared fixture controls; the installed Linux browser check cannot run without CUA or browser-use.
Refs: docs/plans/light-profile-20261030.md; tests/test_cdp_effector.py; python/jevdual/effectors/cdp/snapshot.py; PR 16 review.

## LCDRU1 · update · 2026-10-31 12:03
Observed: all four added assertions failed on the original composer: three compound sensitive autocomplete values leaked and the unported custom-control surface reported complete. With token-aware redaction and incomplete coverage, all 17 CDP checks pass, including three real headless-Chrome checks on macOS. The already-locked websockets 15.0.1 is now a direct dependency; the updated lock passes offline consistency validation. The prediction heading was mechanically renamed from CR1 to LCDR1 because the notebook checker found an existing CR1 in another package; its prediction text is unchanged from fdd676e.
Resolves: LCDR1 = held
Next: run the installed Linux observation job and final corrected transport/lifecycle checks. Resource-baseline and mutation qualification remain separate.
Refs: output/cdp-takeover/privacy-before.txt; results/light-cdp-read-20261031/report.md.
