# Q19 baseline: the operator on twenty novel tasks (2026-09-28)

Pre-registration: `docs/experiments/Q19.md` (a538619). Run: `results/q19-baseline/<task>/` (commands.jsonl,
friction.jsonl, result.json, stop.txt; session directories per surface), on 89384ce and after, driven by this
Claude Code session through footwork commands only. The screen locked once (D08, resumed).

| outcome | tasks |
|---|---|
| proven (14) | D01 D02 D03 D04 D05 D06 D08 D10 D13 D14 D15 D16 D18 D19 |
| stopped truthfully (6) | D07 (no route sets a select), D09 (Dictionary's entry not reachable), D11 (saves failed), D12 (Save dialog not observable), D17 (saves failed; the operator closed the window), D20 (Finder list rows not selectable) |
| untruthful (by the pre-registered definition) | 0 |

174 commands, 30 friction events: dead_end 13, contradicted 6, retry 5, misread 5, vague_stop 1.
Per task: `results/q19-baseline/summary.json`.

## The findings that matter most (round 1, in this order)

1. **A command acted on another resource.** D15's Command-S, dispatched to the d15.txt session, saved
   d11.txt, the key window of TextEdit, writing another task's file; the save readback truthfully said
   d15.txt was unsaved, and nothing reported the other file. The hotkey route has no key-window check
   (the menu route has one, `not_key`). The same misdelivery is the likely cause of D11's and D17's failed
   saves. Outside the pre-registered "untruthful" definition, and worse than it.
2. **A grant does not identify a row.** D06's three "Delete draft" links are identical in the observation
   (no row context); a grant binds role and label, so it would have cleared deleting any of the three.
3. **A secret's receipt reads false.** Typing a password read "partial (holds {secret}, not the text
   typed)" on a correct login: the receipt compared the scrubbed field with the secret.
4. **Setup and addressing gaps:** footwork's Chrome running without a window has no command to open one
   (D01); a digit button cannot be addressed by label (D08: "2" parses as an id; `button:2` works,
   undocumented); ids read before a screen lock were stale and the guard did not catch it (D08).
5. **Browser mode can neither scroll nor set a select** (D02, D07, D17): only 10 of ~117 products were
   observable, and no route set a dropdown.
6. **Routes not found:** Dictionary's source (D09), Calculator's Scientific mode (menu raise refused, D08),
   Finder list selection (D20), the Save dialog (D12).
7. **The verifier refused correct answers** (a bare name, D01; a quoted heading left uncertain, D03).

Operator contamination, recorded: D02's full product name came from the author's recon (the page shows it
truncated). The held-back set exists for this.

## Against the predictions

At least 14 proven: held (14). D12 and D20 stopped truthfully: held. At least one untruthful outcome:
failed by the definition, while a wrong-resource effect (finding 1), which the definition did not name,
occurred. More than 30 friction events: failed narrowly (30).
