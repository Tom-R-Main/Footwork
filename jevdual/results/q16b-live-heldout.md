# Q16b result: not adopted by the rule; the one false completion is a stale oracle on both arms (2026-09-26)

Pre-registration: `docs/experiments/Q16b.md` (ef6d3eb). Run `results/q16b-live-heldout` on ef6d3eb, 24
tasks, once, both arms interleaved, alongside Q11b's runs. 48 rows, no error rows.

| arm | verified | predicate passes | false completions | no-fact refusals | UNVERIFIED | driver requests |
|---|---|---|---|---|---|---|
| guarded | 19 | 23 | 1 (`lhw-rust-year`) | 7 | 4 (2 no_evidence, 2 uncertain) | 106 |
| guarded_evidence | 21 | 22 | 1 (`lhw-rust-year`) | 3 | 1 (uncertain) | 95 |

## Against the rule

- Verified passes on `guarded_evidence` at least those on `guarded`: met (21 against 19).
- No-fact refusals no more than `guarded`'s: met (3 against 7).
- Zero false completions on `guarded_evidence`: **not met.** Not adopted, per the rule.

## The false completion

`lhw-rust-year` asks, using Wikipedia, for the year Rust first appeared; its predicate is
`answer_contains: 2015`. Both arms ended on the Rust article and answered 2012, quoting the infobox,
"First appeared: January 20, 2012", and the verifier on both arms accepted with that claim found on the
page. The article states 2012 today; 2015 is Rust 1.0. The predicate is stale, and the run is a false
completion only by it. The strict check did not cause it: the default check accepted the same answer.

The heldout is never debugged, and changing its ground truth is the owner's decision, not the
experimenter's. What the rule's author intended the condition to catch (the looser atoms letting an
unsupported answer through) did not happen in this run: every accepted claim on either arm was found on
the page.

## Decision

Not adopted as the default, per the pre-registered rule. Open for the owner: correct
`lhw-rust-year`'s predicate to the page's current answer (or retire the task as drifting), after which
this run's rows re-grade without rerunning; under a corrected predicate all three conditions hold.
