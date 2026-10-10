# Next work, from the 2026-09-26 status audit

Written 2026-09-26 at `e5fb462`. Sources: the status audit (`results/status-audit-20260926/`), the
Q11 and Q12 results, `docs/plans/legible-harness.md`, and the Legible Loop v6 draft, whose rule
statuses this work changes.

**Milestone:** the same command stays on the same resource, executes only its approved effect,
preserves the person's data, and returns evidence that cannot overstate what happened. Nothing paid
runs until packages A to C hold; after that, measurement answers whether the repaired contract
reduces work.

Every package opens with a notebook file of predictions (`docs/notebook/`), committed before the
tests that resolve them, and closes with a summary and `uv run python -m evals.notebook docs/notebook`.

## Order

| # | Package | Closes | Paid runs | exf |
|---|---|---|---|---|
| 0 | Documentation reconciliation | claims that outrun the evidence | none | 9ed3f95b |
| A | Session identity and truthful evidence | v6 L2, L5 operator cells, secrets row | none | 8d7525ce |
| B | Authorization parity | v6 L4, both surfaces | none | 9c409f70; part of b3b29084 |
| C | Trusted input after navigation | the route L3 requires | none | 9b9916a6 |
| D | Action-specific receipts, then Q12b | L2's burden claim, L3 | about $2.50 | b3b29084 |
| E | Verifier evidence and recovery ownership | L6 blind spots; the S1 question | one Q, to be sized | d270bf73 |
| F | Q11b, the narrow declaration | L1 | about $3 | fce6dd93 |
| G | Cross-surface pilot, then Q13 | L9 | to be sized | 49ace2c6 |

Q14 (the paired comparison of the browser through the accessibility tree and through DevTools) waits
until after G. The Cua browser route exists; the experiment does not.

## 0. Documentation reconciliation (half a day, now)

Every item is an audit finding about a claim, not about code.

- README: Q12 is finished and not adopted as a burden reduction; Q9e did remeasure repaired
  delegation (36 verified against 41 guarded); the blanket "zero false completions on every split and
  run" narrows to "on the predicates of Q11 and Q12", since `li-add-then-delete-authorized` in
  `q8-q9e-live-dev-20260922-162350` was claimed done with its predicate failed; "calibration
  transfers" becomes the Q10b write-up's ranking result.
- `footwork run`: its default enables System 1 and escalates, which the experiments call reactive
  dual. Either rename the default or add `--guarded` and make it the default; the CLI and README use
  the research names.
- Q12 result and `evals.burden`: "53 tasks with checkpoints" becomes "53 tasks with some progress in
  both arms (19 of 59 declare checkpoints; 6 excluded for zero progress)", and `evals.burden` prints
  that population and the zero-progress counts itself (the first piece of P7).
- `legible-harness.md`: conformance cells updated to match the audit; P6's browser route marked
  built and Q14 marked not run; P1 (Q12) marked complete, with exf b642f4ab closed.

Done when: every changed sentence cites a results directory, and the README has no claim the audit
contradicts.

## A. Session identity and truthful evidence

Predictions A1 to A4 are written (`docs/notebook/2026-09-26-a-session-evidence.md`).

- A1: persist the bound browser target and tab; refuse when it is gone.
- A2: a refused receipt is never upgraded; `type` confirms on equality with the intended value,
  `append` on the before value plus the insertion, bound to the same field.
- A3: secret classification travels with the field through receipts, rendering, the session log and
  model inputs.
- A4: replacing a non-empty document is a replacement at any length.

Done when: each audit probe in `probes.py` has a failing-then-passing CLI scenario, the probes script
reports the corrected behaviour, and the scenario suite and ruff are green. A browser-mode scenario
needs a fake browser driver fixture; build it once here, since B and D reuse it.

## B. Authorization parity

- The browser path's failed destructive judgment becomes a pause, with a test that raises in the
  judgment and asserts nothing dispatches (the half of P2 that needs no live run).
- A route-parity table test: the same semantic action (submit, delete, replace, confirm a default
  button) through click, key, Enter, menu, hotkey and text routes, on both surfaces, gets the same
  decision. Where a route cannot be judged semantically, it pauses.
- Grants bind to an operation and a resource rather than a label substring. Design first in a
  prediction entry, since this changes `--authorize` for the operator.

