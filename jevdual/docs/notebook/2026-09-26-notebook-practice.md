# The notebook itself

The practice is a harness change for whoever does the engineering, so it gets a prediction too.

## N1 · prediction · 2026-09-26 16:10
Question: does writing predictions before tests surface wrong diagnoses that would otherwise go unrecorded?
Hypothesis: across packages A to C, at least one prediction per package fails or is revised, and each failure names a change the package then made (a wider fix, a different cause, a rule restated).
Alternatives: predictions get written after the test, or only for safe cases, and everything holds.
Test: at each package summary, run `uv run python -m evals.notebook docs/notebook` and compare each prediction's commit time with the commit of the test that resolved it.
Predicts: one or more failed or revised predictions in each of A, B and C, each linked to a change; every prediction committed no later than the test that resolves it.
Against: A to C close with every prediction held, or predictions committed in the same commit as their resolving test; either way the practice is not doing its job and gets changed or dropped.
Refs: docs/notebook/README.md
