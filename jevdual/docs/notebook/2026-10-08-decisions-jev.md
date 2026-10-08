# Decisions and Jev: resumption

## DAPI1 · prediction · 2026-10-08 14:21
Question: can Decisions replace a narrow System One judgment role without changing Footwork's deterministic authority?
Hypothesis: native predicates and choice distributions make a portable semantic-judge contract practical; completion coverage can improve over Jev on exposed development cases without additional evidence. Confidence is provider-specific and cannot be assumed equivalent.
Test: D1, a paired shadow comparison of completion, destructive-effect judgment and bounded action selection, three replays per backend on already exposed or authored development cases; preserve code floors and thresholds and separately report semantic and final decisions. No action dispatch or sealed adoption runs.
Predicts: the candidate improves positive completion acceptance in at least one category, accepts no negative in any replay, and supports strict finite answer/distribution validation. Deterministic evidence defects remain visible with unchanged projections.
Against: any negative acceptance, no positive coverage improvement, provider confidence being substituted without provenance, or any apparent gain requiring changed evidence, settings or floors.
Refs: docs/experiments/D1-decisions-jev.md; https://developers.openai.com/api/docs/guides/decisions; docs/notebook/2026-09-30-responses-jev.md

## S-DRESUME · summary · 2026-10-08 14:21
Established: The user supplied the public-beta Decisions guide; fetched official documentation confirms POST /v1/decisions with gpt-6-luna, predicates, discrete choice distributions, ordered score expectations, independent question batching, and input-only pricing. Existing OpenAI and TypeSafe credentials remain available without exposure or writes. Restored the pinned project environment entirely from the local uv cache; no network dependency fetch. Runtime base is e3b7b08. The installed OpenAI SDK is 2.26.0, below the documented Decisions SDK minimum, so use the documented HTTP endpoint rather than change dependency pins.
Uncertain: This account's usable access, response usage fields, model behavior, calibration and real latency remain unmeasured. The guide's speed claim compares Responses, not Jev. Speculative target heads are conditionally defined and must not be described as independent without checking their wording.
Decision: Resume the authorized development-only comparison with existing keys and a combined $5 ceiling. Keep runtime backend selection unchanged; build a strict shadow adapter, retain native provider scores, and refuse malformed/refused results. Record all failed attempts and costs. No new key, install, activation or heldout run.
Refs: docs/experiments/D1-decisions-jev.md; https://developers.openai.com/api/docs/guides/decisions; https://docs.typesafe.ai/models

## S-DCONTRACT · summary · 2026-10-08 14:35
Established: The optional Decisions HTTP adapter has provider-neutral typed native outputs and no TypeSafe imports. The D1 eval-only bridge preserves native probabilities/confidence/model/unknown usage, captures existing request builders and replays unchanged verifier/arbiter code. Host offline checks passed; preflight prepares every registered development case and rejects oversized requests. Refusals, invalid distributions and failed requests cannot establish safety. Fan-out reservations are conservative per question and retained when billing usage is unknown.
Uncertain: DAPI1 is still open; offline mocks do not establish usable account access, native response shape, semantic accuracy, billing behavior or latency. Risk fixture labels extend beyond the current destructive question's scope. Fixed-threshold transfer is diagnostic only.
Decision: Commit the implementation and preflight before a one-shot contract probe, then run paired shadows only if usable access and the native contract are established. Include probe accounting in the same $5 ceiling; no retries or dispatch. Keep active Jev routes unchanged.
Refs: results/d1-offline-20261008; tests/test_decisions.py; tests/test_d1_compare.py; tests/test_notebook.py; evals/d1_compare.py; docs/experiments/D1-decisions-jev.md

## U-DACCESS · update · 2026-10-08 14:35
Observed: The one-shot authenticated contract probe on 5962744 returned the requested predicate, choice and score answers, correct synthetic labels, native model identity and input-token usage. The output contract validated; all request accounting was retained and redaction changed no files. No Jev request or paired comparison has run yet.
Inferred: Public documentation and usable access now satisfy the deferral's entry condition. This simple request is access/contract proof, not model quality or comparative latency evidence.
Next: Commit the probe receipt, then measure the frozen paired development comparison from a clean checkout, including the probe's input-only charge in the same $5 ceiling. DAPI1 remains open.
Refs: results/d1-contract-20261008; docs/experiments/D1-decisions-jev.md; 5962744
