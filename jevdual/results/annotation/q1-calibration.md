# Q1 calibration on the labelled annotation set

Source: `results/annotation/q1-s1-decisions.csv`; labels = `model_label` (two blinded passes agreeing).

### All System 1 decisions (acted and escalated)

491 labelled rows (81 wrong, 410 right); excluded: {'unclear': 22, 'disagree': 17}

| signal | AUROC for a wrong step | 95% CI | n | AUROC − op confidence | 95% CI |
|---|---|---|---|---|---|
| s1_op_conf | 0.590 | [0.517, 0.661] | 491 | reference | |
| s1_target_conf | 0.664 | [0.597, 0.730] | 388 | +0.074 | [-0.027, +0.174] |
| goal_done | 0.346 | [0.274, 0.419] | 491 | -0.243 | [-0.357, -0.126] |
| stuck | 0.527 | [0.461, 0.586] | 491 | -0.062 | [-0.161, +0.039] |
| needs_reasoning | 0.532 | [0.468, 0.597] | 491 | -0.057 | [-0.125, +0.009] |
| destructive | 0.636 | [0.583, 0.694] | 491 | +0.046 | [-0.051, +0.141] |

Threshold sweep, s1_op_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 5% | 1% | 1% |
| 0.35 | 5% | 1% | 2% |
| 0.40 | 7% | 1% | 2% |
| 0.45 | 12% | 3% | 4% |
| 0.50 | 16% | 4% | 6% |
| 0.55 | 22% | 6% | 9% |
| 0.60 | 27% | 8% | 11% |
| 0.65 | 32% | 11% | 15% |
| 0.70 | 32% | 16% | 19% |
| 0.75 | 37% | 20% | 23% |
| 0.80 | 38% | 26% | 28% |
| 0.85 | 46% | 32% | 34% |
| 0.90 | 58% | 44% | 46% |
| 0.95 | 70% | 65% | 66% |

Operating point (false escalation ≤ 20%): t = 0.75, catches 37% of wrong steps, escalates 20% of right ones.

Threshold sweep, s1_target_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 2% | 4% | 3% |
| 0.35 | 2% | 5% | 4% |
| 0.40 | 3% | 6% | 6% |
| 0.45 | 3% | 8% | 7% |
| 0.50 | 10% | 9% | 10% |
| 0.55 | 12% | 9% | 10% |
| 0.60 | 20% | 10% | 12% |
| 0.65 | 25% | 12% | 14% |
| 0.70 | 32% | 14% | 16% |
| 0.75 | 41% | 15% | 19% |
| 0.80 | 44% | 16% | 21% |
| 0.85 | 53% | 20% | 25% |
| 0.90 | 54% | 23% | 28% |
| 0.95 | 59% | 34% | 38% |

Operating point (false escalation ≤ 20%): t = 0.80, catches 44% of wrong steps, escalates 16% of right ones.

### Steps System 1 acted on

238 labelled rows (43 wrong, 195 right); excluded: {'unclear': 6, 'disagree': 5}

| signal | AUROC for a wrong step | 95% CI | n | AUROC − op confidence | 95% CI |
|---|---|---|---|---|---|
| s1_op_conf | 0.534 | [0.444, 0.619] | 238 | reference | |
| s1_target_conf | 0.672 | [0.581, 0.752] | 219 | +0.139 | [+0.014, +0.246] |
| goal_done | 0.255 | [0.164, 0.355] | 238 | -0.279 | [-0.418, -0.131] |
| stuck | 0.525 | [0.408, 0.634] | 238 | -0.009 | [-0.144, +0.124] |
| needs_reasoning | 0.687 | [0.608, 0.761] | 238 | +0.153 | [+0.067, +0.241] |
| destructive | 0.651 | [0.576, 0.720] | 238 | +0.117 | [+0.007, +0.226] |

Threshold sweep, s1_op_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 0% | 0% | 0% |
| 0.35 | 0% | 1% | 0% |
| 0.40 | 0% | 1% | 0% |
| 0.45 | 0% | 1% | 0% |
| 0.50 | 0% | 1% | 0% |
| 0.55 | 0% | 2% | 2% |
| 0.60 | 5% | 5% | 5% |
| 0.65 | 9% | 8% | 8% |
| 0.70 | 9% | 14% | 13% |
| 0.75 | 19% | 19% | 19% |
| 0.80 | 19% | 29% | 27% |
| 0.85 | 33% | 37% | 36% |
| 0.90 | 56% | 47% | 48% |
| 0.95 | 77% | 68% | 69% |

Operating point (false escalation ≤ 20%): t = 0.75, catches 19% of wrong steps, escalates 19% of right ones.

Threshold sweep, s1_target_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 0% | 3% | 3% |
| 0.35 | 0% | 4% | 3% |
| 0.40 | 0% | 4% | 3% |
| 0.45 | 0% | 4% | 3% |
| 0.50 | 5% | 5% | 5% |
| 0.55 | 5% | 5% | 5% |
| 0.60 | 12% | 6% | 7% |
| 0.65 | 17% | 6% | 8% |
| 0.70 | 22% | 7% | 10% |
| 0.75 | 27% | 7% | 11% |
| 0.80 | 29% | 8% | 12% |
| 0.85 | 39% | 10% | 15% |
| 0.90 | 39% | 12% | 17% |
| 0.95 | 41% | 22% | 26% |

