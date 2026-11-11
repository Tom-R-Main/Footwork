# Native save modal binding

## SMB1 · exploratory · 2026-11-10 19:30
Question: which exact process/window owns the observed Save sheet, and why did the existing foreground hotkey guard refuse the project-folder navigation chord before application input?
Test: inspect the recorded refusal and pinned guard source, then bounded read-only SDK/AX observations of Chrome PID24992 bound parent306787, its own focused/main window and focused field ancestry, plus the observed sheet ancestry/window references. Inspect a remote save-panel process only if an actual AX relationship from this owned sheet proves association. No input, focus, activation, pointer motion or Save.
Refs: output/suno-20261110/song-b-save-go-folder.txt; output/suno-20261110/song-b-export-save-wait.txt
