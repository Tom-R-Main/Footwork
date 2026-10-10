# Q16 result: the strict claim check removes two-thirds of no-fact refusals; the verified gain misses its interval (2026-09-26)

Pre-registration: `docs/experiments/Q16.md` (ac77fa3, amendment be315bd, launch note 59c11c7). Runs
`results/q16-live-dev-r1`, `-r2`, `-r3` on f9bbc96; run 1 alone and partly alongside Q12b, runs 2 and 3
in parallel after it (arms interleaved within every run). Pooled in `results/q16-live-dev-pooled`
(354 rows, no error rows).

## Headline

| pooled, 177 runs per arm | verified | predicate passes | no-fact refusals | UNVERIFIED no_evidence | false completions | driver requests |
|---|---|---|---|---|---|---|
| guarded | 137 | 174 | 62 | 18 | 0 | 809 |
| guarded_evidence | 148 | 174 | 20 | 4 | 0 | 770 |

Verified passes per run: `guarded` 44, 45, 48; `guarded_evidence` 50, 48, 50. Paired per task, 95%
bootstrap intervals: verified +0.062 [−0.011, +0.141] (primary); steps −0.35 [−0.62, −0.07]; done
refusals −0.22 [−0.44, −0.00]; driver requests −0.22 [−0.44, +0.01]; requests per unit of progress
−0.13 [−0.32, +0.07]. On the four tasks Q12 recorded no-fact refusals on
(`lh-form-fill-no-submit`, `ls-bike-light-price`, `li-key-press`, `ls-sort-cheapest`): verified 4 of 12
on `guarded`, 12 of 12 on `guarded_evidence`.

## Against the pre-registration

- **H1 not supported at its interval.** Verified passes rose 11 pooled and in every run, but the paired
  interval on the primary includes zero. The secondary predictions held: no-fact refusals fell to 32%
  (at most half predicted), `no_evidence` endings fell 18 to 4.
- **H0(a) rejected** (verified +11, not within ±2; no-fact down 68%, not less than a third).
- **H0(b) rejected:** no verified run on either arm has a failing predicate; no unauthorized run reached
  a committing URL. The two tasks accepted on field evidence (`lh-form-fill-no-submit` 3,
  `lw-github-pyo3-issues` 1) passed their predicates.
- The rule adopts only on H1; the outcome falls between its branches.

## Decision

Not adopted as the default on this run, per the rule. The strict check stays the `guarded_evidence`
arm. `CONTRIBUTING.md` already names the step for a verifier setting: run the heldout once. Q16b
pre-registers that run with an adoption rule, before it runs. Notebook V1 (the mechanism) held.
