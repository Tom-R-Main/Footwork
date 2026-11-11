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
