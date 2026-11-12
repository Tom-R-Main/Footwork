# Explicit foreground web selection edits

## WSR1 · prediction · 2026-11-10 18:15
Hypothesis: an explicit UTF-16 selected-range edit can safely insert before Suno's AX terminal LF without normalizing it, by requiring exact independent selection and selected-text evidence and preserving the complete raw prefix and suffix in the expected postcondition.
Test: public CLI simulated-Mac scenarios for zero-length insertion before LF, nonempty selection including supplementary Unicode, stale selection/value/identity, unreadable selected text, invalid or unsupported options before binding, uncertain single dispatch, and exact full-value receipts including truncation and trailing-whitespace differences.
Predicts: only an already matching range and selected text permit one positively paced focus-guarded text call; no Select All is sent; exact full readback can confirm preserved prefix/suffix while contradictory, unavailable or changed-identity readback cannot confirm. Existing whole-field replacement still refuses an unselected LF.
Against: a stale or partial selection dispatches, a UTF-16 split is accepted, an uncertain input retries, a preview/whitespace-equivalent mismatch confirms, or the ordinary full-field guard changes.
Refs: docs/notebook/2026-11-10-suno-end-to-end.md; output/suno-20261110/lyrics-parameterized-observation.json

## WSR2 · update · 2026-11-10 18:25
Resolves: WSR1 = held
Observed: 14 public CLI cases failed against the absent option before implementation. The final selected-range group has 35 passing scenarios, and the affected session/native/AX/CLI/discovery/authorization/evidence/operations and CUA contract set has 542 passing tests. Exact LF-sensitive mismatches, surrogate splits, selection changes, unknown delivery, later readback changes and SDK fallback do not confirm. The existing whole-field LF guard remains in place.
Inferred: a separate selected-range contract can preserve the LF without claiming it is removable. Fresh exact-value provenance is required because the SDK fallback may trim whitespace even when its string appears to corroborate an earlier read.
Next: freeze source for the parent agent's live selection-edit qualification; keep renderer/server acceptance separate from AX postcondition evidence.
Refs: results/foreground-web-selection-20261110/report.md; results/foreground-web-selection-20261110/baseline.txt; results/foreground-web-selection-20261110/focused.txt

## WSR3 · summary · 2026-11-10 18:25
Established: explicit bounded UTF-16 selection edits require exact raw value/range/selected-text agreement, preserve prefix and suffix, send one paced focus-guarded type call, and compare complete exact readback rather than preview or stripped text. Durable replay includes the range and keeps foreground-readback provenance distinct from AX insertion acknowledgement.
Uncertain: no worker live input occurred. SDK focus and field selection checks are sequential, not an atomic renderer transaction; divergence stays unverified without retry. The existing completion consumer does not adopt the new durable field-readback source as whole-task completion proof.
Decision: hand off the frozen source with the existing project-local focus1 overlay; no native rebuild or global install required.
Refs: results/foreground-web-selection-20261110/report.md
