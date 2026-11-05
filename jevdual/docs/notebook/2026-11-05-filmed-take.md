# Filmed take readiness: DemoGeek iteration 6 end to end

## FT1 · prediction · 2026-11-05 17:57
Question: why does Footwork's observation of DemoGeek's empty Message textarea show the value 'Describe what to film…'?
Hypothesis: CUA's tree builder substitutes AXPlaceholderValue when AXValue is empty (cua-driver platform-macos ax/tree.rs:500-503), and Footwork takes that as the field's value; a direct read showed AXValue '' and AXPlaceholderValue 'Describe what to film…'.
Alternatives: Chrome reports the placeholder as AXValue itself.
Test: a bridge-level test with a fake AX layer where a web text field's AXValue is empty and its placeholder equals the reported value; then a live footwork look on the prototype.
Predicts: today the observation carries the placeholder as the value; after a narrow correction (web text fields only, where AXValue is empty and AXPlaceholderValue equals the reported value) the value is empty, a field with real text keeps it, and a live look shows Message with no value.
Against: the live look still shows the placeholder after the correction, or a field holding real text loses it.
Refs: design/iteration-6/take/TAKE.md (demogeek cbeafd6)

## FT2 · prediction · 2026-11-05 17:57
Question: can footwork's existing click, hover and type routes be filmed with the real pointer travelling to each target like a person's, without changing how the action is delivered?
Hypothesis: a filmed pointer mode that, before delivery, plays CUA's planned path from the pointer's current location to the target's centre (refused when every arc fallback leaves the window or enters the keep-out), keeps the pointer where the gesture ended, and ends the take on idle movement or contention, gives the film a continuous pointer while the AX press, hover and type_text delivery stay as today.
Test: scenario tests with the poster and clock replaced: approach then delivery for click, hover and type; a path that would cross the keep-out takes a lower arc or is refused before anything is posted; park to the rest position and to a viewport point; a pointer moved between commands ends the take and every later filmed route refuses. Live: the rehearsal take on the prototype, recorded by OBS.
Predicts: offline each case as stated; live, every TAKE.md step completes, the pointer never enters the keep-out after step 5, and the recording shows continuous motion between targets with no jump.
Against: delivery changes (a click lands as a pointer click rather than an AX press), a path enters the keep-out, or the film shows the pointer jump.
Refs: FT1; 2026-11-05-pointer-drag.md PDU3; demogeek design/pointer-motion/PLAN.md v13

## FTU1 · update · 2026-11-05 17:58
Resolves: FT1 = held
Observed: tests/test_placeholder_value.py failed on its own commit (value 'Describe what to film…') and passes on 92d69aa, where a filled web field keeps 'Relay demo'. Live footwork look on the prototype with the change lists [5] textbox 'Message' with no value; before it showed = 'Describe what to film…'.
Next: FT2, the filmed pointer mode.

## FT3 · prediction · 2026-11-05 18:58
Question: why is take 8's recording black for its whole 55 s, when take 7's capture of the same window showed it?
Hypothesis: take 8 retargeted the existing "Footwork take window" input with SetInputSettings (take 7 created it), and the screen_capture source kept a dead window stream; the settings readback reads settings, not frames, so setup passed.
Alternatives: the capture needs time after a new window appears; Screen Recording permission for OBS lapsed.
Test: the runner removes and recreates its own input on every take and, before StartRecord, requires a GetSourceScreenshot of the input that is not uniformly black (retrying for 5 s); then recorded take 9.
Predicts: take 9 passes the frame check on the first or second try and its recording shows the window throughout (freezedetect finds no freeze longer than the scripted waits).
Against: the frame check fails on a recreated input (then it is timing or permission), or take 9 is black although the check passed.
Refs: results/demogeek-take-20261105-7, -8 (obs-settings.json, take.jsonl)

## FTU2 · update · 2026-11-05 19:00
Resolves: FT3 = failed
Observed: take 9's runner recreated the input under a new name (7355e51; OBS kept the old one listed after RemoveInput) and its frame check refused after 21 black screenshots. A fresh full-display capture then returned "Failed to render screenshot" (702) for 6 s, as did the user's own window source. OBS's screen capture is down for the whole process, not for one retargeted input. Take 8 itself was right on the Footwork side: 14 gestures all arrived, 70–109 samples over 0.77–1.06 s each, max gap 13.7 ms, the take never ended (results/demogeek-take-20261105-8/session/session.json).
Next: recover OBS capture (probably a restart, the user's call), then a recorded take with the frame check; ask the OBS_MCP thread why a closed captured window wedges capture.
