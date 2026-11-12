# Native receipt representation and outside effects

## NRA1 · prediction · 2026-11-10 19:13
Hypothesis: ordinary native multiline whole-field AX serialization can differ from copied content only in its internal LF pattern, so treating that difference as established partial text delivery can encourage an unsafe retype. A native menu action can also change clipboard/disk/another window without visible change.
Test: public CLI simulated-Mac cases for LF-only multiline differences and an Edit Copy action that increments a simulated clipboard generation while the menu remains unchanged; targeted receipt cases preserve non-LF mismatch, trailing-whitespace legacy behavior, strict selected ranges, browser and secret semantics, refusal and qualified outside readback.
Predicts: only LF-pattern ambiguity in complete untruncated ordinary native multiline replacements becomes unverifiable with independent-readback/no-retype guidance, never confirmed; non-LF mismatch remains partial. Native menu no-visible-change becomes unverifiable, while no-send and qualified proof remain intact.
Against: whitespace or values are normalized, selected-range/browser/secret behavior changes, true text mismatch confirms, menu no-send becomes unknown, or an unchanged menu is treated as proof that Copy failed.
Refs: output/suno-20261110/lyrics-copy-result.json; output/suno-20261110/lyrics-full-value-comparison.json

## NRA2 · update · 2026-11-10 19:17
Resolves: NRA1 = held
Observed: two public CLI cases failed before the source change; four cases now pass, preserving strict range LF mismatch as partial and keeping actual non-LF mismatch partial. The simulated Copy oracle advances while its UI stays unchanged and its new receipt is unverifiable. 465 affected source tests pass. Boundary cases preserve browser/single-line/secret/truncation/trailing-whitespace rules and qualified outside-effect/no-send handling.
Inferred: representational LF ambiguity and an unchanged UI are insufficient to call native text delivery partial or a menu invocation ineffective; independent readback is needed before retrying.
Next: freeze classification-only source and hand off to the parent; do not alter historical receipts.
Refs: results/native-receipt-ambiguities-20261110/report.md; results/native-receipt-ambiguities-20261110/baseline.txt; results/native-receipt-ambiguities-20261110/focused.txt

## NRA3 · summary · 2026-11-10 19:17
Established: exact non-LF equality with internal LF serialization differences downgrades ordinary native multiline replacement to unverifiable with no-retype guidance; native menu no-visible-change likewise remains unverifiable. Neither change confirms input or normalizes values.
Uncertain: no new independent readback mechanism or live UI verification was added. Actual DOM/server acceptance and whole-song completion remain external to these classifications.
Decision: hand off the small receipt package using unchanged SDK bytes; preserve previous receipts and all selected-range guards.
Refs: results/native-receipt-ambiguities-20261110/report.md
