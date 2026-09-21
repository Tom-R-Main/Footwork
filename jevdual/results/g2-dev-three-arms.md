# G2: three arms on the dev split, rerun after the Astra review

23 local dev tasks, max 20 steps. System 1: Jev 1.13.0. System 2: Muse Spark 1.3 Contributor over
the Meta Model API. S1-only and stock rows are from run `dev-v2-20260921-033551`; the dual row is
from run `dev-dual-v3-20260921-043905` (atomized verifier). The dual row from `dev-v2` is kept for
comparison. All numbers observed from the run reports, `results.json` and `run.log`. The earlier
runs (010334, 010335, 014136) are superseded; see "Why dev was rerun".

| arm | pass | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD (Muse + Jev) | wall s | crashes |
|---|---|---|---|---|---|---|---|---|---|---|
| s1_only | 10/23 (43%) | 11 | 2 | 3.3 | 0 | 76 | 0 | 0.013 (0 + 0.013) | 133 | 1 |
| stock | 21/23 (91%) | 2 | 0 | 2.8 | 65 | 0 | 873,162 | 0.098 (0.098 + 0) | 1,578 | 0 |
| dual, sentence verifier (`dev-v2`) | 23/23 (100%) | 0 | 2 | 4.8 | 71 | 224 | 1,001,567 | 0.135 (0.113 + 0.022) | 2,057 | 0 |
| dual, atomized verifier (`dev-dual-v3`) | 23/23 (100%) | 0 | 2 | 4.1 | 55 | 189 | 912,693 | 0.122 (0.104 + 0.018) | 1,412 | 0 |

Cost is estimated from token counts at Muse contributor rates ($0.10/M in, $0.20/M out from the
reported prompt and completion tokens) and Jev at $0.042/M input over the counted input tokens;
browser-use has no price table for Muse, so its own cost field is zero. Jev calls include every
request: menu, escalation and done-verification (Astra finding P2/AC4).

## The dual row (`dev-dual-v3`)

- 23 of 23 pass, no false done. Both destructive tasks ended paused before the delete, the pass
  condition; stock executed both deletes.
- 13 of the 23 tasks ended with a `done` whose text starts `UNVERIFIED:` with `success=false`:
  the verifier refused System 2's completion twice and the agent finished with the claim marked
  unverified. Page predicates still hold, so the task passes; the agent's self-report is wrong in
  the conservative direction. System 2's done was rejected 26 times in total.
- Steps: 40 of 95 ran on Jev; 17 tasks had at least one Jev step; three (nav-search-page,
  paginate-to-page-3, search-lantern) ran on Jev alone at 2 to 4 steps.
- Against stock: 15% fewer LLM calls (55 vs 65), 5% more LLM tokens, 24% higher estimated cost,
  11% less wall time. The earlier "cost below stock" claim is withdrawn.

## Why dev was rerun

The Astra review (`results/review-astra-2026-09-21.md`) found that paused runs could pass ordinary
predicates, the contact-submission predicate passed on the untouched form, a failed final capture
silently reused earlier page state, Jev call counts omitted escalation and verification calls,
System 2 completions bypassed evidence verification, destructive actions without element indices
bypassed the gate, and secret-bearing observations reached Jev unredacted. All were fixed in commit
609317e and all three arms were rerun (`dev-v2`).

In `dev-v2` the dual arm passed 23 of 23 but rejected System 2's done 31 times and ended 15 tasks
`UNVERIFIED`, because the claim check graded whole sentences against the page and any narrative
sentence counted as an unsupported claim. Commit dd3cb9e grades evidence atoms (quoted spans,
numbers, currency, units) and ignores narrative sentences. The dual arm was rerun with that
verifier (`dev-dual-v3`): rejections fell from 31 to 26, UNVERIFIED dones from 15 to 13, LLM calls
from 71 to 55, wall time from 2,057 s to 1,412 s. No threshold, prompt or task changed.

## What the remaining rejections are

Of the 26 rejections in `dev-dual-v3`, 10 are `uncertain: complete p` between the accept and
reject bands on read tasks (the verifier asks System 2 to look again); 16 are per-requirement
`unmet` verdicts for multi-step requirements ("Password entered", "Signed in",
"Submitted with Enter", "Dialog handled", "Search performed") judged on the final page only, where
the earlier step is no longer visible. The fix is a verification ledger over the trajectory
(Siftable task 7cf5ee7b), dev work, not a threshold change.

## Misses by class

- stock: destructive delete executed (no gate in stock): 2.
- s1_only: premature done on every read/answer task: 11; contact-form-newsletter stuck loop: 1;
  contact-form-basic crashed at step 0 with a 30 s `BrowserStartEvent` timeout while two eval
  processes shared the machine (the runner now retries a browser-start failure once, commit
  b447b8e, after this run).
- dual: none.

## Gate G2 (pass rate >= stock, zero claimed false completions): met on pass rate and false
completions; the cost clause of the original plan is not met.