Done when: the parity table passes on both surfaces, an unavailable or malformed judgment dispatches
nothing anywhere, and a grant for one action cannot clear a different action whose label shares a
substring.

## C. Trusted input after navigation

The execution blocker behind Q11's and Q12's saucedemo losses. Start from
`scripts/diag_trusted_input.py`.

- Build a deterministic local fixture: a page that navigates on click and a button on the next page
  that counts arriving events.
- Predict the cause before touching it (session bookkeeping is the audit's leading guess, not an
  established cause); keep the alternatives in the entry.
- Fix, then prove exactly-once delivery across fresh browser sessions, and run the targeted
  authorized and unauthorized saucedemo tasks once each on the frozen fix as a check, not a
  measurement.

Done when: the fixture shows input arriving exactly once after navigation in repeated fresh sessions,
with no duplicated events.

Amended 2026-09-26 (notebook U14): the fixture never showed the fault, so passing it proves nothing.
Done when instead: the saucedemo tasks pass inside the full agent loop with every click delivered
exactly once, or the loss is caught there with its dispatch and session state recorded, fixed, and
turned into a test that fails without the fix.

## D. Receipts that name the effect, then Q12b

- Click receipts on a page that did not navigate name what changed: scroll position, focus, an
  expanded section, a delayed navigation. Dispatch status and postcondition are separate fields.
- Pre-register Q12b: receipts delivered against recorded-only, on the repaired input path from C,
  with the same primary (requests per unit of progress, its population named), all-task verified
  completion, zero-progress counts and the Q12 guardrails. An input fix's gain is not credited to
  receipts.

Done when: Q12b is run and decided under its rule. If requests per unit of progress fall with a route
available, v6's L2 gains a burden claim and L3 is confirmed; if not, receipts stay an honesty measure.

## E. Verifier evidence and recovery ownership

Ahead of Q11b because the record shows correct or nearly correct work ending UNVERIFIED for missing
evidence, which a declaration cannot fix and a lower threshold would hide.

- Oracle probes for save, read-back and absence (the Finder Move to Trash case at 0.70), with typed
  evidence rather than page text; insufficient evidence is its own outcome.
- A pre-registered question on recovery ownership: System 1 finishes only mechanical actions whose
  target, arguments, permission and expected effect are fixed; System 2 keeps repair until a named
  progress condition holds. Primary: cost and latency per correctly completed, authorized task, not
  System 2 call counts (Q10b: 44 calls against 130, 29% more cost).

## F. Q11b

As already planned: the requirements list only, plus one sentence that the done text is checked
against the page. Prediction: the implied-page gain outside saucedemo stays and the narrated refusals
go. Runs after C, so saucedemo no longer decides the result.

## G. Cross-surface pilot, then Q13

One browser-to-TextEdit transfer with typed data provenance and an exact saved-file oracle, then the
five-task Q13 study. Only once A and B hold, since a handoff is where identity and authority are
lost.

## In parallel, the person's work

- The 40-row human audit sheets (web, Q10, Q10b) are still blank; the 12 recorded Q10b judgments count
  and are a targeted sample, not a population estimate (exf dcd70da2).
- The Legible Loop: after each package, update v6's statuses from its notebook summary. The manifest
  in v6 section 5 is this plan's "Closes" column.

## Checkpoint

After C closes, score N1 (`docs/notebook/2026-09-26-notebook-practice.md`): did each package produce
a failed or revised prediction that changed the work, and was every prediction committed before its
test? Keep, change or drop the notebook on that answer.

## Status, 2026-09-26 (end of day)

| # | Package | State | Evidence |
|---|---|---|---|
| C | Trusted input | closed | Chrome's breached-password warning dropped every post-login click; quiet profile; S4 |
| D | Receipts, Q12b | closed | delivery field; Q12b H0(c), receipts not delivered by default; S6 |
| E | Verifier evidence, recovery | measured | Q16 (no-fact refusals 62 to 20, primary interval includes 0), Q16b (not adopted by its rule; stale heldout oracle, owner's call), Q17 H0(b) |
| F | Q11b | closed | H0(b), not adopted |
| G | Cross-surface pilot | pilot closed | G3 held (transfer with provenance, exact saved line); G5 held (native save readback: 12 of 12 accepted, Q17 0 of 6); Q13 needs five oracles first |
