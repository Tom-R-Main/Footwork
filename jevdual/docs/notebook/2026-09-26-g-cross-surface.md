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

## G5 · prediction · 2026-09-26 16:45
Revises: G4
Hypothesis: as G4, on an unlocked screen: with the bridge's save readback on the trajectory line, the verifier accepts the saved append Q17 refused six times.
Test: `evals.native.runner --task textedit-append-line --arm dual --arm guarded --repeats 3` on main (0d3907a), screen unlocked, owner at the Mac.
Predicts: at least 5 of 6 verified (predicate passed, done accepted), each run with one save step whose receipt is `confirmed`.
Against: fewer than 5 of 6 verified with the save receipt confirmed (the verifier ignores the readback), or a confirmed save receipt on a run whose predicate fails.
Refs: results/q17-native-dev.md; python/jevdual/native.py (save_readback)

## U27 · update · 2026-09-26 16:49
Resolves: G5 = held
Observed: `results/g5-native-append` on 6918473, screen unlocked: 6 of 6 verified and accepted (dual 3, guarded 3), 3 to 7 steps; Q17 had 0 of 6 on the same task and arms. Every accepted done follows a save receipt `confirmed` ("saved: ... holds the window's text exactly"), with "was saved" unmet at 0.09 to 0.26 when accepted. In 4 of 6 runs the first Command-S read `partial` (the file differed from the window) and a File > Save one step later read `confirmed`; one dual run's verifier rejected (saved unmet 0.90) one step after a confirmed save and accepted the next done.
Inferred: the readback is the evidence the verifier lacked. Whether those first Command-S saves failed or the readback at 0.5 s read the disk before TextEdit's write is not separable from these traces; if the latter, the `partial` was false and cost a step each time.
Changes: the bridge polls the file for up to 3 s before calling a save `partial`.
Next: none for G; a later native run shows whether first saves still read partial.

## G6 · prediction · 2026-09-26 16:49
Question: were G5's first-Command-S `partial` receipts failed saves or early reads?
Hypothesis: early reads: TextEdit finishes writing after 0.5 s, so polling for up to 3 s turns them into `confirmed`.
Alternatives: the first Command-S genuinely does not save (the chord reaches TextEdit before it is key), so polling changes nothing.
Test: the same six runs on 1a31586.
Predicts: the first Command-S receipt `confirmed` in at least 5 of 6 runs, and no File > Save step after it.
Against: `partial` on the first Command-S in 3 or more of 6 (failed saves, not early reads).

