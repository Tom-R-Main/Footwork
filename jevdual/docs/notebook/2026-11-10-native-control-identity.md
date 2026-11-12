# Native DOM control identity

## NCI1 · exploratory · 2026-11-10 18:52
Question: do the exact owned More options controls expose a closest direct AXWebArea ancestor with actual HTTP(S) AXURL suitable for a scoped DOM identifier?
Test: one fresh bound-window SDK observation, independently resolve the two exact named controls by role/frame and walk at most32 direct AXParent links each, recording only role, exact control name/DOM ID and closest WebArea URL; no input or focus writes. SDK WebArea resolution may be recorded separately without inferring direct containment.
Refs: output/suno-20261110/SUN25-hero-peer-probe.json

## NCI2 · update · 2026-11-10 18:54
Observed: both exact owned controls were AXPopUpButton with matching direct names and distinct DOM IDs. Their direct parent chains reached the closest AXWebArea at depths9 and5 with the same actual complete Suno song URL. No SDK ancestry fallback, input or focus write occurred.
Next: qualify scoped identity in source only and test all-peer failure conditions.
Refs: output/suno-20261110/control-document-scope.json

## NCI3 · prediction · 2026-11-10 18:54
Hypothesis: complete native DOM identifiers scoped to the same directly resolved WebArea document can safely distinguish same-label controls when every pre-pruning semantic peer has a unique identifier and independently qualified scope.
Test: public CLI simulated-Mac scenarios for distinct identified controls, hidden unreadable/duplicate-ID/mixed-document peers, changed ID/document and reorder across saved selection or final revalidation; projection, AX decoder, inspect-target and grant-binding regressions.
Predicts: both controls survive pruning and only the freshly selected scoped ID dispatches; partial or duplicate evidence, document changes, ID changes and reorder refuse. No-DOM-ID controls retain existing ambiguity and default nonidentified controls retain behavior.
Against: a partial/clipped identity clears ambiguity, an unknown hidden peer is ignored, a stale ID/document clicks another control, an ordinal grant authorizes a different scoped control, or inspect-target hides identity drift.
Refs: results/native-link-resources-20261110/report.md; output/suno-20261110/control-document-scope.json

## NCI4 · update · 2026-11-10 19:04
Resolves: NCI3 = held
Observed: both public CLI positive cases failed before implementation; 19 scoped-control scenarios and 805 affected source/contract tests now pass. Unknown/duplicate IDs, mixed documents, unequal WebArea ancestors, hidden peers, read limits, saved-choice and final-revalidation drift/reorder send no click. Inspection exposes exact scoped metadata and refuses drift; grants reject peer/document changes and old ordinal refs. New secret-bearing identity metadata redacts and loses qualification.
Inferred: direct scoped DOM identity can distinguish the observed hero/footer controls without inferring a song-row URI or relaxing no-ID controls such as Main Play.
Next: freeze source for parent-owned actual menu qualification; no worker input or further UI probe.
Refs: results/native-control-identity-20261110/report.md; results/native-control-identity-20261110/baseline.txt; results/native-control-identity-20261110/focused.txt

## NCI5 · summary · 2026-11-10 19:04
Established: complete DOM IDs plus closest direct WebArea URL and equality proof refine native button/popup identity only when every observed semantic peer qualifies. Metadata persists, binds grants and inspections, and remains guarded at preflight and final rematching.
Uncertain: AX snapshots can omit unobserved controls, DOM IDs can change on rerender, and no actual menu was clicked by this worker. The bounded read-only probe showed scope availability; synthetic checks do not establish live task completion.
Decision: hand off frozen source with unchanged focus1 native bytes and existing project-local overlay; parent owns live verification.
Refs: results/native-control-identity-20261110/report.md