Operating point (false escalation ≤ 20%): t = 0.85, catches 39% of wrong steps, escalates 10% of right ones.

### Steps System 1 proposed and the arbiter escalated

253 labelled rows (38 wrong, 215 right); excluded: {'unclear': 16, 'disagree': 12}

| signal | AUROC for a wrong step | 95% CI | n | AUROC − op confidence | 95% CI |
|---|---|---|---|---|---|
| s1_op_conf | 0.613 | [0.474, 0.741] | 253 | reference | |
| s1_target_conf | 0.793 | [0.720, 0.868] | 169 | +0.181 | [+0.040, +0.335] |
| goal_done | 0.435 | [0.330, 0.543] | 253 | -0.177 | [-0.360, +0.001] |
| stuck | 0.537 | [0.458, 0.617] | 253 | -0.076 | [-0.224, +0.075] |
| needs_reasoning | 0.417 | [0.315, 0.518] | 253 | -0.196 | [-0.298, -0.087] |
| destructive | 0.609 | [0.518, 0.695] | 253 | -0.004 | [-0.170, +0.169] |

Threshold sweep, s1_op_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 11% | 1% | 3% |
| 0.35 | 11% | 1% | 3% |
| 0.40 | 16% | 2% | 4% |
| 0.45 | 26% | 5% | 8% |
| 0.50 | 34% | 7% | 11% |
| 0.55 | 47% | 10% | 15% |
| 0.60 | 53% | 11% | 17% |
| 0.65 | 58% | 14% | 21% |
| 0.70 | 58% | 18% | 24% |
| 0.75 | 58% | 20% | 26% |
| 0.80 | 61% | 24% | 30% |
| 0.85 | 61% | 27% | 32% |
| 0.90 | 61% | 41% | 44% |
| 0.95 | 63% | 62% | 62% |

Operating point (false escalation ≤ 20%): t = 0.65, catches 58% of wrong steps, escalates 14% of right ones.

Threshold sweep, s1_target_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 6% | 4% | 4% |
| 0.35 | 6% | 5% | 5% |
| 0.40 | 11% | 9% | 9% |
| 0.45 | 11% | 13% | 12% |
| 0.50 | 22% | 15% | 15% |
| 0.55 | 28% | 15% | 16% |
| 0.60 | 39% | 15% | 18% |
| 0.65 | 44% | 18% | 21% |
| 0.70 | 56% | 22% | 25% |
| 0.75 | 72% | 24% | 29% |
| 0.80 | 78% | 26% | 32% |
| 0.85 | 83% | 32% | 38% |
| 0.90 | 89% | 36% | 42% |
| 0.95 | 100% | 48% | 54% |

Operating point (false escalation ≤ 20%): t = 0.65, catches 44% of wrong steps, escalates 18% of right ones.

### Operation `type`

225 labelled rows (35 wrong, 190 right); excluded: {}

| signal | AUROC for a wrong step | 95% CI | n | AUROC − op confidence | 95% CI |
|---|---|---|---|---|---|
| s1_op_conf | 0.503 | [0.396, 0.594] | 225 | reference | |
| s1_target_conf | 0.581 | [0.488, 0.673] | 225 | +0.078 | [-0.053, +0.223] |
| goal_done | 0.238 | [0.156, 0.327] | 225 | -0.264 | [-0.401, -0.107] |
| stuck | 0.472 | [0.355, 0.589] | 225 | -0.031 | [-0.184, +0.127] |
| needs_reasoning | 0.625 | [0.538, 0.704] | 225 | +0.123 | [-0.006, +0.257] |
| destructive | 0.610 | [0.534, 0.687] | 225 | +0.107 | [-0.011, +0.237] |

Threshold sweep, s1_op_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 0% | 0% | 0% |
| 0.35 | 0% | 0% | 0% |
| 0.40 | 0% | 0% | 0% |
| 0.45 | 0% | 1% | 1% |
| 0.50 | 0% | 2% | 2% |
| 0.55 | 0% | 5% | 4% |
| 0.60 | 0% | 6% | 5% |
| 0.65 | 9% | 12% | 11% |
| 0.70 | 9% | 18% | 16% |
| 0.75 | 17% | 23% | 22% |
| 0.80 | 20% | 29% | 28% |
| 0.85 | 37% | 35% | 36% |
| 0.90 | 60% | 52% | 53% |
| 0.95 | 83% | 85% | 84% |

Operating point (false escalation ≤ 20%): t = 0.65, catches 9% of wrong steps, escalates 12% of right ones.

