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
