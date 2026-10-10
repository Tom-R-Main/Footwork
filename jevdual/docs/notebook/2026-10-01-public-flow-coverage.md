# Public-flow coverage calibration

## PF1 · prediction · 2026-10-01 16:23
Question: why does a successful public-flow packet still leave the first page's served resources and blank-form POST attribution uncertain?
Hypothesis: attaching after the initial navigation omits the first document-load interval, while a method-only POST count cannot distinguish same-origin requests from coincident third-party analytics. A recorded reload plus step-scoped request-method/origin-class counts will close those two reporting gaps without recording URL values.
Alternatives: a warm reload does not represent the actual entry load, or origin class cannot be computed from sanitized request metadata and capture-start scope.
Test: add a recorded baseline reload to the private-config lead-generation scenario, then add a deterministic step traffic summary to the sealed-packet coverage report. Verify with synthetic first-party/third-party GET and POST events, malformed URLs, and a live isolated public rerun. Keep site configuration and packets private.
Predicts: the rerun contains a document request within the explicit reload step, and the blank-submit step reports same-origin versus third-party POST counts without domains, paths or query values. Coverage remains labeled limited when lifecycle orphans remain.
Against: the reload document is absent while the step reports completion, origin-class counts expose URL values, or method counts turn coincident analytics into a claim that the form submitted.
Refs: tools/inspection-experiments/live-public-smoke.mjs; tools/inspection-experiments/coverage.mjs

## PF2 · update · 2026-10-01 16:25
Resolves: PF1 = held
Observed: a sealed private rerun recorded one document request in the explicit reload interval, 1116 events and zero reported gaps. The blank-submit interval contained five request starts, including two external-origin POSTs and zero same-origin POSTs. Private packet inspection identified both POST hosts as analytics endpoints. The coverage audit remains limited by three orphan terminal events and fourteen unclosed requests. The deterministic synthetic coverage test and combined suite passed 64/64.
Inferred: the warm reload fills the target-page document-load evidence gap, while method/origin grouping prevents treating every interval POST as a form submission. It does not recover the cold first navigation, worker targets, or causal request ownership.
Next: use a pre-navigation target attachment only after a separate origin-fence design and test; keep first-load coverage explicitly false until then.
Refs: output/inspection-public-smoke/leadgen-20261001202429-28cb91b3/; tools/inspection-experiments/coverage.test.mjs

## PF3 · summary · 2026-10-01 16:25
Established: the generic public-flow runner now records a warm target-page reload, and offline coverage emits step-scoped request counts by method and origin class without URL values. Live readback, hash verification, 64 focused tests and the notebook check passed.
Uncertain: cold navigation, workers, external form backends and request causality remain outside this calibration. Lifecycle orphans keep the live packet's network assessment limited.
Decision: retain this bounded improvement; do not promote a successful action callback or a POST count to evidence of a submitted form.
Refs: tools/inspection-experiments/live-public-smoke.mjs; tools/inspection-experiments/coverage.mjs
