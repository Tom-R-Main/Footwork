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

## V2 · prediction · 2026-09-27 15:42
Question: how often does the verifier accept a done that is false, and refuse one that is true, on claims built to separate them?
Hypothesis: the deterministic claim check binds no fact to its subject, so it accepts the adversarial cases whose facts are all somewhere on the page (a real price on the wrong product, a real value in the wrong field, a true fact for a different task, an unsupported qualification in narrative words); the Jev judgment catches some of them through the requirements; the strict check lowers false rejections without raising false acceptances.
Alternatives: the Jev judgment already rejects nearly all the adversarial cases, so the claim check's weakness is covered in practice; or the strict check accepts more false claims than it rescues true ones.
Test: `evals/claims_audit.py` over `evals/fixtures/claims_audit.yaml` (a fixed set of correct and incorrect dones on synthetic pages, labelled before scoring): the claim check alone in both modes, then the full `Verifier.verify` (Jev) in both modes.
Predicts: claim check alone: false acceptance at least half of the adversarial cases in both modes; strict false rejection below page's. Full verifier: false acceptance above zero; strict does not accept any case page rejects.
Against: full-verifier false acceptance zero in both modes (the Jev judgment covers the gap), or strict accepting an adversarial case that page rejects.
Refs: results/status-audit-20260927/README.md (step 2)

## U31 · update · 2026-09-27 15:44
Resolves: V2 = failed
Observed: `results/claims-audit-20260927` (18 labelled dones, 10 incorrect): claim check alone, `page`: false acceptance 2/10, false rejection 4/8; `page_and_fields`: 7/10 and 0/8. Full verifier (Jev plus claim check): false acceptance 0/10 in both modes; false rejection 6/8 (`page`) and 3/8 (strict). The strict verifier still refuses A4 (a filled form field: complete p=0.20), A7 (cheapest after sorting: uncertain, unmet 0.46) and A8 (a navigation task that asks no answer: "no fact found" with complete 0.96, unmet 0.04).
Inferred: the claim check binds no fact to its subject (the strict one alone accepts a real price on the wrong product, a value in the wrong field, a true fact for another task), as predicted; but the Jev judgment rejected every incorrect done here, so V2's Against held: in this set the requirement judgments carry the safety and the claim check mostly adds false rejections. `page` mode's apparent 2/10 is low for the wrong reason (it cannot find split prices, so it rejects correct and incorrect price answers alike). Two strict-mode refusals are verifier defects: the no-fact rule demotes a done on a task that asks for no answer (A8), and Jev's page text has no field values, so it cannot see a filled form (A4).
Next: V3.

## V3 · prediction · 2026-09-27 15:44
Question: do the two defects account for A4 and A8 without admitting any incorrect done?
Hypothesis: in strict mode, (1) apply the no-fact demotion only when the task asks for an answer, and (2) give Jev the non-secret field values beside the page text; A4 and A8 are then accepted and the ten incorrect dones stay rejected.
Alternatives: field values in Jev's view make it accept R2 (a value in the wrong field), or dropping the no-fact demotion lets R8 (the order not placed, a non-answer task) through.
Test: the same audit after the change.
Predicts: strict full verifier: false rejection at most 1/8 (A7 may remain), false acceptance 0/10.
Against: any incorrect done accepted by the strict verifier.

## U32 · update · 2026-09-27 15:46
Resolves: V3 = failed
Observed: `results/claims-audit-20260927b`, strict full verifier after the two changes: false acceptance 0/10, false rejection 2/8 (A4, A7); A8 now accepted; A4 moved from reject (complete 0.20) to uncertain (complete 0.42, max unmet 0.67). `page` mode unchanged (0/10, 6/8).
Inferred: the field values reached Jev, but A4's second requirement, "Form not submitted", is an absence the page alone cannot show and this synthetic case has no trajectory to show it; that is the verifier's known absence blind spot, not the field defect. The prediction's threshold failed (2 against at most 1); its safety half held (no incorrect done accepted).
Changes: kept both strict-mode changes (field values in Jev's view; the no-fact rule only when the task asks for an answer).
Next: adoption needs a fresh live measurement of the current strict check; the audit set is the offline gate any claim-check change runs first.

## V4 · prediction · 2026-09-28 02:18
Question: can the verifier accept a correct cross-surface done (Q13 task 1: 3 of 3 correct, 0 accepted) once it sees where the value came from, without accepting a tampered one?
Hypothesis: task 1 was refused because the verifier read the destination window alone ("The document's last line is the first book's price" unmet); with the other surfaces' step lines and the carries' sources on its trajectory (`footwork done --context-from`), it can see that the appended line is the value read from the first book.
Alternatives: (a) Jev ignores trajectory lines for a requirement about the current window, so nothing changes; (b) the extra context makes it accept a destination line that differs from the carried value.
Test: offline first, four verifier calls on synthetic windows: the correct destination with and without the cross-surface context, and a tampered destination (its last line £52.00, the carry £51.77) with the context; then Q13 task 1, three repeats, and tasks 2 and 3 once each as a check.
Predicts: offline: correct with context accepted, without context not accepted, tampered with context not accepted; live: task 1 accepted in at least 2 of 3, tasks 2 and 3 still accepted.
Against: the tampered case accepted, or task 1 still unaccepted in all three.

## U41 · update · 2026-09-28 02:20
Resolves: V4 = failed
Observed: `results/v4-offline-20260928.json`: correct destination without the other surface's context: verify (complete 0.53, max unmet 0.60); with it: verify (0.74, 0.46); tampered destination (last line £52.00, carried £51.77) with the same context: verify (0.78, 0.46).
Inferred: the context moves Jev's scores toward acceptance but not across, and it moves the tampered case exactly as far: Jev does not compare the carried value in the trajectory with the window's line. Context that could have made the correct case pass would have made the tampered one pass too; V4's alternative (b) is the real risk even though it did not fire. Loose context is the wrong evidence for this requirement.
Next: V5, a deterministic check the harness makes itself.

## V5 · prediction · 2026-09-28 02:20
Question: does a harness-computed check (the field that received a carried value holds it exactly as its last line) let the verifier accept the correct destination and refuse the tampered one?
Hypothesis: at `done`, for each carried value this session typed or appended, the harness compares the field's current value with the carried text and puts a typed line on the trajectory: "harness check: 'text area' holds @price = '£51.77' (read at books.toscrape.com) as its last line", or "does not hold ... its last line is '£52.00'". Jev reads a harness verdict, not a comparison it has to make.
Alternatives: Jev still does not weigh a trajectory line against the current window for "last line" requirements (a), or it accepts even with a "does not hold" line (b).
Test: `scripts/v4_offline.py` extended with the check line in each case (the correct case gets "holds", the tampered "does not hold"), then Q13 task 1 three times and tasks 2 and 3 once.
Predicts: offline: correct with the check accepted; tampered with its check not accepted; live: task 1 accepted in at least 2 of 3; tasks 2 and 3 still accepted.
Against: the tampered case accepted, or the correct case still not accepted offline.
