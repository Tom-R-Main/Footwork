# SubQ versus Jev development comparison and selectable System One

## SC1 · prediction · 2026-10-15 17:12
Hypothesis: SubQ Snap can preserve completion safety on Footwork's exposed development fixtures while offering competitive client wall latency against the application's pinned Jev model.
Test: committed SC1 experiment; same captured state/questions and unchanged production replay for 36 completion, 40 risk and 30 action cases, three replays/provider, randomized paired order within completion-first role blocks. Fresh pooled clients, concurrency one, no retries or dispatch; one durable aggregate $1 cap including failures and diagnostics.
Predicts: Snap has no negative completion case accepted in any replay, all negative cases have three valid measurements, and positive completion coverage is no worse than Jev. Common-success paired latency is no slower overall.
Against: any unsupported completion is accepted, negative evidence is incomplete, positive coverage falls, or latency is slower. Semantic and final guarded acceptance are reported separately and do not imply cross-provider calibration.
Refs: docs/experiments/SC1-subq-jev-dev.md; evals/d1_compare.py; docs/notebook/2026-10-15-subq-snap.md

## SC2 · prediction · 2026-10-15 17:12
Hypothesis: the current injected SystemOneClient seam supports an explicit Jev/SubQ backend switch without changing existing policy, completion floors or default Jev behavior.
Test: implement a validated SDK-compatible Snap adapter and shared provider/model configuration; propagate selected model, credentials and pricing through real runtime factories. Offline mock transport and caller tests check exact wire path, singleton choice handling with deterministic provenance, native probability/confidence preservation, malformed output refusals, defaults, model mismatch and configuration errors. Run the relevant policy/verifier/session/evidence/eval tests; independent implementation review.
Predicts: default callers retain pinned Jev and existing safety checks; explicit Snap selection reaches the same policy/verifier/evidence behavior through the adapter, and bad/unsupported output cannot enter admission.
Against: a factory remains pinned to a different model, defaults change, confidence is invented for model-generated choices, unsupported output passes, costs retain the wrong provider rate, or backend switching bypasses a safety floor.
Refs: python/jevdual/policy.py:SystemOneClient; python/jevdual/verify.py; python/jevdual/evidence.py

## SC-U1 · update · 2026-10-15 17:29
Resolves: SC2 = held
Observed: explicit provider/model configuration now reaches active action, verifier, effect-risk and delegated-evidence factories; sessions freeze selection and old sessions stay pinned Jev. Strict native Snap validation, exact wire path and singleton provenance tests pass. Full deterministic source suite passes 1675 with 21 skips and 17 deselections, plus 15 comparison tests; Ruff/notebook checks pass. Independent implementation review found no blockers; summed timing conformance was repaired before measurement. Native accounting now counts proposal and verification tokens per run instead of proposals alone.
Inferred: the existing injected client contract supports explicit experimental backend selection without a broad response-type refactor or changed admission/authority logic. Transport interoperability does not establish semantic interchangeability.
Next: retain Jev defaults and document the measured safety failure before recommending any backend change.
Refs: 29f93cb; f3d7d5e; bd34247; tests/test_system1.py; tests/test_session_scenarios.py; tests/test_native_runner.py; output/sc1-source-tests.txt

## SC-U2 · update · 2026-10-15 17:29
Resolves: SC1 = failed
Observed: all 636 planned attempts completed with valid responses and reported usage at bd34247; final negative completion acceptance is Jev0/18 versus Snap4/18, semantic0/18 versus8/18. Positive final all-three coverage is5/18 versus7/18. Risk all-three correctness is33/40 versus37/40; action exact pairs28/30 versus29/30, with zero incorrect admitted pairs for either. Median paired Snap/Jev request ratios are1.35 completion,1.12 risk and1.70 actions. Aggregate input-price estimate is0.025787922 dollars; largest reconstructed pre-dispatch reservation0.053348710 dollars, cap1dollar. Independent raw-response replay, request/manifest hashes, counts, metrics and both ledgers agree; no retries, extra probes or heldout runs.
Inferred: greater positive coverage and stronger action/risk dev scores do not compensate for unsupported completions. Snap is slower by paired request latency in each role in this implementation. The smoke result did not predict hard-case safety; the full registered hypothesis fails.
Next: close SC1 unchanged; no prompt/threshold tuning or further paid requests in this package.
Refs: results/sc1-20261015T172206/report.md; results/sc1-20261015T172206/audit.json; results/sc1-budget.json

## SC-S1 · summary · 2026-10-15 17:29
Established: selectable experimental System1 backend is implemented with Jev default, selected model/rate propagation, persistent session selection, strict Snap validation and unchanged policy authority. Complete matched dev evidence and independent audit establish the observed Snap completion failure and slower paired client latency. Cost is below the approved1dollar cap; credential-bearing process exited with no persisted key.
Uncertain: calibrated provider thresholds, heldout/live task performance, image value and future provider revisions remain unmeasured. Risk label/prompt scope and singleton transport differences constrain interpretation. Three repeats on exposed fixtures do not prove general safety.
Decision: retain Jev for normal completion and as runtime default. Keep Snap opt-in for research; any action/risk adoption requires separate role-specific validation. Package closed with no further calls.
Refs: docs/experiments/SC1-subq-jev-dev.md; results/sc1-20261015T172206/report.md; python/jevdual/system1.py; README.md
