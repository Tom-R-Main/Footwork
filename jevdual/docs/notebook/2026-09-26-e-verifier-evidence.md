# Package E: verifier evidence and recovery ownership

Plan: `docs/plans/next-work.md` (E). Correct or nearly correct work ends UNVERIFIED for missing
evidence. Q12's rejection audit (`results/q12-live-dev-pooled/rejections-guarded.md`): 44 done
rejections for "no fact found on the page", every one in a run that later passed.

## V1 · prediction · 2026-09-26 13:49
Question: why does the claim check find no fact in done texts whose facts are true?
Hypothesis: the check reads the wrong things, not the driver. (1) After a first rejection the driver prefixes "UNVERIFIED:" and the colon rule takes the whole following clause as one atom, which no page contains, so the rejection feeds itself; (2) a parenthetical aside ("Alan Turing (verified in input value and screenshot)") is glued into the atom; (3) typed form values are not in the page's innerText, so "Customer name: Alan Turing" is unfindable on the very page that shows it in the field.
Alternatives: the done texts carry facts that are genuinely not on the final page (a price seen on an earlier page, a claim about a past action), which a better atom rule cannot rescue and only trajectory evidence could.
Test: `scripts/audit_no_fact.py` over Q12's traces (done texts where recorded); then a switchable claim check (status labels and asides stripped, clauses over six words narrative, non-secret field values in the evidence corpus) measured as its own arm, `guarded_evidence` against `guarded` (Q16).
Predicts: Q16 pooled: no-fact rejections on `guarded_evidence` at most half of `guarded`'s; verified passes up on the tasks where Q12 recorded no-fact rejections (`lh-form-fill-no-submit`, `ls-bike-light-price`, `li-key-press`, `ls-sort-cheapest`); no false completion on either arm.
Against: no-fact rejections fall by less than a third (the facts really are elsewhere), or `guarded_evidence` verifies a run whose predicate fails.
Refs: scripts/audit_no_fact.py (27 recorded no-fact done texts in Q12: all 27 start "UNVERIFIED:", 21 atoms carry an aside, 14 are clauses of more than six words)

## U20 · update · 2026-09-26 14:02
Observed: Q16 smoke (`results/q16-smoke-20260926`, three tasks, both arms, once): `lh-form-fill-no-submit` and `li-key-press` ended `done_claimed` with no refusal on `guarded_evidence` and UNVERIFIED (`no_evidence`) after three refusals on `guarded`; the recorded failing claims on `guarded` were field values ("Customer name: Alan Turing") and a clause after the quoted message's colon. `ls-bike-light-price` stayed UNVERIFIED on both: the claim "$9.99" was not found on the inventory page, and a reproduction shows the menu text reads "$ 29.99 ... $ 9.99" (saucedemo writes `$<!-- -->9.99`, two text nodes).
Inferred: a fourth mechanism, not in V1: prices split across text nodes. Every saucedemo price answer fails the exact check.
Changes: the strict check closes a space between a currency sign and a digit in the page and field text before matching (Python, before the matcher; the Rust matcher and its twin are unchanged). Amendment appended to Q16.md before run 1.
Next: Q16 runs 1 to 3 once Q12b's runs finish.

## U29 · update · 2026-09-26 17:51
Resolves: V1 = held
Observed: Q16 (`results/q16-live-dev.md`): no-fact refusals 62 on `guarded`, 20 on `guarded_evidence`; verified passes on V1's four tasks 4 of 12 against 12 of 12; no false completion on either arm.
Inferred: the no-fact refusals came from the check, as V1 said: most of them go when it reads labels, asides, form fields and split prices correctly. The all-task verified gain (+11 pooled) is short of its interval, because the rescued tasks are few among 59.
Next: Q16b on the heldout.
