# Package G: cross-surface pilot, then Q13

Plan: `docs/plans/next-work.md` (G). A session binds exactly one surface (package A), so a handoff is
two sessions and a value carried between them. Built: `jevdual.carry` (a value plus its source),
`footwork read` and `read --match`, `@NAME` in `do type` and `do append` with `--from`, and
`footwork check-file`, the exact saved-file oracle (c81c0e5). The scenarios run on the simulated Mac,
which has no browser tab or text area, so the live pilot is the first test of the whole route.

## G1 · prediction · 2026-09-26 14:10
Question: does one browser-to-TextEdit transfer keep its provenance and end in a file that holds exactly the value read?
Hypothesis: yes, end to end, with every step's receipt true: the read names the page and the match; the append's readback confirms before + separator + value; Command-S's receipt confirms (the title loses its edited mark); check-file confirms line 2 equals the carried text with the full chain.
Alternatives: (a) the save needs the foreground and `foreground_permitted` waits for the person, so the run stalls or reports `human_active`; (b) TextEdit's AXValue read-back and the saved file disagree (the Driver strips trailing whitespace; a rich-text document saves RTF, not the line); (c) the text area's label is not "text area" and the append refuses on the label.
Test: `scripts/pilot_cross_surface.sh`, once, on a plain-text scratch file in ~/footwork-pilot.
Predicts: exit 0 from every command; check-file prints "confirmed: line 2 of ..." naming books.toscrape.com.
Against: check-file fails while the append and save receipts said confirmed (a receipt overstated), or any step needs a retry the receipts did not explain.
Refs: scripts/pilot_cross_surface.sh; python/jevdual/carry.py
