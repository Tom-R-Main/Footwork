# Q11b result: the narrow declaration costs verified passes through the claim check (2026-09-26)

Pre-registration: `docs/experiments/Q11b.md` (ef6d3eb). Runs `results/q11b-live-dev-r1`, `-r2`, `-r3` on
ef6d3eb, in parallel with each other and with Q16b (arms interleaved within every run). Pooled in
`results/q11b-live-dev-pooled` (354 rows, no error rows). The verifier is the default claim check
(`page`), since Q16b did not adopt the strict one.

| pooled, 177 runs per arm | verified | predicate passes | UNVERIFIED | no-fact refusals | driver requests | false completions |
|---|---|---|---|---|---|---|
| guarded | 133 | 172 | 28 | 68 (24, 18, 26) | 820 | 0 |
| guarded_narrow | 123 | 174 | 42 | 91 (38, 25, 28) | 841 | 0 |

Paired per task, 95% bootstrap intervals: requests per unit of progress (primary, 59 of 59 tasks)
−0.14 [−0.52, +0.15]; raw requests +0.12 [−0.10, +0.32]; steps +0.33 [+0.09, +0.60]; done refusals
+0.21 [0.00, +0.40]; UNVERIFIED +0.08 [+0.01, +0.15]; verified −0.06 [−0.13, +0.02]; predicate passes
+0.01 [0.00, +0.03].

## Against the pre-registration

- **H1 not supported:** the primary's interval includes zero.
- **H0(b) is the outcome:** verified passes −10 pooled (−2 allowed); no-fact refusals up, one run (38)
  above `guarded`'s spread (18 to 26); runs ending UNVERIFIED up with the interval above zero. The
  driver did the work (predicate passes +2) and failed to have it accepted.
- My expectation before the run (H1, no-fact refusals near `guarded`'s) was wrong: the sentence asking
  the driver to "state only what the page shows" did not produce done texts the claim check can read.
- Guardrails: no false completion, no unauthorized commit, `undelivered_inputs` zero on both arms (the
  dropdown fix from package D holds).

## Decision

H0(b), per the rule: not adopted; the browser path keeps its requirements undeclared. The done-text
sentence is the suspect and is tested alone before any rerun. Q16's result bears on it: the refusals
this declaration adds are no-fact refusals, the kind the strict claim check removed two-thirds of, so a
rerun belongs on whichever claim check the owner adopts.
