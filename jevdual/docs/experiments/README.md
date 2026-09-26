# Experiment program

One pre-registered experiment per open question, committed before the run. Each `QN.md` holds the
hypothesis, the predictions if it is true and if it is false, the design, one primary metric, the
guardrails and the decision rule. Results and the decision are appended after the run, under a
`## Result` heading, and the pre-registered text above it is not edited afterwards. Status of each
question is in the table.

| id | question | status | depends on |
|---|---|---|---|
| [Q6](Q6.md) | Does the calibration survive contact with live sites? | result recorded (`results/q6-live-paired.md`): direction supported, calibration awaits labels | nothing |
| [Q1](Q1.md) | What signal should trigger deliberation? | pre-registered | Q6 traces, step labels |
| [Q3](Q3.md) | Is a small calibrated verifier better than an LLM judge? | pre-registered | Q6 traces, trajectory labels |
| [Q2](Q2.md) | Should the check sit before the action or after it? | pre-registered | Q6 task set, arm configs |
| [Q5](Q5.md) | Which decisions belong to Jev at all (extraction as selection)? | pre-registered | Q6 read tasks |
| [Q4](Q4.md) | Per-step arbitration or per-subgoal delegation? | pre-registered | Q6 multistep tasks, arm configs |
| [Q8](Q8.md) | Consent: completion under policy versus false pauses | pre-registered | Q6 consent tasks |
| [Q7](Q7.md) | Should the arbiter learn? | pre-registered | Q6 sites, memory mechanism |
| [Q9](Q9.md) | Does System 2 directing System 1 beat S1 from the front? Four arms incl. a guarded S2 baseline | result recorded (`results/q9-live-dev.md`): delegation falsified on cost with the first build; guarded matches on completions at lowest cost; coherent build measured (`results/q9c-coherent-delegation.md`): falsification stands, executor reach rate 5 of 30 | guarded arm, call economy, ledger semantics, delegation and evidence workflows |
| [Q10](Q10.md) | Does the arbiter's calibration transfer from DOM menus to accessibility-tree menus (native computer use through Cua Driver)? | result recorded (`results/q10-native-dev.md`): calibration transfers (target AUROC 0.90), dual loses to guarded on verified completions through verifier refusals and one repeated-sequence task; not adopted, verifier and tasks fixed first; Q10b (`results/q10b-native-dev.md`): after the fixes dual is within one task of guarded (13 vs 15 of 18), residual gap is one repeated-sequence task; native stays experimental | native dev split (`evals/native/tasks/dev.yaml`, oracles 7/7), Q1 labelling protocol |
| [Q11](Q11.md) | Does declaring the contract the guard already enforces (requirements, refusal budget, authorized scope) and naming what a refused done is missing let the same driver finish with fewer model requests and no loss of verified completions? | result recorded (`results/q11-live-dev.md`): falsified, requests +21% per task with completions unchanged; the burden is a step-cap grind on clicks that change nothing where the silent arm died on an `evaluate` pause, plus narrative dones refused by the claim check; not adopted, Q12 (effect receipts) next, then a narrower declaration as Q11b | guarded arm, `jevdual.contract`, live-dev consent tasks |
| [Q12](Q12.md) | Does a receipt for every action (the effect diff in the driver's five words, delivered to the driver and the verifier) cost the driver less per unit of progress than browser-use's "Clicked"? | result recorded (`results/q12-live-dev.md`): H0(b), receipts cut repeated no-op clicks 18% and raw requests 5% but not requests per unit of progress; the driver escapes to `evaluate` sooner and fails the same way; receipts kept, not adopted as a burden claim; P2 input fix then Q12b | `jevdual.receipts`, `guarded_receipts` arm, `evals.burden`, terminal modes |
| [Q15](Q15.md) | Does a footwork session run alongside a person without taking their work, input or focus (another app, another document of the same process, another tab of the same window, a foreground step beside an idle or moving person, a conflicting edit)? | result recorded: 15 of 15 cases passed with every check (C3 attributed rerun 3 of 3); adopted, `background_only` is the operator default and `foreground_permitted` holds the front 36 to 65 ms only after 3 s idle | `jevdual.posture`, `jevdual.ax`, `jevdual.coexist` |

## Ground rules

- **Pre-register in the repo.** Hypothesis, predictions, design, primary metric, guardrails and
  decision rule are committed before the run. The heldout protocol carries over: the live heldout
  split (`live-heldout.yaml`) is never debugged; a heldout miss becomes a new dev task.
- **Paired, repeated, with intervals.** Every arm runs the same tasks; three repeats per arm;
  paired bootstrap 95% intervals on the difference between arms. Samples under 30 tasks report
  counts, not percentages.
- **One primary metric per experiment, guardrails fixed.** Guardrails everywhere: crashes, false
  completions (a claimed done whose predicate fails), completion under policy (consent tasks),
  and estimated cost. An arm that wins its primary metric and breaches a guardrail is not adopted.
- **Cost is part of the result.** Report failures prevented per dollar and per LLM call, never pass
  rate alone. Jev calls are counted at the SDK boundary and include escalation and verification.
- **Live sites are flaky.** A task that no arm passes in any repeat is marked `unreachable` in the
  result and excluded from the paired comparison, with the count reported. Predicates are chosen
  to be stable (canonical URLs, years, names), never counts or prices that drift.
- **Labels are the expensive input.** Q1 and Q3 need human labels (roughly 300 S1 steps as right
  or wrong, roughly 200 trajectories as complete or not). Model calls for the whole program are
  under a few dollars at contributor rates; the binding cost is labelling time.

## Prerequisites, by dependency

1. **Live task set** (Q6's instrument, everyone's prerequisite). `evals/tasks/live-dev.yaml` and
   `live-heldout.yaml`: public pages with stable facts and practice sites built for automation
   (saucedemo.com, the-internet.herokuapp.com, httpbin.org). Machine-checkable predicates; URL
   checkpoints for multistep tasks (`checkpoints:` on the task, all must be visited); tags
   `multistep` and `consent` mark the subsets Q4 and Q8 need. No real messages are sent and no
   real orders placed: the consent-gated tasks submit to practice endpoints that discard input.
2. **Step and trajectory labels** drawn from Q6 traces, including S1-only's confident wrong dones.
3. **Metrics module**: reliability diagrams and expected calibration error for Choice probabilities;
   AUROC and meta-d′ for escalation signals; false-accept and false-reject rates for verifiers;
   completion under policy and false-pause rate; cost per prevented failure.
4. **Arm configurations**: arbiter rule subsets, verifier variant, delegation prompt on or off,
   memory on or off, as named configs so an experiment is a config and not a code branch.

## How to proceed from each result

Supported: the mechanism moves into the default configuration, the README gets the number and its
results file, and the next experiment starts from that baseline. Falsified: the simpler mechanism
stays and the hypothesis is recorded as falsified with the data. Inconclusive at the pre-set
sample: widen the sample once; if still inconclusive, park it rather than rerun until it passes.
Every adoption reruns the frozen local heldout and the live heldout once, so the heldout numbers in
the README always reflect the current default.

## Sources

Consensus search, 2026-09-21. Arbitration: [A1] When to Plan: Learning to Select Between Reactive
Control and Deliberative Planning; [A4] Fast, slow, and metacognitive thinking in AI; [A5]
Measuring the metacognition of AI; [A8] Thinking Fast and Slow in Human and Machine Intelligence;
[A12]/[A14] Combining Fast and Slow Thinking for Human-like and Efficient Decisions/Navigation in
Constrained Environments; [A17] Deep Search with Hierarchical Meta-Cognitive Monitoring.
Verification: [V1] The Art of Building Verifiers for Computer Use Agents; [V5] Let's Think in Two
Steps: Mitigating Agreement Bias in MLLMs; [V7] ST-WebAgentBench; [V11] WebCanvas; [V14] An
Illusion of Progress? Assessing the Current State of Web Agents; [V15] Done, But Not Sure:
Disentangling World Completion from Self-Termination; [V17] When Is Enough Not Enough? Illusory
Completion in Search Agents; [V20] Don't Act Blindly: Robust GUI Automation via Action-Effect
Verification. Hierarchy: [H1] Why Do LLM-based Web Agents Fail? A Hierarchical Planning
Perspective; [H2] Enhancing Web Agents with a Hierarchical Memory Tree; [H5] HiPER; [H7] From
Grounding to Planning: Benchmarking Bottlenecks in Web Agents; [H8] Think Big, Search Small; [H12]
HiMAC. Links are in the session record; each is on consensus.app under its title.
