# Native receipt representation and outside effects

## NRA1 · prediction · 2026-11-10 19:13
Hypothesis: ordinary native multiline whole-field AX serialization can differ from copied content only in its internal LF pattern, so treating that difference as established partial text delivery can encourage an unsafe retype. A native menu action can also change clipboard/disk/another window without visible change.
Test: public CLI simulated-Mac cases for LF-only multiline differences and an Edit Copy action that increments a simulated clipboard generation while the menu remains unchanged; targeted receipt cases preserve non-LF mismatch, trailing-whitespace legacy behavior, strict selected ranges, browser and secret semantics, refusal and qualified outside readback.
Predicts: only LF-pattern ambiguity in complete untruncated ordinary native multiline replacements becomes unverifiable with independent-readback/no-retype guidance, never confirmed; non-LF mismatch remains partial. Native menu no-visible-change becomes unverifiable, while no-send and qualified proof remain intact.
Against: whitespace or values are normalized, selected-range/browser/secret behavior changes, true text mismatch confirms, menu no-send becomes unknown, or an unchanged menu is treated as proof that Copy failed.
Refs: output/suno-20261110/lyrics-copy-result.json; output/suno-20261110/lyrics-full-value-comparison.json
