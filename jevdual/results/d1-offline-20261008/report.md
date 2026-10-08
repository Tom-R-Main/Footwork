# D1 offline preflight

Host checks on 2026-10-08 before any paid request: 76 tests passed across test_decisions.py,
test_d1_compare.py and test_notebook.py; scoped Ruff passed on the two implementation and two test
files. These are local contract, replay and accounting checks, not Decisions model validation.

preflight.json records all 106 prepared development projections, the projection hash, request body
sizes and conservative fan-out accounting. Full unknown-usage reservations exceed the $5 ceiling;
the live runner may stop early. No case action is dispatched. No dependency pins or runtime
backend factories changed. Actual account access and model performance remain unmeasured.
