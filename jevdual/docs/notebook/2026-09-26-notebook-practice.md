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

## U21 · update · 2026-09-26 14:04
Resolves: N1 = failed
Observed: `uv run python -m evals.notebook docs/notebook` and `git log -S` per entry, after package C closed: every one of the 15 resolved predictions (A1 to A4, B1 to B3, C1 to C7, D1) was first committed before the update that resolved it, and for C5, C6, C7 and D1 before the run or test itself (779e8f9, 410d83f, 7eddfff, 39d24c6). A had one failed prediction (A3) that widened the fix from two leak sites to four; C had four failed and one inconclusive, and the failures moved the work each time (C1 off navigation, C4 off a misplaced click, C6's wrong timing account recorded rather than rewritten); B's three all held.
Inferred: N1 fails as written, on B. B's predictions stated conformance to a specification (a failed judgment pauses, routes match, grants are exact), where a test already carries the prediction and a failure would have been a bug, not a wrong diagnosis. The practice paid where the cause was unknown: C found a cause (Chrome's breached-password warning) none of its first four predictions named, and the failed ones are what kept the search honest.
Changes: keep the notebook; narrow what needs a prediction. A diagnosis, a mechanism or an expected effect size gets one; conformance work whose tests state the expectation gets a summary only. README amended in the same commit.
Next: none for N1.
