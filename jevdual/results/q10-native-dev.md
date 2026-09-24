# Q10 result: native dev split, three arms, three repeats (2026-09-24)

Run dir: `results/q10-native-dev-20260924` (63 rows: 7 tasks × 3 arms × 3 repeats; the run crashed
once after 16 rows on a serialisation bug in the runner and was resumed with `--resume`, commit
98fddf0; no row was rerun or dropped). Pre-registration: `docs/experiments/Q10.md`. Oracles:
`results/native-oracle-20260924` (7/7). Build: 3fadd7e, 9163e79, c85647d, 5bd00cb.

## Headline

Counts, not percentages (n = 7 tasks, 21 rows per arm).

| arm | predicate passed | verified (passed and claimed done) | paused | false completions | LLM calls | Jev calls | est. cost USD |
|---|---|---|---|---|---|---|---|
| s1_only | 11 | 6 | 0 | 0 | 0 | 101 | 0.021 |
| dual | 12 | 6 | 0 | 0 | 79 | 271 | 0.065 |
| guarded | 17 | 11 | 0 | 0 | 192 | 114 | 0.052 |

Paired by task, repeats averaged (`evals.paired`, bootstrap 95% on the per-task difference):

| comparison | Δ passed per task | 95% CI | tasks better / worse |
|---|---|---|---|
| dual − guarded | −0.24 | [−0.67, +0.10] | 1 / 2 |
| dual − s1_only | +0.05 | [+0.00, +0.14] | 1 / 0 |

Verified completions per task (of 3 repeats):

| task | s1_only | dual | guarded |
|---|---|---|---|
| calc-multiply | 3 | 3 | 3 |
| calc-subtract | 0 | 0 | 0 |
| calc-percent | 0 | 0 | 2 |
| calc-read-result (answer) | 0 | 0 | 3 |
| textedit-type-sentence | 3 | 3 | 3 |
| textedit-append-and-save | 0 | 0 | 0 |
| textedit-read-word-count (answer) | 0 | 0 | 0 |

**On the primary metric H1 is not supported: `guarded` beats `dual` on verified completions
(11 vs 6) and `dual` adds nothing over `s1_only` (6 vs 6) while costing three times as much.**
Guardrails held: no false completions, no pauses (there are no consent tasks in tranche 1), no
crashes after the runner fix. Direction is consistent across repeats (every task's count is 0 or 3
except calc-percent guarded 2 of 3).

## Where the completions went, task by task

- **calc-subtract, all arms: predicate passes (175 on the display), every done refused.** The
  verifier sits at complete 0.68 to 0.74 with "The display shows 250 minus 75" unmet at 0.45 to
  0.47, band `verify`, on all nine runs. The requirement asks Jev to do the subtraction, which the
  verification prompt tells it not to do; "the product of 12 and 11" on calc-multiply was accepted
  at 0.93 every time. A task-wording effect (the requirement should name the observable, 175),
  and the H0(b) pattern: end state reached, done refused, on every arm alike.
- **calc-percent: System 1 enters the keys in the wrong order.** Under `s1_only` it presses 1, 5,
  Percent, then digits (target confidence 0.46 to 0.69 on the digits), falls into `retry_alternate`
  at 0.23 to 0.42 and escalates on `stuck` 0.93; under `dual` System 2 clears the display and
  System 1 repeats the same sequence until the 25-step budget (three times). Under `guarded` System
  2 plans 240 × 15 % = and finishes in 11 steps (2 of 3 verified; one done refused). This is the one
  task where the dual arm loses to guarded on the agent's own behaviour: a multi-step arithmetic
  order that the operation and target heads cannot see, so they act confidently on the wrong key.
  These rows are the labelled "wrong" clicks the calibration analysis needs.
- **calc-read-result (answer task): `s1_only` cannot answer by design; `dual`'s System 2 done with
  answer "81" was refused twice at complete 0.49 on every repeat, while `guarded`'s identical
  answer on the identical display was accepted at 0.91 every time.** Same page text, same answer,
  same claims (`exact`); the difference is the trajectory the verifier sees (System 1 click lines in
  `dual`, System 2 lines with notes in `guarded`). Verifier variance on thin native state; needs a
  paired probe of the verifier on one fixed state.
- **textedit-read-word-count (answer): every arm fails.** System 2 answers "lantern" in a sentence
  (`narrative` claim); the verifier holds "Reported the second word of the line" unmet at 0.64 and
  refuses twice. A false reject: the answer is right and the document is in the page text.
- **textedit-append-and-save: predicate passes without a save.** TextEdit autosaves in place, so
  `file_contains` passed on 8 of 9 runs whatever happened after the typing step. No arm's done was
  accepted: "The document was saved" is not observable in the window text (unmet 0.80 to 0.89), so
  System 2 pressed cmd+S and File > Save ten times per run. Under `guarded`, System 2 retyped the
  text ten times because the window text shows both lines on one line: the menu builder collapses
  newlines in text-area values (`_clean`). Two task-design faults and one builder fault, none of
  them calibration.
- **calc-multiply, textedit-type-sentence: 3/3 on every arm.** Same steps, same confidences,
  same verifier acceptance across arms; the loop is sound where the task is plain.

## Driver evidence and latency

| executed action | Driver effect | count |
|---|---|---|
| click (AX press) | unverifiable | 285 |
| input (set_value) | confirmed (value readback) | 87 |
| input | refused | 1 |
| send_keys (background press_key) | unverifiable / refused | 12 / 5 |
| menu (invoke_menu) | refused | 3 |

Button presses never carry readback; every `confirmed` came from `set_value`. Background key presses
are refused when the app owns several windows (`same_pid_keyboard_ambiguity`); `invoke_menu` needs
the window frontmost and was refused even after `bring_to_front`. The foreground hotkey route works
(the oracle saves through it). Per step: menu build median 159 ms (p90 453), Jev decision median
162 ms (p90 272). One System 2 step with `reasoning_effort=low` is 5 to 12 s.

Confound to record: Calculator was in Scientific mode for the whole run (a spike earlier in the day
switched it and the setting persists), so every Calculator menu had 54 candidates including memory
and parenthesis keys rather than the 24 of Basic mode. All arms saw the same menus.

## Calibration (pending labels)

Filled in from `results/annotation/q10/` when the two blinded passes and their agreement are in.
