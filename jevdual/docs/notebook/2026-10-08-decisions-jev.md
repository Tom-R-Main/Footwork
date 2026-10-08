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

## U-DREJECTED · update · 2026-10-08 14:39
Observed: D1 stopped after seven attempts on 6a9a67b. Both providers returned all three R16 risk replays; the first A12 candidate request was rejected with HTTP 400. Its 11 questions include singleton target choices. The transport discarded the HTTP error body, so no constraint is established. The runner's account/model/route stop label is overbroad. All attempts and uncertain-cost reservations remain recorded. Independent review also found alternate-admission target scoring and coarse abstention reporting limitations, plus asymmetric connection pooling.
Inferred: Access was established by the probe and risk calls; this rejection may concern the request contract. The partial run cannot establish comparative performance or safety. DAPI1 remains open.
Next: Preserve this version, commit bounded diagnosis before another request, capture sanitized provider metadata, and repair effective-target reporting before any new action comparison. A new measured version gets a fresh run directory, never a resumed original run.
Refs: results/d1-dev-20261008; evals/d1_compare.py; python/jevdual/decisions.py; 6a9a67b

## DAPI2 · prediction · 2026-10-08 14:39
Question: does the rejected A12 request expose a specific Decisions contract restriction?
Hypothesis: the rejection concerns the question batch or choice shape, rather than lack of usable account access, because the probe and predicate requests already succeeded.
Test: one explicit diagnostic dispatch of the frozen A12 request after committing sanitized HTTP error capture; inspect only bounded provider type/code/param/message with key redaction. If a specific restriction is returned, isolate that restriction with a tiny synthetic contract request in a separately committed version. No automatic retry or resumed comparison; all charges/reservations include prior attempts under $5.
Predicts: rejection metadata identifies a question/batch contract constraint that can be represented as an explicit adapter capability limit.
Against: no reproducing rejection, an opaque error, or evidence of an account/access error instead.
Refs: docs/experiments/D1-decisions-jev.md; results/d1-dev-20261008

## U-DLIMIT · update · 2026-10-08 14:44
Resolves: DAPI2 = held
Observed: The explicit A12 diagnostic on a8c5b94 returned invalid_request_error / array_below_min_length at questions[2].choices, saying the minimum is two and the supplied length is one. The frozen request hash matched version 1. Both rejected attempts retain uncertain-cost reservations; the total upper includes every earlier call. No full comparison result exists.
Inferred: This is a specific adapter capability restriction. A singleton target is conditionally fixed by code, not a model uncertainty judgment. The user explicitly prioritizes visual value and makes quality and speed determinants of broader agnosticism.
Next: Mark forced singleton bindings separately from native answers, pool both clients, repair effective alternate scoring and separate exact pair correctness from safe abstention. Commit tests before a fresh version 2 run. Evaluate visual added information separately and let results determine architecture breadth.
Refs: results/d1-diagnostic-20261008; docs/experiments/D1-decisions-jev.md; a8c5b94

## S-DV2 · summary · 2026-10-08 14:46
Established: Version 2 handles the diagnosed singleton restriction by marking code-forced heads, preserving actual native receipts and hashing actual wire requests. Both clients pool connections. Exact selected pairs, coarse abstention and effective admitted alternate targets are reported separately. Host checks passed, and preflight retains the original logical evidence/question projection hash. The API error diagnosis is established, not inferred from status alone.
Uncertain: DAPI1 remains open. Quality, speed, calibration and visual added value remain unmeasured beyond the simple contract and partial risk calls. Synthetic menu cases do not establish live execution performance. Earlier failed calls retain uncertain-cost upper bounds.
Decision: Commit the repaired harness and run a fresh version 2 paired comparison including all prior budget upper bounds. Quality and speed determine whether broader interchangeability is worth implementing; visual utility can be a dedicated role. No active backend migration is justified yet.
Refs: results/d1-v2-offline-20261008; results/d1-diagnostic-20261008; docs/experiments/D1-decisions-jev.md; tests/test_decisions.py; tests/test_d1_compare.py

