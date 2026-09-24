# Q1 calibration on the labelled annotation set

Source: `results/annotation/q10b/q10b-s1-decisions.csv`; labels = `model_label` (two blinded passes agreeing).

### All System 1 decisions (acted and escalated)

243 labelled rows (21 wrong, 222 right); excluded: {'disagree': 3}

| signal | AUROC for a wrong step | 95% CI | n | AUROC − op confidence | 95% CI |
|---|---|---|---|---|---|
| s1_op_conf | 0.915 | [0.866, 0.955] | 243 | reference | |
| s1_target_conf | 0.869 | [0.813, 0.917] | 201 | -0.046 | [-0.118, +0.030] |
| goal_done | 0.574 | [0.466, 0.687] | 243 | -0.340 | [-0.435, -0.227] |
| stuck | 0.564 | [0.452, 0.676] | 243 | -0.351 | [-0.480, -0.201] |
| needs_reasoning | 0.690 | [0.622, 0.758] | 243 | -0.224 | [-0.281, -0.170] |
| destructive | 0.537 | [0.433, 0.637] | 243 | -0.377 | [-0.475, -0.288] |

Threshold sweep, s1_op_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 0% | 0% | 0% |
| 0.35 | 5% | 0% | 1% |
| 0.40 | 5% | 0% | 1% |
| 0.45 | 5% | 1% | 2% |
| 0.50 | 5% | 1% | 2% |
| 0.55 | 10% | 2% | 2% |
| 0.60 | 19% | 2% | 3% |
| 0.65 | 33% | 2% | 5% |
| 0.70 | 43% | 3% | 7% |
| 0.75 | 48% | 5% | 8% |
| 0.80 | 48% | 8% | 11% |
| 0.85 | 67% | 9% | 14% |
| 0.90 | 81% | 13% | 19% |
| 0.95 | 100% | 36% | 42% |

Operating point (false escalation ≤ 20%): t = 0.90, catches 81% of wrong steps, escalates 13% of right ones.

Threshold sweep, s1_target_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 0% | 0% | 0% |
| 0.35 | 15% | 2% | 3% |
| 0.40 | 15% | 3% | 4% |
| 0.45 | 25% | 6% | 7% |
| 0.50 | 25% | 7% | 9% |
| 0.55 | 30% | 11% | 13% |
| 0.60 | 55% | 14% | 18% |
| 0.65 | 80% | 20% | 26% |
| 0.70 | 95% | 24% | 31% |
| 0.75 | 100% | 29% | 36% |
| 0.80 | 100% | 34% | 41% |
| 0.85 | 100% | 42% | 48% |
| 0.90 | 100% | 57% | 62% |
| 0.95 | 100% | 85% | 87% |

Operating point (false escalation ≤ 20%): t = 0.65, catches 80% of wrong steps, escalates 20% of right ones.

### Steps System 1 acted on

217 labelled rows (17 wrong, 200 right); excluded: {'disagree': 1}

| signal | AUROC for a wrong step | 95% CI | n | AUROC − op confidence | 95% CI |
|---|---|---|---|---|---|
| s1_op_conf | 0.944 | [0.896, 0.981] | 217 | reference | |
| s1_target_conf | 0.884 | [0.828, 0.933] | 190 | -0.060 | [-0.130, +0.008] |
| goal_done | 0.616 | [0.486, 0.737] | 217 | -0.327 | [-0.441, -0.207] |
| stuck | 0.552 | [0.433, 0.679] | 217 | -0.392 | [-0.528, -0.240] |
| needs_reasoning | 0.725 | [0.651, 0.801] | 217 | -0.219 | [-0.280, -0.161] |
| destructive | 0.525 | [0.417, 0.638] | 217 | -0.419 | [-0.524, -0.313] |

Threshold sweep, s1_op_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 0% | 0% | 0% |
| 0.35 | 0% | 0% | 0% |
| 0.40 | 0% | 0% | 0% |
| 0.45 | 0% | 0% | 0% |
| 0.50 | 0% | 0% | 0% |
| 0.55 | 0% | 0% | 0% |
| 0.60 | 12% | 0% | 1% |
| 0.65 | 29% | 0% | 2% |
| 0.70 | 41% | 2% | 5% |
| 0.75 | 47% | 2% | 6% |
| 0.80 | 47% | 3% | 6% |
| 0.85 | 65% | 4% | 9% |
| 0.90 | 76% | 7% | 12% |
| 0.95 | 100% | 30% | 36% |

Operating point (false escalation ≤ 20%): t = 0.90, catches 76% of wrong steps, escalates 7% of right ones.

Threshold sweep, s1_target_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 0% | 0% | 0% |
| 0.35 | 18% | 2% | 3% |
| 0.40 | 18% | 3% | 5% |
| 0.45 | 24% | 4% | 6% |
| 0.50 | 24% | 5% | 7% |
| 0.55 | 29% | 9% | 11% |
| 0.60 | 47% | 12% | 15% |
| 0.65 | 76% | 17% | 23% |
| 0.70 | 94% | 21% | 28% |
| 0.75 | 100% | 26% | 33% |
| 0.80 | 100% | 32% | 38% |
| 0.85 | 100% | 40% | 45% |
| 0.90 | 100% | 56% | 60% |
| 0.95 | 100% | 85% | 86% |

Operating point (false escalation ≤ 20%): t = 0.65, catches 76% of wrong steps, escalates 17% of right ones.

