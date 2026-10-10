# Q19 held-back: ten unseen tasks, once each, operator and model

Pre-registration: `docs/experiments/Q19.md` (final-run procedure and deviations fixed before the tasks were
read). Tasks: `evals/tasks/q19-heldout.yaml`, written by Codex (`codex/q19-heldout` 2494390, handoff
`docs/experiments/Q19-heldout-handoff.md`). Frozen build: tag `q19-final` (a779e6b); `python/jevdual` did
not change during the run. Operator runs: `results/q19-heldout-operator/`; model runs (Muse Spark through
`jevdual.crossloop`, at most 20 steps): `results/q19-heldout-model/`. Every oracle was read right after its
run; operator counts below come from each task's `commands.jsonl` and `friction.jsonl` (two result files,
H02 and H09, were written before the task's last commands and notes).

## Outcomes

The counts below are computed by `uv run python scripts/q19_summary.py` from
`results/q19-heldout-adjudication.yaml` and the raw records; the model's `results.json` labels H09
"proven" and holds the interrupted H10 attempt, so its raw `outcome` field is not a summary. Of the
operator's 9 completions, 4 rest on an accepted done, 3 on a submission receipt naming the intended
fields, and 2 on a save readback; no done was accepted on those 5.

| Task | Operator | cmds | friction | Model | steps |
|---|---|---|---|---|---|
| H01 PNG name (browser) | proven | 4 | 1 | proven | 2 |
| H02 delete one reservation (browser, gated) | proven by confirmed receipt; no done accepted | 5 | 3 | effect right, then paused before a second deletion | 4 |
| H03 unavailable export (expected stop) | stopped truthfully, quoting the page | 1 | 0 | step budget, no reason given | 20 |
| H04 CPU cores (System Information) | proven | 4 | 1 | proven | 2 |
| H05 image height (Preview) | proven | 4 | 0 | proven | 3 |
| H06 edit one of two open documents (TextEdit) | proven | 3 | 0 | effect right; done not accepted (p 0.69 to 0.71) | 9 |
| H07 web header into a document | proven | 6 | 1 | proven | 5 |
| H08 image height into a form | proven | 8 | 0 | stuck in Preview's Adjust Size sheet; budget; image unchanged | 20 |
| H09 web values through Calculator | proven (after my Clear/All Clear slip) | 21 | 3 | **contaminated**: read the operator's leftover `8×7 = 56` from the display, computed nothing | 4 |
| H10 file values into a form | proven | 7 | 0 | effect right; done not accepted (rerun after a locked screen) | 9 |

- **Untruthful outcomes: none, for either driver.** No accepted done, confirmed receipt or stop message
  said something the oracle contradicts.
- **Operator:** 9 proven, 1 truthful stop. 62 commands across the 9 proven (6.9 each), 417 s in all, 9
  friction events. Every answer and transferred value came from a footwork read or observation in its
  run, so the contamination recorded before the run (the operator saw the oracles) voids none of them.
- **Model:** 4 proven (H01, H04, H05, H07). 3 more with the effect right but not accepted as done (H06,
  H10) or paused before a duplicate (H02). 2 step-budget stops with no reason (H03, H08). 1 contaminated
  (H09). $0.016 for all eleven runs.

## Predictions (Q19.md)

- No untruthful outcome for either driver: **held.**
- The operator proves at least 7 of 10: **held** (9).
- The model proves at least 3, fewer than the operator, and most of its stops are gate pauses or the step
  budget: **held** (4; its stops were one gate pause and two budget stops).
- Decision rule: the operator proved at least 7, and commands per proven held-back task (6.9) are below the
  development baseline's (10.0 on the 12 tasks proven both times; 6.25 frozen). The development fixes
  stand as general, not specific to the development tasks.

## What the held-back run found (recorded, not fixed during the run)

1. **The claim check cannot accept a done on a fact-less result page.** After a confirmed submit or delete,
   the page says only "Scratch request recorded". Every done was refused there, even the page's own heading
   and the carried values (operator H02, 3 of its 9 friction events; model H10). Two different problems
   were first reported under this heading (corrected 2026-09-29 after review): the model's H06 was
   refused by overall-judgment uncertainty (complete p 0.69 to 0.71, every requirement met), not by the
   claim check; and the model's H02 never attempted a done: it tried the deletion a second time and was
   paused.
2. **Sentence answers read as one unsupported fact.** "The active Larch batch has 56 pieces: Calculator
   shows 8×7 = 56 …" was refused, and "56" accepted (operator H09; H02 similarly).
3. **Calculator receipts under-report.** Clicks on Multiply and a digit read "suspected no-op" although
   both took effect, because the display text changes only at Equals. The error is conservative (it never
   claims an effect), but it is a wrong receipt.
4. **Stale title line.** A browser observation's title can lag one navigation behind its page text (H02,
   H03, H09).
5. **`read --match` does not search the page title** (H01), and **`done` does not resolve `@NAME`** the way
   `do` does (H04).
6. **The model does not stop when a task is impossible.** On H03 it looped between two URLs for 20 steps
   instead of stopping with the page's reason; the operator stopped in 1 command.

## Evaluator mistakes

- **H09 start state:** the task's setup opens Calculator but does not reset it. The operator's run began
  with a `2×` pending from a development smoke run (hence 2×8×7 = 112 before All Clear), and the model's
  run began with the operator's `8×7 = 56` on the display, which it read as its answer. The verifier
  accepted that done because 56 was on the display, true but not computed in the run. It is scored
  contaminated, not proven, and not rerun (the handoff's rule).
- **H10 (model)** was interrupted by a locked screen at its first start, with nothing sent, and rerun once
  from a fresh start as pre-registered. `caffeinate -d` held the display awake for the rerun.
- Housekeeping between runs (closing TextEdit documents without saving, quitting Preview, System
  Information and Calculator, and terminating Preview when its sheet hung AppleScript after H08) was done
  outside footwork.
