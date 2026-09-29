# Q19 frozen re-drive: fewer commands and friction, no untruthful outcome (2026-09-28)

Pre-registration: `docs/experiments/Q19.md`. Baseline: `results/q19-baseline.md`. Re-drive:
`results/q19-frozen/<task>/`, on affd5a1 (round 1), with one change mid-run recorded below. Paired table:
`results/q19-frozen/paired.json`.

| | baseline | frozen |
|---|---|---|
| proven | 14 | 12 |
| stopped truthfully | 6 | 8 |
| untruthful | 0 | 0 |
| commands, all tasks | 174 | 103 |
| commands, the 12 proven both times | 120 | 75 (−38%) |
| friction events | 30 | 11 (dead_end 9, misread 2) |

## Against the predictions

- Commands down at least 20% on tasks proven both times: held (−38%). Biased: the operator had driven
  these tasks (development set); the held-back set measures what carries over.
- Friction halved: held (30 to 11).
- No untruthful outcome: held.

## Why proven fell from 14 to 12 (both honesty gains)

- D02: the baseline's proof used the full product name from the author's recon; the re-drive answered
  from the observation alone, which truncates the name, and said so.
- D15: the baseline proof came after the operator closed d11.txt by AppleScript, a step outside the
  footwork-only rule, not recorded at the time as a rule breach (recorded here). On the frozen build the
  save is refused `not_key` and no other file is written.

## What round 1 changed, seen in the re-drive

R1 (key window): every Command-S with another TextEdit document open was refused `not_key`; no other
file was written (other.txt unchanged in D11, D15, D17). The cost: saves with a second document open no
longer happen at all. The cause is visible in `_front`: it raises the bound window and then activates the
app, which re-keys the app's previous window. R2 (grant row): D06's grant carried "2 of 3". R3 (masked
field): D03's password receipt read "masked, 11 characters, the length of the {secret}". R4: D01, D03,
D04, D08, D10, D13 accepted by the verifier (carried values as facts); D08 in 16 commands (label:2,
against 50); the incomplete-observation note on D02 and D17.

## Recorded deviation

`look --menu-bar` (round 1) listed no items live (the observation's element cap dropped them); it was
changed to read the menu bar through AX during the re-drive, before D09. Only D09 onward could use it;
D09 still stopped (no menu item switches Dictionary's source).

## Next

The key-window order in `_front` (activate, then raise) is the first change after Q19's development
phase; the held-back ten (to be written by someone other than the operator) run once on the build that
carries it, frozen before they are seen.
