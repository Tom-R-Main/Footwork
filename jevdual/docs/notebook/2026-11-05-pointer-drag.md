# Pointer drag: a human-paced real-pointer drag on macOS

## PD1 · prediction · 2026-11-05 16:49
Question: can Footwork perform a fluid real-pointer drag that the target app receives as one continuous drag ending at the drop point, using CUA's planned path?
Hypothesis: posting a tagged left-button down, then the planner's samples as LeftMouseDragged events at their scheduled times, then a left-button up, all through kCGHIDEventTap at absolute points and with no warp, moves the visible pointer and delivers a normal drag; an AppKit-hosted Tk window receives it as press, a dense motion stream with the button held, and release at the drop point.
Alternatives: HID-posted drag events without a warp do not move the cursor (CUA mouse.rs says this of MouseMoved), so the app sees press and release only; or the window server coalesces the stream so the app sees a handful of motion events.
Test: offline, a fake poster and clock check event order, the press dwell, duplicate dropping, the gap rule, and that every exit (finish, cancel, stall, contention, exception) posts exactly one release. Live, scripts/p1_live_drag.py drags a 40 pt square in a Tk fixture across about 400 pt and drags a Tk slider, with the idle guard; the fixture logs every event with root coordinates to JSON.
Predicts: the square's final centre is within 2 pt of the drop point; the fixture logs at least 60 B1-motion events for a roughly 1 s drag, with no gap between consecutive motion events above 50 ms; the logged positions stay within 2 pt of the posted points; the slider ends at the value under the drop point; CGEventGetLocation equals the drop point afterwards; the left button is up afterwards.
Against: the square does not move or jumps straight to the end (few motion events), logged positions diverge from the posted path, or the button is still down after any exit.
Refs: demogeek design/pointer-motion/PLAN.md v13 §8 (drag deferred); 2026-11-05-pointer-motion-p0.md PMU3
