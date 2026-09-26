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

## U23 · update · 2026-09-26 14:43
Resolves: G2 = inconclusive
Observed: the rerun on 46dad49 exited 6. TextEdit still had the G1 document open, and the script had rewritten the file under it, so the window held G1's text; the append added a second '£51.77' and its receipt read `confirmed` (the window's field did hold earlier text, a line break and the value). Command-S did not save; the save receipt read `partial (save not confirmed: .../transfer.txt differs from the window's text at character 32)`, and check-file failed ("no line ... holds '£51.77'"). No dialog was left open; the document was closed without saving.
Inferred: the test did not run under its own conditions (a stale open document), so G2's confirmations are untested. What it did show is the property that matters more: when the save failed, the save receipt and the oracle both said so, and neither receipt overstated. Before the fix, the same save was reported "suspected no-op" whether or not the file was written.
Changes: the pilot writes a fresh file per run.
Next: G3.

## G3 · prediction · 2026-09-26 14:43
Revises: G2
Hypothesis: on a fresh file, every receipt in the transfer is true and confirmed.
Test: `scripts/pilot_cross_surface.sh` (fresh file per run), once.
Predicts: append `confirmed`; Command-S `confirmed` ("saved: ... holds the window's text exactly"); check-file confirmed on line 2; exit 0.
Against: any receipt other than confirmed while the file's bytes are right; or a confirmed save while check-file fails.

## U24 · update · 2026-09-26 14:44
Resolves: G3 = held
Observed: the pilot on a fresh file exited 0: the read carried '£51.77' from books.toscrape.com; the append's receipt read `confirmed` ("now holds 'Price carried from the browser:\n£51.77'"); Command-S's read `confirmed (saved: ~/footwork-pilot/transfer-144337.txt holds the window's text exactly (38 characters))`; check-file confirmed line 2 with the chain back to the page.
Inferred: one browser-to-TextEdit transfer runs with provenance and an exact oracle, and across G1 to G3 no receipt overstated: two understated (fixed), and when the save failed the receipt and the oracle both said so.
Next: summary.

## S5 · summary · 2026-09-26 14:44
Established: a value read in one session carries its source (surface, app, URL, element or matched line, step) to another session's `do append`, and `check-file` proves the saved line byte for byte. A native save is now confirmed only by reading the file the window names against the window's text; a native append follows the bridge's line-break rule instead of the Driver's stripped value. The browser observation's title can lag a navigation (the Driver's `get_browser_state`, upstream).
Uncertain: Q13's five tasks have no oracles yet; only one transfer shape (browser to TextEdit, plain text) was driven, once confirmed; a rich-text document, a second app, and the reverse direction are untested.
Decision: G's pilot closes; Q13 is pre-registered only once five oracles pass, per the plan. A single session holding both bridges (`switch_surface`) is not built: two sessions and a carry kept each session's identity guarantee from package A intact, and the pilot did not need more.
Refs: python/jevdual/carry.py; python/jevdual/session.py (save_readback); scripts/pilot_cross_surface.sh

## G4 · prediction · 2026-09-26 14:47
Question: does the save readback, moved into the native bridge, let the verifier accept the saved append Q17 refused six times?
Hypothesis: the verifier held "The document was saved" at 0.42 to 0.55 unmet because the save's receipt was `unverifiable` (a chord changes nothing a window diff sees); with the bridge reading the file against the window after Command-S or File > Save, the trajectory line reads `confirmed` with "saved: ... holds the window's text exactly", and the requirement is met.
Alternatives: the verifier judges "saved" from the window title or the page, not the trajectory line, so it stays uncertain.
Test: `evals.native.runner --task textedit-append-line --arm dual --arm guarded --repeats 3` on this build (Q17's task, same arms).
Predicts: 6 of 6 verified (predicate passed, done accepted), each with one save step; Q17 had 0 of 6 with two to four save attempts each.
Against: fewer than 5 of 6 verified, or a save receipt `confirmed` on a run whose predicate fails.
Refs: python/jevdual/native.py (save_readback); results/q17-native-dev.md

## U25 · update · 2026-09-26 15:32
Resolves: G4 = inconclusive
Observed: `results/g4-native-append` (6 runs, dual and guarded): every run hit the 25-step budget with no append; from step 3 on, actions were answered "pid ... has no AX window" or "not in the process's current AXWindows". `CGSSessionCopyCurrentDictionary` reports the screen locked since 1790448343, about 20 minutes into the run; Q17, an hour earlier on the same task, reached the append in every run.
Inferred: the test never ran under its conditions (accessibility cannot reach windows on a locked screen), so the save readback is untested on the native agent path. The harness failed its own milestone here: it kept deciding and pressing keys for 25 steps against a screen nobody could see, instead of stopping and saying why.
Changes: `jevdual.posture.screen_locked`; the posture refuses every delivery with `screen_locked` and the native bridge refuses to observe on a locked screen (a typed `NativeBridgeError`), so a run ends at its first observation with the reason. The suite pins the screen unlocked (`tests/conftest.py`); with the real screen locked, 35 tests had failed, which is how the dependence was found.
Next: G4 again once the screen is unlocked.
