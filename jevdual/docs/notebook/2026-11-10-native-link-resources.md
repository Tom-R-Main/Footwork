# Native link resource identity

## LRI1 · prediction · 2026-11-10 18:28
Hypothesis: independently read complete AXURL values distinguish same-title native links safely when every member of their pre-pruning semantic group has qualified URL evidence; incomplete groups and duplicate URLs remain ambiguous.
Test: public CLI simulated-Mac scenarios for two same-title distinct resources, unreadable/pruned peers, same-URL duplicates, row reorder and same-ID URL replacement, including changes during the final live reobservation. Add focused AX URL/projection/persistence tests and run affected native/session/menu/CLI/authorization contracts.
Predicts: both distinct links survive pruning and a freshly selected numeric ID dispatches only its observed resource. Unknown or duplicate identity, URL replacement or qualification loss refuses before input; browser href semantics and row buttons do not acquire native resource authority.
Against: a clipped, relative, malformed or unreadable URL clears ambiguity; an unreadable hidden peer is ignored; a changed URL or reordered ID clicks a different resource; existing non-link targeting changes.
Refs: output/suno-20261110/generated-link-identities.json; docs/notebook/2026-11-10-suno-end-to-end.md

## LRI2 · update · 2026-11-10 18:35
Resolves: LRI1 = held
Observed: both public CLI positive cases failed before the source change; the final group has 14 passing scenarios, and 615 affected source/contract tests pass. Distinct complete resource URLs survive pruning and target the expected backing resource. Missing peer evidence, duplicate URLs, saved-ID replacement/reorder and final revalidation changes send no click. An intermediate focused run caught unnecessary null URL fields on ordinary button action metadata; those fields are now added only for qualified native links.
Inferred: complete independently read URL evidence can refine a link's semantic identity without inheriting that authority into row buttons or ordinary browser hrefs. All-or-none observed peer qualification must precede pruning.
Next: freeze source and hand off to the parent for live qualification; keep later focus-preparation changes separate.
Refs: results/native-link-resources-20261110/report.md; results/native-link-resources-20261110/baseline.txt; results/native-link-resources-20261110/focused.txt

## LRI3 · summary · 2026-11-10 18:35
Established: exact bound AXLink URL/name reads qualify complete HTTP(S) resources across observed semantic peer groups, persist resource provenance and refuse URL changes, lost qualification or duplicate resources before input.
Uncertain: no worker live actions or probes occurred. SDK observation coverage can remain incomplete; qualification does not prove absence of unobserved page controls or whole-song task completion. Row buttons retain their existing identity requirements.
Decision: freeze the native link resource package using the unchanged focus1 SDK overlay; no native rebuild or global installation.
Refs: results/native-link-resources-20261110/report.md
