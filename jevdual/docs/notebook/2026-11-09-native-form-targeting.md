# Native browser form targeting

## NFT1 · prediction · 2026-11-09 21:07
Question: can the reported native Chrome form limitations be reproduced and repaired without weakening duplicate-target refusal?
Hypothesis: native projection drops usable placeholder and ancestor context before identity matching, and ordered truncation hides active popup controls; session targeting failures return before an audit record is written.
Test: add public CLI simulated-Mac scenarios for repeated row actions, distinct empty placeholders, dynamic row changes, late popup options and early targeting refusals. Run the counterexamples before implementation, then affected regression suites and available offline checks.
Predicts: baseline scenarios fail to expose or address qualified controls and omit nondispatch history; preserving independently supplied context and prioritizing popup controls enables qualified actions while stale, ambiguous and changed-context selections refuse before dispatch. Refusal records retain selector and observation evidence without typed text or secrets.
Against: the fixture cannot supply distinct semantics from the pinned driver contract, qualification silently targets another row after mutation, a placeholder becomes entered value, or a previously safe distinct control stops working. Projection tests alone cannot establish live Chrome behavior.
Refs: user-provided Namecheap limitation report dated2026-11-09; tests/test_session_scenarios.py; python/jevdual/native.py; python/jevdual/session.py; docs/notebook/2026-11-01-duplicate-control-identity.md

## NFTU1 · update · 2026-11-09 21:14
Resolves: NFT1 = held
Observed: the native worker reproduced three public CLI failures before its repair: row sections missing, late popup option absent and empty placeholder fields losing identity. The initial native repair passed those cases. The session worker reproduced11 failing public CLI cases before its repair, including absent nondispatch records and changed-role/section targets that still dispatched. Independent review identified additional boundaries in renumbered fields, grant identity, final placeholder matching and popup/menu-bar classification.
Inferred: the reported failures arise at multiple boundaries; adding display labels alone cannot establish safe targeting or trustworthy receipts. The pinned driver collapses groups, so some context requires a bounded direct AX read rather than parsing unstructured page text.
Changes: retain independently read placeholders before pruning; use explicit ancestor names, prioritize popup choices, persist a configurable candidate budget and record early targeting refusals. Extend regression checks to the review findings before closing.
Next: complete dynamic-row, grant and readback checks; capture integrated test results. No live DNS mutation or native qualification is part of this package.
Refs: tests/test_session_scenarios.py native_form scenarios; tests/test_session_targeting_audit.py; tests/test_ax_semantics.py; prediction f720c51

## NFTU2 · update · 2026-11-09 21:24
Observed: review counterexamples reproduced input after a select-all recapture changed the target, false uniqueness after a partial placeholder read, and a truncated-label peer escaping the supplemental scope group. Native repairs passed245 affected tests. Session receipt/grant follow-ups passed205 affected tests; a grant fixture first lacked an authorization trigger and was corrected before verifying the roster-signature counterexample. The first full offline suite passed2917 tests with one failure for the existing installed CUA version mismatch; changed-file lint passed while repository lint found nine unchanged IR1-script issues.
Changes: rematch after selection before insertion, preserve ambiguity for incomplete semantic peer groups, and require qualified field identity and form-roster agreement for readbacks and exact grants. Selection already delivered is retained as dispatched evidence even when typing is withheld.
Next: freeze the follow-up repair and rerun the full offline suite; document environment and live-platform limits separately from fixture success.
Refs: output/native-form-targeting/receipt-roster-green.txt; output/native-form-targeting/grant-roster-red-corrected.txt; results/native-form-targeting-20261109/pytest-initial.txt; results/native-form-targeting-20261109/ruff.txt
