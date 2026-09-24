# Q1 calibration on the labelled annotation set

Source: `results/annotation/q10/q10-s1-decisions.csv`; labels = `model_label` (two blinded passes agreeing).

### All System 1 decisions (acted and escalated)

255 labelled rows (70 wrong, 185 right); excluded: {'disagree': 31}

| signal | AUROC for a wrong step | 95% CI | n | AUROC − op confidence | 95% CI |
|---|---|---|---|---|---|
| s1_op_conf | 0.875 | [0.830, 0.914] | 255 | reference | |
| s1_target_conf | 0.899 | [0.853, 0.942] | 184 | +0.023 | [-0.030, +0.083] |
| goal_done | 0.558 | [0.483, 0.633] | 255 | -0.317 | [-0.383, -0.238] |
| stuck | 0.827 | [0.759, 0.888] | 255 | -0.048 | [-0.132, +0.029] |
| needs_reasoning | 0.609 | [0.540, 0.670] | 255 | -0.266 | [-0.318, -0.214] |
| destructive | 0.483 | [0.411, 0.561] | 255 | -0.392 | [-0.464, -0.321] |

Threshold sweep, s1_op_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 1% | 0% | 0% |
| 0.35 | 7% | 0% | 2% |
| 0.40 | 9% | 0% | 2% |
| 0.45 | 13% | 2% | 5% |
| 0.50 | 20% | 4% | 8% |
| 0.55 | 23% | 4% | 9% |
| 0.60 | 29% | 5% | 11% |
| 0.65 | 40% | 5% | 15% |
| 0.70 | 44% | 6% | 16% |
| 0.75 | 44% | 9% | 18% |
| 0.80 | 46% | 12% | 22% |
| 0.85 | 51% | 17% | 27% |
| 0.90 | 70% | 18% | 33% |
| 0.95 | 99% | 34% | 52% |

Operating point (false escalation ≤ 20%): t = 0.90, catches 70% of wrong steps, escalates 18% of right ones.

Threshold sweep, s1_target_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 6% | 1% | 3% |
| 0.35 | 10% | 1% | 4% |
| 0.40 | 19% | 1% | 6% |
| 0.45 | 25% | 5% | 10% |
| 0.50 | 42% | 7% | 16% |
| 0.55 | 58% | 10% | 23% |
| 0.60 | 77% | 15% | 31% |
| 0.65 | 88% | 21% | 38% |
| 0.70 | 96% | 32% | 49% |
| 0.75 | 98% | 35% | 52% |
| 0.80 | 98% | 40% | 55% |
| 0.85 | 100% | 50% | 63% |
| 0.90 | 100% | 60% | 70% |
| 0.95 | 100% | 79% | 85% |

Operating point (false escalation ≤ 20%): t = 0.60, catches 77% of wrong steps, escalates 15% of right ones.

### Steps System 1 acted on

179 labelled rows (26 wrong, 153 right); excluded: {'disagree': 24}

| signal | AUROC for a wrong step | 95% CI | n | AUROC − op confidence | 95% CI |
|---|---|---|---|---|---|
| s1_op_conf | 0.928 | [0.886, 0.964] | 179 | reference | |
| s1_target_conf | 0.938 | [0.901, 0.974] | 156 | +0.011 | [-0.045, +0.065] |
| goal_done | 0.541 | [0.427, 0.655] | 179 | -0.387 | [-0.500, -0.276] |
| stuck | 0.702 | [0.587, 0.814] | 179 | -0.226 | [-0.359, -0.105] |
| needs_reasoning | 0.660 | [0.575, 0.740] | 179 | -0.268 | [-0.339, -0.194] |
| destructive | 0.428 | [0.296, 0.568] | 179 | -0.500 | [-0.619, -0.378] |

Threshold sweep, s1_op_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 0% | 0% | 0% |
| 0.35 | 0% | 0% | 0% |
| 0.40 | 0% | 0% | 0% |
| 0.45 | 0% | 0% | 0% |
| 0.50 | 0% | 2% | 2% |
| 0.55 | 0% | 2% | 2% |
| 0.60 | 4% | 2% | 2% |
| 0.65 | 23% | 2% | 5% |
| 0.70 | 35% | 3% | 8% |
| 0.75 | 35% | 5% | 9% |
| 0.80 | 38% | 6% | 11% |
| 0.85 | 50% | 8% | 14% |
| 0.90 | 69% | 8% | 17% |
| 0.95 | 96% | 23% | 34% |

