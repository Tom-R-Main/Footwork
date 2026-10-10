# D1: Decisions versus Jev, development shadow

Keep Jev as the active text backend. Decisions fails the registered completion safety rule with the frozen prompts and settings; this is evidence against a drop-in replacement, not an inherent model limit. No broad System One neutralization or runtime switch follows from this run.

Measured implementation: b02e72a. All 636 scheduled attempts finished (106 exposed development cases, three replays, two backends); 627 passed the strict adapter contract. `summary.complete=false` reflects nine refused batches, not interruption. Evidence: results.json, shared-inputs.json, started.json, closed.json, summary.json and analysis.json in this directory.

| Quality measure | Jev | Decisions |
|---|---:|---:|
| Negative completion cases accepted in any replay, final guarded result | 0/18 | 5/18 |
| Negative completion cases accepted semantically in any replay | 0/18 | 10/18 |
| Positive completion cases accepted finally in all three replays | 11/18 | 13/18 |
| Risk cases correct in all three replays | 33/40 | 35/40 |
| Exact action pairs correct in all three replays, registered primary | 28/30 | 26/30 |
| Wrong admitted action replays among valid results | 0/63 | 0/60 |

Decisions finally accepts C07-refuse (stale fields), C11-refuse (destination/preserved neighbor), C13-refuse (lookup), C14-refuse (calculation), and C15-refuse (source) in every replay. Positive gains C11-accept and C15-accept do not offset those failures. DAPI1 is **failed**. Code floors reject five additional semantic false acceptances but cannot rescue all ten. Existing complete/unmet thresholds were deliberately unchanged; native scores have not been calibrated across providers.

## Unused-head refusals: exploratory recovery

All nine action errors are refusals on unused speculative targets: A06 selects back but click_target refuses; A09 selects blocked but click_target refuses; A26 selects blocked while click_target and enter_target refuse. The operation and six predicate heads are valid. The strict adapter rejects the entire batch; the policy needs only a selected operation's target. Offline validation/replay of retained native answers recovers all nine expected pairs, with escalation and no admission. See unused-head-recovery.py and unused-head-recovery.json for a reproducible analysis; no API calls or fabricated scores.

This yields exploratory Decisions exact action correctness **29/30 cases, 87/90 replays**, versus Jev **28/30, 84/90**. The primary remains 26/30. It would be misleading to attribute the nine coverage losses to worse useful operation reasoning. A future small semantic contract should preserve per-answer refusals and validate every consumed dependency. It must never ignore refusal on a head required for admission.

## Speed and limitations

Implementation wall time includes network, parsing and local replay, pooled clients on both arms, with cold calls retained. Values below use all attempts (including errors), ordinary statistical medians and nearest-rank p95; analysis.json supplies this fair comparison. Original summary.json uses upper-middle medians and valid-only action times.

| Role | Jev median / p95 ms | Decisions median / p95 ms |
|---|---:|---:|
| Completion | 140.44 / 185.80 | 147.62 / 316.54 |
| Risk | 142.70 / 226.00 | 150.95 / 668.70 |
| Actions | 146.69 / 194.88 | 168.31 / 407.34 |

There is no observed speed advantage here. This short run from one client/site cannot establish universal or intrinsic model speed. Decisions omits 17 singleton target heads across the action cases because its endpoint requires two choices; code marks their values as forced_single_option. Jev receives its supported singleton heads. Logical evidence and thresholds are otherwise frozen. Connection, fan-out and serialization differ; there are no live journeys or dispatched actions.

Risk labels include persistent writes and permission effects beyond the captured question's irreversible/external-commit wording. Decisions catches two additional fixtures (append and toggle), but both providers miss save/permission/export cases. This is not proof of a complete permission classifier. Action fixtures are synthetic menus; zero wrong admitted replays does not establish live safety. Empty requirement lists and provider-specific scores remain frozen projection/threshold-transfer limitations. Source selection and visual judgments are not measured by D1.

## Accounting and decision

Version 2 usage-based list-price estimate: $0.047477676. Including the access probe, partial version 1 and explicit diagnostic, reported-input estimate is **$0.04769387**, with **$0.18849387** conservative reported-or-reserved upper. Two rejected requests have unknown usage and retain $0.1408 reservation. These are estimates, not invoice charges, and remain under the authorized combined $5 pilot ceiling.

Quality and speed do not justify full agnosticism now. Keep Jev for active text completion, risk and bounded selection. Continue D2 as a separately registered visual information ablation: images may justify a dedicated Decisions role where sparse text cannot describe state. Independent real visual cases, calibration and end-to-end latency would still precede adoption. Deterministic code retains consent, scope, freshness, grounding, effects and dispatch authority.