### Steps System 1 proposed and the arbiter escalated

26 labelled rows (4 wrong, 22 right); excluded: {'disagree': 2}

| signal | AUROC for a wrong step | 95% CI | n | AUROC − op confidence | 95% CI |
|---|---|---|---|---|---|
| s1_op_conf | 0.670 | [0.364, 0.957] | 26 | reference | |
| s1_target_conf | 0.562 | [0.125, 1.000] | 11 | -0.108 | [-0.708, +0.446] |
| goal_done | 0.347 | [0.196, 0.580] | 26 | -0.324 | [-0.580, -0.054] |
| stuck | 0.540 | [0.219, 0.920] | 26 | -0.131 | [-0.660, +0.396] |
| needs_reasoning | 0.330 | [0.083, 0.667] | 26 | -0.341 | [-0.609, -0.125] |
| destructive | 0.460 | [0.237, 0.676] | 26 | -0.210 | [-0.500, +0.125] |

Threshold sweep, s1_op_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 0% | 5% | 4% |
| 0.35 | 25% | 5% | 8% |
| 0.40 | 25% | 5% | 8% |
| 0.45 | 25% | 14% | 15% |
| 0.50 | 25% | 14% | 15% |
| 0.55 | 50% | 18% | 23% |
| 0.60 | 50% | 18% | 23% |
| 0.65 | 50% | 18% | 23% |
| 0.70 | 50% | 18% | 23% |
| 0.75 | 50% | 27% | 31% |
| 0.80 | 50% | 50% | 50% |
| 0.85 | 75% | 55% | 58% |
| 0.90 | 100% | 64% | 69% |
| 0.95 | 100% | 86% | 88% |

Operating point (false escalation ≤ 20%): t = 0.55, catches 50% of wrong steps, escalates 18% of right ones.

Threshold sweep, s1_target_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 0% | 0% | 0% |
| 0.35 | 0% | 0% | 0% |
| 0.40 | 0% | 0% | 0% |
| 0.45 | 33% | 38% | 36% |
| 0.50 | 33% | 50% | 45% |
| 0.55 | 33% | 50% | 45% |
| 0.60 | 100% | 75% | 82% |
| 0.65 | 100% | 75% | 82% |
| 0.70 | 100% | 88% | 91% |
| 0.75 | 100% | 88% | 91% |
| 0.80 | 100% | 88% | 91% |
| 0.85 | 100% | 88% | 91% |
| 0.90 | 100% | 88% | 91% |
| 0.95 | 100% | 88% | 91% |

Operating point (false escalation ≤ 20%): t = 0.30, catches 0% of wrong steps, escalates 0% of right ones.

### Operation `click`

189 labelled rows (20 wrong, 169 right); excluded: {'disagree': 3}

| signal | AUROC for a wrong step | 95% CI | n | AUROC − op confidence | 95% CI |
|---|---|---|---|---|---|
| s1_op_conf | 0.948 | [0.900, 0.981] | 189 | reference | |
| s1_target_conf | 0.859 | [0.797, 0.912] | 189 | -0.088 | [-0.149, -0.026] |
| goal_done | 0.657 | [0.516, 0.780] | 189 | -0.291 | [-0.411, -0.157] |
| stuck | 0.575 | [0.453, 0.690] | 189 | -0.372 | [-0.508, -0.242] |
| needs_reasoning | 0.862 | [0.801, 0.916] | 189 | -0.085 | [-0.133, -0.045] |
| destructive | 0.592 | [0.483, 0.704] | 189 | -0.355 | [-0.469, -0.250] |

Threshold sweep, s1_op_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 0% | 1% | 1% |
| 0.35 | 0% | 1% | 1% |
| 0.40 | 0% | 1% | 1% |
| 0.45 | 0% | 2% | 2% |
| 0.50 | 0% | 2% | 2% |
| 0.55 | 5% | 2% | 2% |
| 0.60 | 15% | 2% | 3% |
| 0.65 | 30% | 2% | 5% |
| 0.70 | 40% | 2% | 6% |
| 0.75 | 45% | 2% | 6% |
| 0.80 | 45% | 2% | 6% |
| 0.85 | 65% | 2% | 8% |
| 0.90 | 80% | 5% | 13% |
| 0.95 | 100% | 33% | 40% |

Operating point (false escalation ≤ 20%): t = 0.90, catches 80% of wrong steps, escalates 5% of right ones.

Threshold sweep, s1_target_conf (escalate when below t):

| t | wrong caught | right escalated | share escalated |
|---|---|---|---|
| 0.30 | 0% | 0% | 0% |
| 0.35 | 15% | 2% | 3% |
| 0.40 | 15% | 4% | 5% |
| 0.45 | 25% | 6% | 8% |
| 0.50 | 25% | 8% | 10% |
| 0.55 | 30% | 12% | 14% |
| 0.60 | 55% | 15% | 20% |
| 0.65 | 80% | 21% | 28% |
| 0.70 | 95% | 26% | 33% |
| 0.75 | 100% | 31% | 38% |
| 0.80 | 100% | 37% | 43% |
| 0.85 | 100% | 45% | 51% |
| 0.90 | 100% | 62% | 66% |
| 0.95 | 100% | 91% | 92% |

Operating point (false escalation ≤ 20%): t = 0.60, catches 55% of wrong steps, escalates 15% of right ones.