## U28 · update · 2026-09-26 16:53
Resolves: G6 = failed
Observed: `results/g6-native-append` on 809e346 (polling up to 3 s): 6 of 6 verified again; the first Command-S read `partial` in 4 of 6 runs even after polling, and each time the File > Save that followed read `confirmed`.
Inferred: not early reads: those Command-S presses did not save (alternative: the chord arrives before TextEdit's window is key), and the `partial` receipts were true. The receipt is what sent the driver to File > Save; without it, Q17's drivers pressed Command-S again and again against a verifier that could not tell.
Changes: none to the receipt. The unreliable chord is the Driver's foreground hotkey route; routing a save chord through the menu is a candidate, not done.
Next: none.

## U33 · update · 2026-09-27 15:48
Observed: the secondary audit: `check-file` proved only that some line equals the carried value, not the location, the earlier content, or a single insertion; and `start` kept an older session's `carries.json` in the same directory.
Inferred: a transfer that duplicated the value on a retry, or replaced the document's first line, would have read confirmed; a stale carried value could be used as if read in the new session.
Changes: `footwork snapshot-file PATH` records the destination before the work; `check-file ... --appended` requires the file to be the snapshot, one line break, and the value once at the end, and names the failure otherwise (content not preserved, inserted N times, not the value's own line, other text added). `start` clears carries and snapshots. The pilot uses both. Tests: `test_the_append_oracle_names_what_went_wrong`, `test_the_workflow_oracle_through_the_real_commands`, `test_a_new_session_does_not_inherit_an_old_sessions_carries`.
Next: the pilot on the new oracle when the desktop is available; then Q13's other four oracles.

## G7 · prediction · 2026-09-27 15:58
Question: does the whole browser → TextEdit → saved-file path satisfy the workflow oracle, and does it report a duplicate as a failure?
Hypothesis: the clean run passes every criterion: the source value is the first book's price read from books.toscrape.com; the destination is the fresh file; its earlier line is kept; the value is appended exactly once; `check-file --appended` confirms. The duplicate run's receipts confirm both appends (each did what it said) and the oracle fails with "inserted 2 times".
Alternatives: the save needs File > Save (recorded as recovery, not success on the first try); the Driver's AX value around the stripped trailing newline makes the second append land on the same line, so the duplicate reads "not the value's own line" instead.
Test: `scripts/pilot_cross_surface.sh clean`, then `duplicate`, once each, on this commit; evidence under results/g-pilot-*.
Predicts: clean: oracle exit 0, "confirmed: line 2"; duplicate: oracle exit 6, "inserted 2 times"; every append receipt confirmed.
Against: the clean run's oracle fails while its receipts said confirmed, or the duplicate run's oracle confirms.

## U34 · update · 2026-09-27 16:00
Observed: the first G7 clean run (`results/g-pilot-20260927-155808-clean`): `footwork start` on TextEdit failed with the Driver's "AX tree walk for pid=38619 timed out after 20 s" (TextEdit also had long.txt and note.txt open), printed as a Python traceback, and left no session; the pilot carried on, the append failed on the missing session, and the oracle's "failed: ... does not hold the value as a line" was reported with exit 0 (tee's code).
Inferred: not a test of the workflow. Two defects: an unhandled Driver error in a session command is a traceback, not a named stop (the milestone breached on another path), and the pilot script did not stop at a failed step or report its real exit code.
Changes: every footwork command that raises outside its own handling stops with "stopped: <reason>: <message>", exit 7, logged to the session (`test_a_driver_error_at_start_stops_with_its_reason_not_a_traceback`); the pilot runs under pipefail and stops at the first failed step, writing outcome.txt.
Next: G7 again.

## U35 · update · 2026-09-27 16:05
Resolves: G7 = held
Observed: clean (`results/g-pilot-20260927-160046-clean`): the source value was the first book's price read from books.toscrape.com (£51.77); the destination was the fresh file (snapshot 32 characters); the append's receipt confirmed; the first Command-S was refused as `human_active` (input 1.1 s earlier) and File > Save then confirmed ("holds the window's text exactly (38 characters)"), recorded in recovery.txt; `check-file --appended` confirmed line 2 with the earlier line kept and one insertion. Duplicate (`results/g-pilot-20260927-160203-duplicate`): both appends confirmed, the window holding the value twice; every save attempt for 60 s yielded to the person (input 0.0 to 0.3 s before each); the file on disk nonetheless held both lines, and the oracle failed with "the value was inserted 2 times" (exit 6). An earlier duplicate run (both saves yielded, nothing on disk) failed the oracle on "no value added".
Inferred: the complete path meets the workflow oracle on a clean run, and the oracle reports a duplicate for what it is. The duplicate reached the disk through TextEdit's own autosave, not a save the harness made, which the oracle cannot tell apart and need not: it judges the file. The clean pass needed a recovery (File > Save after a yield); that is recorded, not hidden.
Next: the fresh verifier evaluation (Q16c), then resource-bound grants.

## U36 · update · 2026-09-27 23:19
Observed: Q13's plan requires its five oracles to pass before any measured claim. One exists (`check_append`, G7). Built: the fixture server records every GET's query (both fixture forms submit by GET) and serves `.txt` files as downloads; `evals.crossapp` has three more oracles, each reading end state only: `one_submission` (exactly one request to a path with the field exactly equal to the carried value), `downloaded_and_opened` (exactly one byte-identical download, and it is the open document), `renamed` (the carried name, unchanged bytes, the old name gone). Tests: `tests/test_crossapp.py`.
Inferred: four of five oracle shapes exist and are exact; none is yet validated on a scripted live solve, which is the plan's gate.
Next: after Q18 frees the desktop, a scripted solve of each task shape against its oracle (the plan's oracle stage), then the grants live pilot; Q13 pre-registration only after both.

## G8 · prediction · 2026-09-28 00:54
Question: do Q13's oracles confirm a correct scripted solve and name the fault in a wrong one, on the real apps?
Hypothesis: each oracle reads the end state the real apps leave exactly: (2) Calculator → fixture form: one GET to /confirm.html with message=624; the wrong solve submits twice ("2 submissions"); (3) TextEdit → fixture search: one GET with q="quarterly report"; the wrong solve searches twice; (4) download → open in TextEdit: one byte-identical file in ~/Downloads that TextEdit has open; the wrong solve downloads again ("2 identical copies"); (5) order page → Finder rename: the file named B-20260921.txt with its bytes unchanged; the wrong solve renames to a truncated name. Task 1 is G7's.
Alternatives: Chrome encodes the query differently from the carried text (e.g. "+" for spaces is fine, but a trailing newline from TextEdit's line is not); Chrome's download of a .txt names it differently or opens it inline; TextEdit reports the opened path through a symlink (/private/var vs /var), so the path comparison fails on a correct solve.
Test: `scripts/q13_oracle_stage.py`, once; reads through footwork sessions (carried values), effects through footwork where it has a route (typing, clicking, navigating) and by script where it has none (opening a file in TextEdit, a Finder rename, which the plan found unreachable).
Predicts: 4 of 4 correct solves confirmed and 4 of 4 wrong solves failed with the named fault.
Against: any correct solve failed by its oracle, or any wrong solve confirmed.
