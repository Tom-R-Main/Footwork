# Q16b erratum: `lhw-rust-year`'s oracle, regraded without rerunning (2026-09-27)

The original run, its rows and its decision (`results/q16b-live-heldout.md`: not adopted by the rule)
stand. This records a correction to one heldout oracle and what the same rows score under it.

**The defect.** `lhw-rust-year` asks, using Wikipedia, for the year Rust first appeared. Its predicate
was `answer_contains: 2015`. Wikipedia's infobox reads "First appeared: January 20, 2012"; 2015 is Rust
1.0 (the Rust 1.0 announcement, 2015-05-15). Both arms answered 2012 quoting the infobox, and the
claim check found the quote on the page on both arms. The secondary audit (`results/status-audit-20260927/`)
reached the same reading independently. Corrected in `evals/tasks/live-heldout.yaml` to `2012`, with
the old value in a dated comment.

**Regraded from the stored answers (no rerun):**

| arm | verified, original oracle | verified, corrected | false completions, corrected |
|---|---|---|---|
| guarded | 19 of 24 | 20 of 24 | 0 |
| guarded_evidence | 21 of 24 | 22 of 24 | 0 |

Under the corrected oracle all three of Q16b's adoption conditions hold.

**Why this does not adopt the strict check now.** The strict check measured in Q16 and Q16b is not the
current code: on 2026-09-27 it was changed to check facts inside parenthetical asides, after the audit
showed it could keep a sentence as supported while dropping a fact from the check. The heldout tasks
are also no longer unseen evidence. Adoption now needs (1) the offline adversarial evidence set
(false acceptance and false rejection measured separately), then (2) a fresh measurement of the current
check.
