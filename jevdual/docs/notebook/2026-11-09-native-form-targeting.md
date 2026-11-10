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
