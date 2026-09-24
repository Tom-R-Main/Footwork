# Q10b result: corrected build, corrected tasks, two stage-2 runs (2026-09-24)

Pre-registration: the Q10b amendment in `docs/experiments/Q10.md`. Stage 1 (verifier on oracle end
states): `results/q10b-verifier-probe-20260924*`. Stage 2 runs: `results/q10b-native-dev-20260924`
(run 1, build e5f7ea1) and `results/q10b-native-dev-20260924-r2` (run 2, build ddd2dd8: the verifier's
trajectory lines carry labels, chords and effects instead of bare indices; nothing else changed). Six
tasks (the pure-read task is held out, stage 1), three arms, three repeats, Calculator in Basic mode,
fresh app instance per run. Labels: `results/annotation/q10b/` (run 1, protocol 2, kappa 0.93).

## Headline

Verified completions (predicate passed and done accepted) of 18 per arm:

| arm | run 1 | run 2 | predicate passed (run 2) | false completions | pauses | est. cost (run 2) | LLM calls | Jev calls |
|---|---|---|---|---|---|---|---|---|
| s1_only | 9 | 9 | 12 | 0 | 0 | $0.014 | 0 | 105 |
| dual | 12 | 13 | 16 | 0 | 0 | $0.032 | 44 | 170 |
| guarded | 15 | 15 | 18 | 0 | 1 (run 1) | $0.025 | 130 | 21 |

Paired by task, repeats averaged (run 2): Δ passed (dual − guarded) −0.11 per task [−0.33, 0.00];
Δ passed (dual − s1_only) +0.22 [0.00, +0.56]. Q10 for comparison: guarded 11, dual 6, s1_only 6.

Verified completions per task, run 2 (run 1 in brackets where different):

| task | s1_only | dual | guarded |
|---|---|---|---|
| calc-multiply | 3 | 3 | 3 |
| calc-subtract | 3 | 3 | 3 |
| calc-percent | 0 | 1 (3) | 3 |
| calc-read-result (answer) | 0 | 3 (0) | 3 |
| textedit-type-sentence | 3 | 3 | 3 |
| textedit-append-line | 0 | 0 | 0 |

## Against the amendment's predictions

- **"If the Q10 deficit was verifier and task artefacts, `dual` ≥ `guarded` within one task."** Met in
  both runs: the gap is 3 (one task's three repeats) in run 1 and 2 in run 2, and the interval on the
  paired difference touches zero. calc-subtract went from 0 verified on every arm to 3 on every arm
  once its requirement named the number; calc-read-result went from 0 to 3 under `dual` once the
  trajectory carried labels (the same display was refused at complete 0.65 with `click(8)` lines and
  accepted at 0.94 with `click(9) -> unverifiable` lines, exactly the Q10 asymmetry).
- **"If it was System 1's confident wrong sequences, the deficit stays on calc-percent."** Also met:
  the residual gap is calc-percent, where System 1 enters 1, 5, Percent with target confidence 0.35 to
  0.71, falls to `retry_alternate`, System 2 clears, and System 1 repeats (two of three runs exhausted
  the budget in run 2; all three completed in run 1, so the loop is not deterministic). `guarded`
  finishes it in 10 steps every time. The repeated-sequence arbiter rule is the next change, measured
  on its own.
- **Guardrails.** No false completions in either run; one boundary pause in run 1 (System 2 proposed a
  `type` that would have replaced the document's content; the boundary named the rule); content
  preserved on every append-line run (exact-file predicate 18 of 18). The run-1 `dual` append rows
  lost their window three times: after a correct `append`, System 1 clicked an unlabelled toolbar
  "button" at target confidence 0.55 to 0.64, which closed the document. Both label passes mark those
  six clicks wrong; at the 0.60 operating point four of the six would have escalated.
- **append-line verified by nobody.** The file predicate passed on all 18 runs (the append is right
  and autosave writes the file during the run), but "The document was saved" was never accepted:
  the foreground hotkey comes back `unverifiable` (no readback) and the verifier holds the requirement
  unmet at 0.62 to 0.79. That is the honest reading of the evidence; the fix is a save with readback
  (a window-title or "Edited" indicator in the end state, or the file's mtime as an observation),
  not a lower threshold.

## Calibration, protocol 2 (run 1 rows, 246 System 1 decisions)

Two blinded passes over packets with window text, prior effects and no scores: agreement 0.988,
kappa 0.927 (Q10's packets with scores and no display: 0.742). Three disagreements, all on whether
an All Clear after a Clear is a right recovery. Agreed labels: 222 right, 21 wrong. Wrong rows:
15 calc-percent keys, 6 append-line clicks on the unlabelled button. Argument labels on the 12
typed rows: all right (System 1 chose `append`, not `type`, on the append task in every run).
Completion labels on the 30 done rows: all supported.

| rows | signal | AUROC (wrong step) | 95% CI |
|---|---|---|---|
| all S1 decisions (243) | operation confidence | 0.915 | [0.866, 0.955] |
| all S1 decisions (243) | target confidence | 0.869 | [0.813, 0.917] |
| acted only (217) | operation confidence | 0.944 | [0.896, 0.981] |
| acted only (217) | target confidence | 0.884 | [0.828, 0.933] |

With 21 wrong rows in two tasks these are ranking results with wide intervals, not a calibration
claim; a reliability analysis needs more failure modes than a percent key and one toolbar button.

## Decision

Per the amendment: the Q10 deficit was mostly artefacts (task wording, an overwrite the predicate
missed, verifier evidence without labels), and after their correction `dual` sits within one task of
`guarded` on verified completions at roughly a third of its LLM calls but higher total cost (Jev calls
per step). The native backend stays experimental. Next, in order: (1) a save with readback and an
end-state field the verifier can see; (2) the repeated-sequence arbiter rule, measured alone on
calc-percent; (3) identifier hints for unlabelled controls in the menu builder; (4) tranche 2, the
consent classes, pre-registered as an amendment, since the boundary now covers every route.