Operating point (false escalation ≤ 20%): t = 0.90, catches 69% of wrong steps, escalates 8% of right ones.

Threshold sweep, s1_target_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 12% | 1% | 3% |
| 0.35 | 20% | 1% | 4% |
| 0.40 | 24% | 1% | 4% |
| 0.45 | 28% | 4% | 8% |
| 0.50 | 48% | 5% | 12% |
| 0.55 | 64% | 8% | 17% |
| 0.60 | 88% | 12% | 24% |
| 0.65 | 96% | 18% | 31% |
| 0.70 | 100% | 30% | 41% |
| 0.75 | 100% | 33% | 44% |
| 0.80 | 100% | 37% | 47% |
| 0.85 | 100% | 48% | 56% |
| 0.90 | 100% | 58% | 65% |
| 0.95 | 100% | 79% | 82% |

Operating point (false escalation ≤ 20%): t = 0.65, catches 96% of wrong steps, escalates 18% of right ones.

### Steps System 1 proposed and the arbiter escalated

76 labelled rows (44 wrong, 32 right); excluded: {'disagree': 7}

| signal | AUROC for a wrong step | 95% CI | n | AUROC − op confidence | 95% CI |
|---|---|---|---|---|---|
| s1_op_conf | 0.603 | [0.458, 0.731] | 76 | reference | |
| s1_target_conf | 0.365 | [0.064, 0.764] | 28 | -0.238 | [-0.536, +0.118] |
| goal_done | 0.487 | [0.363, 0.623] | 76 | -0.116 | [-0.285, +0.052] |
| stuck | 0.876 | [0.783, 0.955] | 76 | +0.273 | [+0.105, +0.450] |
| needs_reasoning | 0.228 | [0.116, 0.348] | 76 | -0.375 | [-0.510, -0.245] |
| destructive | 0.374 | [0.239, 0.518] | 76 | -0.229 | [-0.354, -0.095] |

Threshold sweep, s1_op_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 2% | 0% | 1% |
| 0.35 | 11% | 0% | 7% |
| 0.40 | 14% | 0% | 8% |
| 0.45 | 20% | 9% | 16% |
| 0.50 | 32% | 12% | 24% |
| 0.55 | 36% | 16% | 28% |
| 0.60 | 43% | 19% | 33% |
| 0.65 | 50% | 19% | 37% |
| 0.70 | 50% | 19% | 37% |
| 0.75 | 50% | 25% | 39% |
| 0.80 | 50% | 44% | 47% |
| 0.85 | 52% | 62% | 57% |
| 0.90 | 70% | 69% | 70% |
| 0.95 | 100% | 88% | 95% |

Operating point (false escalation ≤ 20%): t = 0.65, catches 50% of wrong steps, escalates 19% of right ones.

Threshold sweep, s1_target_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 0% | 20% | 4% |
| 0.35 | 0% | 20% | 4% |
| 0.40 | 13% | 20% | 14% |
| 0.45 | 22% | 40% | 25% |
| 0.50 | 35% | 60% | 39% |
| 0.55 | 52% | 80% | 57% |
| 0.60 | 65% | 80% | 68% |
| 0.65 | 78% | 80% | 79% |
| 0.70 | 91% | 100% | 93% |
| 0.75 | 96% | 100% | 96% |
| 0.80 | 96% | 100% | 96% |
| 0.85 | 100% | 100% | 100% |
| 0.90 | 100% | 100% | 100% |
| 0.95 | 100% | 100% | 100% |

Operating point (false escalation ≤ 20%): t = 0.40, catches 13% of wrong steps, escalates 20% of right ones.

### Operation `click`

171 labelled rows (48 wrong, 123 right); excluded: {'disagree': 31}

| signal | AUROC for a wrong step | 95% CI | n | AUROC − op confidence | 95% CI |
|---|---|---|---|---|---|
| s1_op_conf | 0.934 | [0.889, 0.969] | 171 | reference | |
| s1_target_conf | 0.888 | [0.841, 0.933] | 171 | -0.045 | [-0.105, +0.013] |
| goal_done | 0.516 | [0.426, 0.598] | 171 | -0.418 | [-0.507, -0.338] |
| stuck | 0.811 | [0.729, 0.892] | 171 | -0.122 | [-0.210, -0.038] |
| needs_reasoning | 0.749 | [0.669, 0.821] | 171 | -0.184 | [-0.251, -0.121] |
| destructive | 0.492 | [0.399, 0.588] | 171 | -0.441 | [-0.534, -0.343] |

