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

## U22 · update · 2026-09-26 14:17
Resolves: G1 = failed
Observed: `scripts/pilot_cross_surface.sh` on c81c0e5 exited 0. `read --match` carried '£51.77' from books.toscrape.com; `check-file` printed "confirmed: line 2 of ~/footwork-pilot/transfer.txt equals @price ..." and the file's bytes are "Price carried from the browser:\n£51.77". Two receipts were false in the cautious direction: the append read `partial` ("not its earlier value plus the insertion") while the bridge's exact readback said confirmed; Command-S read `suspected_noop` on a document that was saved. The browser observation's title was 'Dune (novel) - Wikipedia' over the books page's elements.
Inferred: the transfer works and the oracle is exact; the session's receipts are not. The append's before-value came from the Driver, which strips the file's trailing newline, so the expected value was missing the line break the bridge correctly did not add (alternative (b) in part). The save has no readback at all: the session compared element lists, and a save changes none. The stale title is the Driver's (`get_browser_state` page title lags a navigation); upstream, pinned, recorded, not patched.
Changes: a native append is also confirmed as earlier text + one line break + insertion (the bridge's own separator rule); after Command-S or File > Save on a native window, the receipt reads the window's AXDocument path and compares the file on disk with the text area's exact value (`save_readback`): confirmed only when they are equal, partial with the first differing character otherwise, unverifiable when the window names no file.
Next: G2 after Q17 frees the desktop.

## G2 · prediction · 2026-09-26 14:17
Revises: G1
Hypothesis: with the two receipt fixes, the same pilot gives true receipts at every step.
Test: `scripts/pilot_cross_surface.sh` once more, on the fix.
Predicts: the append receipt `confirmed`; the Command-S receipt `confirmed` with "saved: ~/footwork-pilot/transfer.txt holds the window's text exactly"; check-file confirmed on line 2.
Against: either receipt other than confirmed on a file whose bytes are right, or a confirmed save receipt when check-file fails.
Refs: python/jevdual/session.py (save_readback); tests/test_session.py
