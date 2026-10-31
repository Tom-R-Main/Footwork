# Light effector boundary

## LP1 · prediction · 2026-10-30 21:03
Hypothesis: a lazy CUA compatibility adapter can own SDK construction, input constructors and browser authorization without changing current driver requests, receipts or awaited cleanup.
Test: run the existing native/session/browser/coexistence/SDK seam scenarios before and after; add a subprocess import/discovery audit with optional packages blocked, missing-package versus transitive-failure controls and an AST SDK-import boundary check. Build the pure capability wheel and exercise installed discovery outside the checkout. Use the existing fixture outcomes and strict dispatch/refusal assertions as the oracle.
Predicts: discovery remains available without optional imports; SDK request/result objects and authorization decisions remain unchanged; existing scenario effects, no-send refusals and unknown outcomes remain unchanged; SDK imports appear only in effectors/cua.py.
Against: any scope/dispatch/refusal/evidence outcome changes, a shutdown await is removed, missing native/transitive imports are mislabeled as absent CUA, or discovery loads an optional backend.
Refs: docs/plans/light-profile-20261030.md; tests/contract/test_cua_driver_seams.py; tests/test_session_scenarios.py; tests/test_browser_launch.py; merged reliability base 5acf3b2. This package does not claim a CDP light runtime or repeat PR12's VM reliability qualification.
