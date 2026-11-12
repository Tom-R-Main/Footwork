# Named unframed peers in the opaque census

## ONF1 · prediction · 2026-11-10 20:54
Hypothesis: the observed unframed named Hide Tips peer can be independently identified for duplicate-ID census by one exact readable native name under the bound AXWindow, without granting it input authority or dropping unknown peers.
Test: public CLI simulated-Mac scenario with two framed unnamed controls and one named unframed peer; require complete bounded direct native role/name traversal, unique AX object, matching PID/window/document chain and normal DOM/name proof. Cover missing/duplicate/unreadable/name/document drift and traversal bounds; retain named-peer and opaque drift regressions.
Predicts: current opaque census refuses all controls for missing peer frame; a separate exact-name census lookup qualifies framed opaque controls while omitting the unframed peer from actions. Any failed or ambiguous lookup still blocks opaque qualification.
Against: lookup needs positional guessing or hidden-peer omission, makes the unframed peer actionable, bypasses unknown names/children/documents, or lets prior identity drift send input.
Refs: output/suno-20261110/opaque-live-diagnosis.json; results/opaque-named-peer-census-20261110/

## ONF2 · update · 2026-11-10 20:58
Resolves: ONF1 = held
Observed: the public red scenario withheld framed opaque controls when a named peer lacked an SDK frame. The exact-name census lookup now preserves opaque qualification while omitting the independently resolved unframed peer from action candidates. Nineteen new public/direct AX checks and all 594 affected tests pass. Missing/duplicate/unreadable/over-bound lookup, final name changes, document drift and duplicate IDs still refuse. Known unsupported/no-value attributes are explicit negative evidence; other read errors remain unknown. Ruff and notebook validation pass.
Next: freeze source for parent-owned live qualification, then run complete default offline regression because native projection/census behavior changed.
Refs: results/opaque-named-peer-census-20261110/baseline.txt; results/opaque-named-peer-census-20261110/scenarios.txt; results/opaque-named-peer-census-20261110/focused.txt

## ONF3 · prediction · 2026-11-10 20:58
Hypothesis: the census-only exact-name lookup preserves existing projection, identity, authorization and default routes outside the missing-frame named-peer case.
Test: full default offline pytest on frozen source with the existing focus1 overlay, no live/browser opt-ins and production module hashes before/after.
Predicts: full suite passes with normal opt-in skips and unchanged measured source.
Against: existing named controls, native actions or unrelated routes regress, or measured source changes during the run.
Refs: results/opaque-named-peer-census-20261110/focused.txt

## ONF4 · update · 2026-11-10 21:02
Resolves: ONF3 = held
Observed: complete default offline pytest on frozen ca4e7dc passed 3339 tests with 62 opt-in skips in 222.32 seconds, exit 0. Production module hashes match before and after; no live/browser opt-ins were active.
Next: hand off completed regression evidence; parent owns live editor qualification.
Refs: results/opaque-named-peer-census-20261110/full-default.json; results/opaque-named-peer-census-20261110/full-default.txt

## ONF5 · summary · 2026-11-10 21:02
Established: a named unframed SDK peer can supply census-only duplicate-ID evidence through a complete bounded exact-name native lookup, existing independent PID/window/document proof and final unchanged name; it remains absent from action candidates. Nineteen new guards, 594 affected tests and all 3339 default tests pass with 62 opt-in skips.
Uncertain: the worker performed no live qualification of the new resolver. Unknown native branches, missing/duplicate names, conflicting IDs/documents and traversal limits still refuse; no fallback silently ignores the peer.
Decision: close this repair at ca4e7dc with separate full regression evidence; retain exact-window, action, named-control and opaque drift guards. No SDK build, installation or UI input.
Refs: results/opaque-named-peer-census-20261110/report.md
