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