Threshold sweep, s1_op_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 0% | 0% | 0% |
| 0.35 | 0% | 0% | 0% |
| 0.40 | 0% | 0% | 0% |
| 0.45 | 0% | 0% | 0% |
| 0.50 | 0% | 0% | 0% |
| 0.55 | 0% | 0% | 0% |
| 0.60 | 4% | 0% | 1% |
| 0.65 | 17% | 0% | 5% |
| 0.70 | 21% | 2% | 7% |
| 0.75 | 21% | 4% | 9% |
| 0.80 | 23% | 5% | 10% |
| 0.85 | 31% | 6% | 13% |
| 0.90 | 58% | 7% | 21% |
| 0.95 | 98% | 23% | 44% |

Operating point (false escalation ≤ 20%): t = 0.90, catches 58% of wrong steps, escalates 7% of right ones.

Threshold sweep, s1_target_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 6% | 2% | 3% |
| 0.35 | 10% | 2% | 4% |
| 0.40 | 19% | 2% | 6% |
| 0.45 | 25% | 6% | 11% |
| 0.50 | 42% | 7% | 17% |
| 0.55 | 58% | 11% | 25% |
| 0.60 | 77% | 16% | 33% |
| 0.65 | 88% | 23% | 41% |
| 0.70 | 96% | 36% | 53% |
| 0.75 | 98% | 39% | 56% |
| 0.80 | 98% | 44% | 59% |
| 0.85 | 100% | 55% | 68% |
| 0.90 | 100% | 66% | 75% |
| 0.95 | 100% | 88% | 91% |

Operating point (false escalation ≤ 20%): t = 0.60, catches 77% of wrong steps, escalates 16% of right ones.

### Operation `done`

55 labelled rows (20 wrong, 35 right); excluded: {}

| signal | AUROC for a wrong step | 95% CI | n | AUROC − op confidence | 95% CI |
|---|---|---|---|---|---|
| s1_op_conf | 0.849 | [0.741, 0.938] | 55 | reference | |
| s1_target_conf | n/a | | 0 | | |
| goal_done | 0.261 | [0.128, 0.406] | 55 | -0.587 | [-0.796, -0.354] |
| stuck | 0.839 | [0.679, 0.971] | 55 | -0.010 | [-0.177, +0.141] |
| needs_reasoning | 0.229 | [0.108, 0.360] | 55 | -0.619 | [-0.759, -0.474] |
| destructive | 0.449 | [0.299, 0.595] | 55 | -0.399 | [-0.563, -0.235] |

Threshold sweep, s1_op_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 0% | 0% | 0% |
| 0.35 | 15% | 0% | 5% |
| 0.40 | 20% | 0% | 7% |
| 0.45 | 35% | 9% | 18% |
| 0.50 | 60% | 20% | 35% |
| 0.55 | 70% | 23% | 40% |
| 0.60 | 80% | 26% | 45% |
| 0.65 | 90% | 26% | 49% |
| 0.70 | 95% | 26% | 51% |
| 0.75 | 95% | 26% | 51% |
| 0.80 | 95% | 29% | 53% |
| 0.85 | 95% | 31% | 55% |
| 0.90 | 95% | 34% | 56% |
| 0.95 | 100% | 51% | 69% |

Operating point (false escalation ≤ 20%): t = 0.50, catches 60% of wrong steps, escalates 20% of right ones.

Threshold sweep, s1_target_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 0% | 0% | 0% |
| 0.35 | 0% | 0% | 0% |
| 0.40 | 0% | 0% | 0% |
| 0.45 | 0% | 0% | 0% |
| 0.50 | 0% | 0% | 0% |
| 0.55 | 0% | 0% | 0% |
| 0.60 | 0% | 0% | 0% |
| 0.65 | 0% | 0% | 0% |
| 0.70 | 0% | 0% | 0% |
| 0.75 | 0% | 0% | 0% |
| 0.80 | 0% | 0% | 0% |
| 0.85 | 0% | 0% | 0% |
| 0.90 | 0% | 0% | 0% |
| 0.95 | 0% | 0% | 0% |

Operating point (false escalation ≤ 20%): t = 0.30, catches 0% of wrong steps, escalates 0% of right ones.

