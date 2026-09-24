# Annotation set for Q1: System 1's decisions, one row per step

`q1-s1-decisions.csv` holds every step where System 1 chose a target, from the runs whose traces carry
the menu snapshot and verification scores (`results/q8-q9e-live-dev-20260922-162350`, dual and delegate
arms; `results/q9e-delegate-20260922-212255`). Built by `uv run python -m evals.annotation <run> ... --out <csv>`.

| what | rows |
|---|---|
| System 1 acted (`system` = s1) | 188 |
| System 1 proposed, the arbiter escalated and System 2 acted (`system` = s2) | 222 |
| total | 410 |

## How to label

Fill `label` with one of `right`, `wrong`, `unclear`; put anything worth keeping in `note`. Leave
`auto_label` alone (it is the heuristic from `evals.labels`, right/wrong for s1 rows by what happened
next, `unknown` for s2 rows, and it is what the labels are measured against).

The question is the same for every row: **given the task and the page, was System 1's choice
(`s1_operation` on `s1_target`) the right next action?** Not whether the run passed, and not whether
System 2 did something better.

- **s1 rows**: `executed` is System 1's own action. `url_after`, `next_reason` and `result_error` show
  what it did to the page. A choice can be right and the run still fail later; label the choice.
- **s2 rows**: System 1 proposed `s1_target` and was escalated (`arbiter_reason` says why: a low
  confidence, a noul such as destructive or stuck, or a periodic check-in). `executed` and
  `executed_target` are what System 2 ran instead. Label whether System 1's proposal would have been
  right; System 2's action is a hint, not the answer.
- `alternatives` lists the next-best targets with their probabilities, so a wrong choice can be noted
  as "the second option was right" in `note`.
- `menu_size` is how many controls System 1 could choose from. A right target missing from the menu
  is a menu defect, not a choice defect: label `unclear` and say so.
- `destructive`, `stuck`, `needs_reasoning`, `goal_done` are System 1's own situation judgments; they
  are not what is being labelled but they explain the escalation.

Task text is in `task_text`; the page is `url` (the start page for step 1, otherwise the previous
step's page). The traces under each run's `traces/` directory have the full menu per step if a row
needs more than the CSV shows.

## What the labels feed

Q1 (`docs/experiments/Q1.md`): calibration of System 1's operation and target confidences against
human right/wrong, the AUROC of the confidence floors, and the threshold sweep the arbiter policy is
frozen from. Rows labelled `unclear` are excluded from calibration and counted separately.

## Model labels and the audit (2026-09-23)

The CSV now carries `label_a`/`reason_a` and `label_b`/`reason_b` from two blinded Claude Fable
passes (see `docs/experiments/Q1.md`, amendment of 2026-09-23) and `model_label`, the agreed label or
`disagree`. Agreement 96.8%, kappa 0.91. `labels-a/` and `labels-b/` hold the raw passes per packet;
`packets/` (not committed, rebuilt by `scripts/build_label_packets.py`) is what the labellers saw.

**Your part: `audit-sheet.csv`**, 40 rows, blind (no outcome columns, no model labels). Fill
`audit_label` with right / wrong / unclear per `RUBRIC.md` and anything useful in `audit_note`. Then:

    uv run python scripts/audit_agreement.py results/annotation/audit-sheet.csv results/annotation/q1-s1-decisions.csv

reports your agreement with each pass and with the agreed label. `q1-calibration.md` is the Q1
analysis on the agreed labels and is provisional until that number is in.