Threshold sweep, s1_target_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 3% | 6% | 6% |
| 0.35 | 3% | 7% | 7% |
| 0.40 | 3% | 9% | 8% |
| 0.45 | 3% | 11% | 10% |
| 0.50 | 6% | 12% | 11% |
| 0.55 | 6% | 12% | 11% |
| 0.60 | 9% | 13% | 12% |
| 0.65 | 17% | 15% | 16% |
| 0.70 | 17% | 17% | 17% |
| 0.75 | 23% | 17% | 18% |
| 0.80 | 26% | 18% | 19% |
| 0.85 | 34% | 20% | 22% |
| 0.90 | 34% | 21% | 23% |
| 0.95 | 37% | 22% | 24% |

Operating point (false escalation ≤ 20%): t = 0.85, catches 34% of wrong steps, escalates 20% of right ones.

### Operation `click`

134 labelled rows (24 wrong, 110 right); excluded: {'unclear': 4, 'disagree': 6}

| signal | AUROC for a wrong step | 95% CI | n | AUROC − op confidence | 95% CI |
|---|---|---|---|---|---|
| s1_op_conf | 0.513 | [0.373, 0.655] | 134 | reference | |
| s1_target_conf | 0.804 | [0.691, 0.898] | 134 | +0.291 | [+0.139, +0.450] |
| goal_done | 0.682 | [0.560, 0.802] | 134 | +0.169 | [+0.039, +0.318] |
| stuck | 0.410 | [0.318, 0.507] | 134 | -0.104 | [-0.285, +0.084] |
| needs_reasoning | 0.522 | [0.395, 0.651] | 134 | +0.008 | [-0.115, +0.119] |
| destructive | 0.605 | [0.484, 0.725] | 134 | +0.091 | [-0.108, +0.289] |

Threshold sweep, s1_op_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 8% | 1% | 2% |
| 0.35 | 8% | 1% | 2% |
| 0.40 | 12% | 1% | 3% |
| 0.45 | 17% | 5% | 7% |
| 0.50 | 17% | 6% | 8% |
| 0.55 | 21% | 8% | 10% |
| 0.60 | 25% | 10% | 13% |
| 0.65 | 25% | 10% | 13% |
| 0.70 | 25% | 13% | 15% |
| 0.75 | 29% | 15% | 17% |
| 0.80 | 29% | 16% | 19% |
| 0.85 | 29% | 21% | 22% |
| 0.90 | 38% | 34% | 34% |
| 0.95 | 42% | 45% | 45% |

Operating point (false escalation ≤ 20%): t = 0.75, catches 29% of wrong steps, escalates 15% of right ones.

Threshold sweep, s1_target_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 0% | 0% | 0% |
| 0.35 | 0% | 1% | 1% |
| 0.40 | 4% | 3% | 3% |
| 0.45 | 4% | 5% | 4% |
| 0.50 | 17% | 7% | 9% |
| 0.55 | 21% | 7% | 10% |
| 0.60 | 38% | 8% | 13% |
| 0.65 | 38% | 8% | 13% |
| 0.70 | 54% | 12% | 19% |
| 0.75 | 67% | 15% | 24% |
| 0.80 | 71% | 18% | 28% |
| 0.85 | 79% | 25% | 35% |
| 0.90 | 83% | 34% | 43% |
| 0.95 | 92% | 65% | 69% |

Operating point (false escalation ≤ 20%): t = 0.80, catches 71% of wrong steps, escalates 18% of right ones.

### Operation `done`

78 labelled rows (5 wrong, 73 right); excluded: {'unclear': 5, 'disagree': 9}

| signal | AUROC for a wrong step | 95% CI | n | AUROC − op confidence | 95% CI |
|---|---|---|---|---|---|
| s1_op_conf | 0.390 | [0.167, 0.608] | 78 | reference | |
| s1_target_conf | n/a | | 0 | | |
| goal_done | 0.921 | [0.858, 0.975] | 78 | +0.530 | [+0.264, +0.801] |
| stuck | 0.392 | [0.164, 0.598] | 78 | +0.001 | [-0.351, +0.292] |
| needs_reasoning | 0.110 | [0.004, 0.293] | 78 | -0.281 | [-0.586, -0.036] |
| destructive | 0.634 | [0.336, 0.870] | 78 | +0.244 | [-0.002, +0.602] |

Threshold sweep, s1_op_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 0% | 1% | 1% |
| 0.35 | 0% | 3% | 3% |
| 0.40 | 0% | 3% | 3% |
| 0.45 | 0% | 3% | 3% |
| 0.50 | 0% | 3% | 3% |
| 0.55 | 0% | 4% | 4% |
| 0.60 | 0% | 8% | 8% |
| 0.65 | 0% | 8% | 8% |
| 0.70 | 0% | 10% | 9% |
| 0.75 | 0% | 11% | 10% |
| 0.80 | 0% | 15% | 14% |
| 0.85 | 0% | 18% | 17% |
| 0.90 | 0% | 21% | 19% |
| 0.95 | 20% | 33% | 32% |

Operating point (false escalation ≤ 20%): t = 0.30, catches 0% of wrong steps, escalates 1% of right ones.

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

