# Public-flow coverage calibration

## PF1 · prediction · 2026-10-01 16:23
Question: why does a successful public-flow packet still leave the first page's served resources and blank-form POST attribution uncertain?
Hypothesis: attaching after the initial navigation omits the first document-load interval, while a method-only POST count cannot distinguish same-origin requests from coincident third-party analytics. A recorded reload plus step-scoped request-method/origin-class counts will close those two reporting gaps without recording URL values.
Alternatives: a warm reload does not represent the actual entry load, or origin class cannot be computed from sanitized request metadata and capture-start scope.
Test: add a recorded baseline reload to the private-config lead-generation scenario, then add a deterministic step traffic summary to the sealed-packet coverage report. Verify with synthetic first-party/third-party GET and POST events, malformed URLs, and a live isolated public rerun. Keep site configuration and packets private.
Predicts: the rerun contains a document request within the explicit reload step, and the blank-submit step reports same-origin versus third-party POST counts without domains, paths or query values. Coverage remains labeled limited when lifecycle orphans remain.
Against: the reload document is absent while the step reports completion, origin-class counts expose URL values, or method counts turn coincident analytics into a claim that the form submitted.
Refs: tools/inspection-experiments/live-public-smoke.mjs; tools/inspection-experiments/coverage.mjs
