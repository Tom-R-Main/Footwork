# Q18 result: the bounded System 1 rarely has a fixed action, so it gains no time (2026-09-27)

Pre-registration: `docs/experiments/Q18.md` (0868fb7, launch note on 0bc5ca8). Run `results/q18-native-dev`:
native dev split (six tasks), four arms, three repeats, 72 rows, the desktop cleared by the owner.
Verified = predicate passed and done accepted.

| arm | verified | cost USD | cost per verified | wall s per verified | System 1 steps | System 2 steps | handovers |
|---|---|---|---|---|---|---|---|
| s1_only (floor) | 9 of 18 | 0.0137 | 0.00152 | 21.2 | 98 | 0 | 0 |
| dual | 16 of 18 | 0.0299 | 0.00187 | 28.9 | 118 | 37 | 0 |
| guarded | 16 of 18 | 0.0200 | 0.00125 | 33.1 | 0 | 113 | 0 |
| bounded | 17 of 18 | 0.0193 | 0.00114 | 32.9 | 24 | 93 | 20 |

Paired against `guarded` (six tasks, repeats averaged), 95% bootstrap intervals: `bounded` cost per task
−$0.0000 [−0.0001, +0.0001], wall +1.6 s [−3.1, +7.4]; `dual` cost +$0.0006 [−0.0002, +0.0019], wall
−3.8 s [−13.5, +10.4].

## Against the pre-registration

- **H1 not supported:** `bounded` verified the most (17) at the lowest cost per verified task, but its
  wall time per verified task equals `guarded`'s and the paired wall interval includes zero; H1 needed it
  lower.
- **H0(a) is the outcome:** System 1 had a fixed action on 24 of 117 steps; after the first mismatch
  System 2 kept most of the run (20 handovers). On Calculator's and TextEdit's menus the bound (a target
  unique by 0.20, no composed text, nothing needing authority, a confirmed receipt) is rarely met, so
  `bounded` runs close to `guarded`.
- `dual` was 13% faster per verified task than `guarded` this time (Q17: 31%), with its paired wall
  interval including zero, and the most expensive per verified task. Q17 and Q18 differ in the verifier
  default (the strict check since Q16c), so they are not compared directly.
- **Guardrails:** no false completion, no pause, no unauthorized action on any arm. Infrastructure: two
  accessibility-walk timeouts (one `bounded`, one `guarded`) and one run stopped by a locked screen
  (`guarded`), which ended at its first observation with `screen_locked`, as the new stop intends.

## Decision

H0(a), per the rule: `bounded` is not adopted; `guarded` stays the native default where cost matters.
The recorded handovers point to the bound, not the recovery rule: System 1's actions were rarely fixed,
and when they were they confirmed. Whether a looser uniqueness margin keeps the guarantees is a separate
question, not asked here.
