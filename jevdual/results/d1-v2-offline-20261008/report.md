# D1 version 2 offline preflight

94 host tests passed across test_decisions.py, test_d1_compare.py and test_notebook.py; scoped
Ruff passed. Tests cover forced single-option provenance, native receipt preservation, pooled
client lifecycle, exact versus coarse abstention, and actual admitted alternate-target scoring.
No runtime factories or admission thresholds changed. These are local checks, not model evidence.

preflight.json shows the logical projection hash unchanged from version 1. Wire question counts
exclude 17 forced singleton heads across action cases; candidate maximum body is 9,275 bytes.
Full unknown-usage upper exceeds $5, so the runner may stop early. Carry all prior/diagnostic
usage and uncertain-cost reservations into this version's same total budget.
