# Challenge cases for the completion and recovery candidate: a brief for their author

For Codex or the owner. The implementer (the Claude Code session that built M1 to M4) must not see the
cases before they are run. Write them on a branch the implementer does not read, as for Q19.

## What is under test

The frozen candidate, tag `m-candidate-1` (305b29b). Three behaviours:

1. **Completion from effect evidence (M1/M2)**, opt-in with `FOOTWORK_COMPLETION=effect_evidence`
   (`python/jevdual/completion.py`, `verify.py`, `session.py:cmd_done`). A done that is not an answer is
   accepted only with this run's evidence for the effect the task names; a duplicated effect blocks;
   claimed values may be supported by the run's evidence as well as the page.
2. **Repeat protection (U54)**, always on in `footwork do`: loading a recorded submission's result
   address again, or pressing the control that made it, pauses before dispatch.
3. **Bounded recovery (M3/M4)**, opt-in in `jevdual.crossloop` (`recovery=True`, `python/jevdual/progress.py`).

The implementer's own cases and their results: `results/m2-offline-20260929.json`, `results/m3-dev/`,
`results/m4-dev/`; the notebook `docs/notebook/2026-09-29-model-completion.md` records what they found.

## Two sets, two purposes

- **Challenge set** (about 20 offline cases and 6 live tasks): run once on `m-candidate-1` before any fix.
  Its failures become development cases; the implementer may then read and debug against it.
- **Adoption set** (a separate, similar number): sealed until a later candidate is frozen; run once;
  never debugged. A behaviour becomes the default only if it holds on this set.

## What to cover (each negative with a positive counterpart)

- **Benign query navigation** read as a submission: a search, a filter, pagination, a product link.
- **Reordered query parameters**: the same submission's result address with its fields in another order.
- **Different origins sharing a path**: `/done.html?id=2` on two hosts.
- **Identical control labels**: two "Submit" buttons for different forms; a second, different submission
  through a same-named control that should not be blocked.
- **POST forms**: a submission whose result address carries no fields.
- **Two documents with the same filename** in different folders.
- **Stale field values**: a field read back, then changed or navigated away from, before the done.
- **Negated instructions**: "do not submit", "leave X unchanged", where acting would be wrong.
- **Legitimate repeated operations**: "sign up two people", "add three rows", which must not be blocked.
- **Generic success pages**, **wrong resource**, **altered destination**, **preserved neighbour**,
  **incomplete observation** (an answer drawn from a truncated list).
- **Recovery**: an unavailable task in a large site (wandering must end); a task that legitimately needs
  several intermediate pages (recovery must not end it); a native sheet or dialog trap.

## Formats

**Offline completion cases**: one JSON file per case under `evals/challenge/<set>/`, run by
`uv run python scripts/challenge_offline.py evals/challenge/<set>` (three verifier replays per case):

```json
{
  "id": "C07-reordered-query",
  "category": "reordered query parameters",
  "expect": "accept",
  "rationale": "one submission is recorded, so the done is right; reloading it with the fields reordered would repeat it",
  "task": "Submit one cutting request with reference Poster H08 and quantity 318.",
  "requirements": [],
  "answer_expected": false,
  "answer": "Scratch request recorded",
  "page": {"url": "http://127.0.0.1:8767/done.html", "title": "Recorded", "text": "Scratch request recorded", "candidates": []},
  "mode": "browser",
  "records": [ { "t": 1.0, "step": 1, "kind": "receipt", "action": {"op": "click", "target_label": "Submit"},
                 "effect": "confirmed", "evidence": "navigated to /done.html?reference=Poster+H08&quantity=318; 0 elements added" } ],
  "carries": {},
  "memory": ["step 1: click(Submit) -> confirmed"],
  "context": [],
  "repeat_probe": {"op": "navigate", "url": "http://127.0.0.1:8767/done.html?quantity=318&reference=Poster+H08", "expect": "pause"}
}
```

`records` use the shapes `session.jsonl` writes (see any `results/q19-heldout-*/*/*/session.jsonl`);
`context` is a list of other surfaces, each `{records, carries, memory}`. `repeat_probe` (optional)
checks the repeat rule directly: `expect` is `pause` or `allow`. `expect` at the top is the done's
verdict: `accept` or `refuse`. (This example, run on `m-candidate-1`, already shows one gap the review
predicted: the reordered reload is allowed. It is the format's example, not a sealed case.)

**Live tasks**: `evals/tasks/<set>.yaml` in the format of `evals/tasks/m3-dev.yaml` (fixtures under
`evals/fixtures/site/`), with oracles and a test that each oracle tells a correct end state from a wrong
one, as `tests/test_q19.py` does.

## Rules

No real accounts, people or non-scratch files; nothing that syncs or sends. Give each case a one-line
rationale. Do not tune a case against the candidate before handing it over.
