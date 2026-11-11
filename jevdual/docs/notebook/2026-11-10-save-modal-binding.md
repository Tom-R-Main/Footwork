# Native save modal binding

## SMB1 · exploratory · 2026-11-10 19:30
Question: which exact process/window owns the observed Save sheet, and why did the existing foreground hotkey guard refuse the project-folder navigation chord before application input?
Test: inspect the recorded refusal and pinned guard source, then bounded read-only SDK/AX observations of Chrome PID24992 bound parent306787, its own focused/main window and focused field ancestry, plus the observed sheet ancestry/window references. Inspect a remote save-panel process only if an actual AX relationship from this owned sheet proves association. No input, focus, activation, pointer motion or Save.
Refs: output/suno-20261110/song-b-save-go-folder.txt; output/suno-20261110/song-b-export-save-wait.txt

## SMB2 · update · 2026-11-10 19:34
Observed: Chrome PID24992 reports AXFocusedWindow as AXSheet325928 and AXMainWindow306787. The Save sheet has direct AXParent/AXWindow association to306787; filename/Save controls descend through an AXSplitGroup to that sheet. SDK list_windows and get_window_state bind325928 successfully, while Footwork ax.window_element fails because it searches only top-level AXWindows. All observed AX PIDs were24992; no remote process was queried. The recorded wrapper code is foreground_intent_refused; the raw SDK record was discarded.
Inferred: the old parent binding cannot satisfy exact focused-window guards while its modal sheet is key. Rebinding the proven modal is supported by SDK observation but needs a bounded exact-CGID sheet resolver for Footwork direct AX raise/resolve; parent-to-child implicit routing would weaken the guard and is not justified. SDK foreground activation of325928 remains untested by this read-only package.
Next: parent decides the bounded resolver repair and performs any future input on a frozen source. Read-only slot released and drivers shut down.
Refs: output/suno-20261110/save-modal-observation.json; output/suno-20261110/modal-bindability.json

## SMB3 · summary · 2026-11-10 19:34
Established: exact owned Save modal is PID24992/CGWindow325928, associated directly with parent306787; SDK observes it as a separate Save window. Existing direct AX window resolution misses this AXSheet. No input/focus/activation/Save occurred and no remote save-service association was found.
Uncertain: raw SDK refusal code is unavailable from the lossy recorded exception; exact-window-unverified is a source-backed inference. SDK foreground activation and actual folder navigation were not exercised. No file was saved.
Decision: retain exact-window enforcement, propose explicit modal rebinding plus bounded exact sheet resolution, and leave project-only destination selection to the parent after qualification.
Refs: output/suno-20261110/save-modal-observation.json; output/suno-20261110/modal-bindability.json

## SMB4 · prediction · 2026-11-10 19:36
Hypothesis: exact requested modal CGWindow resolution can include a bounded AXSheet descendant of its same-PID top-level AXWindow with independently proven direct parent/window association, without accepting the parent as the modal or weakening exact-key checks.
Test: public CLI simulated-Mac Save-session binding with SDK exact-foreground verification followed by real direct-AX resolver/raise behavior; AX regressions for top-window preservation, wrong PID, unrelated/ambiguous sheets, bounded traversal, association loss and non-key modal refusal.
Predicts: a correctly rebound already-key Save sheet permits the existing guarded folder-navigation hotkey through one input call; parent bindings and unrelated/non-key/unproven/over-bound sheets send no hotkey. Already-key sheets need no AXRaise/AXMain writes; ordinary window raising is unchanged.
Against: requested parent resolves its modal, an unproven sheet dispatches, another process supplies ownership, a non-key sheet or ambiguity is ignored, or failed input retries.
Refs: output/suno-20261110/modal-bindability.json; output/suno-20261110/save-modal-observation.json

## SMB5 · update · 2026-11-10 19:45
Resolves: SMB4 = held
Observed: the corrected public CLI fixture fails only the intended modal hotkey against the unmodified prior ax.py snapshot (one failure/five guard passes), and all six cases pass with the repair. The first fixture attempt had an inconsistent SDK PID and is retained separately rather than called a valid reproducer. 595 affected tests pass, including exact parent preservation, ownership/association/ambiguity/bounds and non-key-sheet guards. AXMain/AXRaise are not written for an already-key sheet; _front_and_key remains unchanged.
Next: freeze source immediately for the parent live test, then run the full default offline suite on that commit and finish the evidence report.
Refs: results/save-modal-binding-20261110/baseline.txt; results/save-modal-binding-20261110/focused.txt

## SMB6 · prediction · 2026-11-10 19:45
Hypothesis: adding exact same-PID modal sheet resolution leaves ordinary window lookup, authorization and non-modal routes unchanged across the default offline suite.
Test: run the complete default pytest suite using the existing focus1 overlay, with no live/browser opt-ins, on the frozen repair commit.
Predicts: the complete default suite passes with the normal opt-in skips; no ordinary-window regression or accidental native UI execution appears.
Against: a previously passing non-modal test fails due to the new resolver or its ownership/read bounds.
Refs: results/save-modal-binding-20261110/focused.txt

## SMB7 · exploratory · 2026-11-10 19:46
Question: which exact same-PID window now owns the GoToWindow field after the successfully delivered folder-navigation chord, and how is it associated with Save325928?
Test: bounded read-only observation of bound Save325928, application focused/key window and observed GoToWindow field67 direct parent/window links; SDK bindability only for a proven associated window. No input, focus/activation or Save. Full default offline validation of frozen16a67f4 continues with production source unchanged.
Refs: output/suno-20261110/save-b-set-filename.txt
