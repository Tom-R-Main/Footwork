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
