# Three implementation plans synthesized from the five directions

Prepared October 28, 2026 against `main` at `5d494c6`. Five fresh-context reviewers each critiqued one of the [five directions](../README.md), checking that plan's source references ([critiques/](../critiques/)). Three further subagents then combined the strongest surviving ideas into the plans below. Each author was told to recheck any critique finding in source before relying on it, and several critique claims were corrected as a result (see each plan's corrections section). The parent rechecked the three headline defects (D1, D2, D5 in Plan A) against `session.py`, `native.py` and `completion.py`.

This packet is design documentation only. No runtime file changed, no prediction was committed, and no live application or model evaluation ran. Subagents ran only read-only unit tests.

## What the critiques changed

| Earlier plan | Main correction | What survived |
| --- | --- | --- |
| 1 Execution core | The capability journal is already generic (`BEGIN IMMEDIATE`, `flock`, tokens, `dispatching→unknown`), so a new store is unnecessary. Native append is not grant-gated, so it is the wrong first slice. | Grant reserved in the intent transaction, token replay for `do`, typed readback with a legacy reader, migration rules |
| 2 Source-to-note | A public page saved to a new `.txt` file needs no GUI, so it cannot test demand. Save readback compares the file with the window, not with the expected content. | Save as its own operation, a job manifest, two separate first-use trials, a failure-scenario list |
| 3 Verification SDK | History checks need Footwork's own journal. Answer support only checks that atoms are present. Most of the code is already stdlib-only. | One typed result record, kinds never convert, an install gate that can fail |
| 4 Operator console | The session log records no observations and no reliable delivery value. A local server is the largest new attack surface. A same-user agent can run `footwork grant` itself. | Four outcome labels taken from structured fields, a static `footwork report` page |
| 5 Evidence lab | Recount re-checks arithmetic, not grading. Schema-only conformance would pass a broken adapter. | Slot-state accounting with null for unknown, mutant-adapter conformance, packet manifest v2 and regrade |

## The three plans

| | [A. Durable operator core](A-durable-operator-core.md) | [B. Auditable workflow](B-auditable-workflow.md) | [C. Evidence contract](C-evidence-contract.md) |
| --- | --- | --- | --- |
| Question | Does every `footwork do` mutation get intent-before-dispatch, replay and typed evidence? | Can an installed host finish one job that truly needs a GUI, and can a developer audit it afterwards? | Do one record and one conformance suite separate correct adapters from broken ones? |
| Primary user | Agent host calling the CLI across shells | Host agent, plus the developer auditing it | Adapter and host integrators, investigators |
| Core move | Extend `capability/journal.py` with grant and reservation tables, and route session `do` through it | Signed-in portal balance appended to an existing TextEdit log and saved; static report | Record v1 built on `completion.Effect`; six mutant adapters; light `footwork-evidence` wheel |
| First PR | DOC1/DOC2 predictions plus strict-xfail tests reproducing D1 (grant spent, no `do` record) and D2 (post-press error logged as `refused` and counted as not sent) | AW1 prediction, then failing tests, then `save_readback` compares disk bytes with expected bytes | Slot ledger (`evals/slots.py`): every slot ends in exactly one state, unknown cost stays null |
| Milestones | 5 | 5 | 6 |
| Evidence of success | 7 interrupt boundaries (B1–B7) never repeat input. Legacy reader equal over 216 committed `session.jsonl` files. | Trial 1 ≥5/6, Trial 2 ≥2/3, zero wrongly certified effects, report beats raw logs by ≥10 points | Each mutant fails its check. Resolving install pulls no heavy dependencies. Regrade reproduces labels. |
| What it gives up | No new user-visible workflow; browser route deferred | General core migration; apps beyond TextEdit | Everyday execution; demand untested until after M5 |

The plans share building blocks but put them in a different order. A produces records that C would type and that B's report would display. B takes only A's journaled save and observation records. C owns the schema, so if A runs first its M4 readback records should emit C's envelope. Each plan names these touch points and says how it proceeds without the others.

## Small fixes that hold under every choice

These are small, falsifiable and needed by every plan. Each still needs its notebook prediction committed before the test that resolves it.

1. **D1 / D2 reproduction** (A M1). [Grant consumption](../../../../python/jevdual/session.py#L966) precedes dispatch, the [narrow `except`](../../../../python/jevdual/session.py#L1014) lets cancellation through before the [`do` record](../../../../python/jevdual/session.py#L1034) is written, and a post-press driver error becomes `refused`, which [completion counts as not sent](../../../../python/jevdual/completion.py#L37).
2. **Save readback against expected bytes** (A M5 = B M1). The current [check](../../../../python/jevdual/native.py#L1334) compares the file on disk with the window text.
3. **Unknown is null, not zero** (C M1). This touches the [paired defaults](../../../../evals/paired.py#L56) and the `TaskResult` cost fields.

## Recommendation

Land the three small fixes first, in the order above. Then choose **A** as the primary plan if Footwork is meant to be a dependable general capability. Its first PR is tests only, so it either reproduces the diagnosis or stops the plan. Choose **B** if the open question is whether anyone needs Footwork. Its authenticated-fixture job is the first design here that `curl` cannot solve. Choose **C** only if outside integrators or investigators are the intended audience, and run its demand gate before M6.

As with the five directions, take one primary plan through its first decision point before reconsidering. The October 9 [product direction](../../agent-superpowers-product-20261009.md) remains the recorded decision until the user selects otherwise.