## DAPI3 · prediction · 2026-10-08 14:49
Question: does a screenshot add usable visual judgment value where the same text projection is underdetermined?
Hypothesis: Decisions can judge common visual-only UI states from pixels more confidently and correctly than either provider can from identical sparse text; useful visual placement need not imply full agnosticism.
Test: D2, twelve synthetic paired-state fixtures and four text/image arms, three replays, frozen predicate bands, native receipts, no dispatch. Keep image metadata free of expected answers and report the information difference explicitly.
Predicts: combined images improve all-three confident correctness over Decisions text-only, with no confident true on a negative fixture.
Against: no confident-correct coverage gain, any confident false positive, or apparent gains caused by labels leaking through filenames/metadata rather than visual evidence.
Refs: docs/experiments/D2-decisions-visual.md

## U-DTEXT · update · 2026-10-08 14:58
Resolves: DAPI1 = failed
Observed: All 636 scheduled version 2 attempts finished; nine unused-target refusals make 627 strictly valid batches. Decisions accepts five negative completion cases finally and ten semantically; Jev accepts none. Decisions gains two positive completion cases and two risk fixtures, with the registered scope caveat. Median and tail latency show no speed advantage. Independent offline analysis recovers all nine unused-head refusals, yielding exploratory action correctness 29/30 versus Jev 28/30; the primary stays 26/30 versus 28/30.
Inferred: Frozen-prompt substitution fails completion safety; this does not establish an inherent model limit. All-or-nothing refusal handling confounds primary action coverage. Quality and speed do not warrant full agnosticism now.
Next: Keep active Jev routes and settings unchanged. Finish separately registered D2, then recommend a dedicated visual role only if evidence supports it. Preserve native refusals per answer in any future consumed-dependency contract.
Refs: results/d1-v2-dev-20261008/report.md; results/d1-v2-dev-20261008/analysis.json; results/d1-v2-dev-20261008/unused-head-recovery.json; docs/experiments/D1-decisions-jev.md; b02e72a

## U-DVISUAL · update · 2026-10-08 15:02
Resolves: DAPI3 = held
Observed: All 144 D2 attempts finished on 84f3fd5. Both image arms are confidently correct on every fixture in all three replays, with no confident true on negative states. Sparse Jev text stays unknown; Decisions text stays unknown or refuses. Combined median/p95 are 170.56/747.53 ms; these exclude screenshot acquisition and do not establish stable real-session speed. All 802 offline tests passed, 26 skipped; Ruff and notebook checks passed.
Inferred: Pixels add usable information in this authored capability ablation; this is not evidence-matched model superiority or independent real-app accuracy. D1 and D2 together support a specialized visual candidate while Jev remains preferred active text judgment. Quality and speed do not warrant broad agnosticism now.
Next: Preserve results and source audit. Collect independent visual cases and capture-to-judgment latency before adoption; keep settings and active factories unchanged.
Refs: results/d2-dev-20261008/report.md; results/d2-dev-20261008/analysis.json; docs/experiments/D2-decisions-visual.md; 84f3fd5

## S-DPACKAGE · summary · 2026-10-08 15:02
Established: Public Decisions access and strict native predicate/choice/score contracts are verified. D1 text substitution fails completion safety; offline per-answer recovery distinguishes unused-head refusal from useful action reasoning. D2 shows image information value in twelve authored UI fixtures. Every attempt, native receipt, failure, usage estimate and uncertain-cost reservation is retained; no keys are exposed.
Uncertain: Independent visual accuracy, calibration, source selection, provider snapshot stability, full live latency and production adoption remain unestablished. Risk question/label mismatch and synthetic action menus limit generalization.
Decision: Keep Jev active for text; qualify Decisions for a dedicated visual validation package. Defer full agnosticism unless role-specific quality and speed earn it. Combined pilot reported-input estimate is $0.051255158 and conservative upper $0.192055158 under the $5 ceiling; no default routing, thresholds, heldout run, push or deployment changed.
Refs: docs/decisions-jev-evaluation.md; results/d1-v2-dev-20261008/report.md; results/d2-dev-20261008/report.md
