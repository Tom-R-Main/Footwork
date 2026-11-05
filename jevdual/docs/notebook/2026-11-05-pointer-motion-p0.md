# Pointer motion P0: desktop hover units

## PM1 · prediction · 2026-11-05 16:33
Question: does a desktop-scoped hover land at the element's centre on a Retina display?
Hypothesis: CUA's desktop `move_cursor` takes native `get_desktop_state` screenshot pixels and divides by the main display's backing scale, but the hover route passes the AX frame centre in points, so on a scale-2 display the real pointer lands at half the intended coordinates.
Alternatives: CUA treats desktop coordinates as points on this pinned build, or Footwork already converts before the call.
Test: give the simulated Mac in `tests/fixtures/native_world.py` a backing-scale model that answers `get_screen_size` and lands a desktop `move_cursor` at x/scale, y/scale, as the pinned source does; hover an element with a known frame through NativeBridge in exclusive_desktop on scale 2 and on scale 1.
Predicts: today the scale-2 hover lands at half the element centre and the scale-1 hover at the centre; after a single typed points-to-desktop-pixels conversion, fed by the same `get_screen_size` scale CUA divides by, both land at the centre in points and the call records the scale it used.
Against: the scale-2 hover already lands at the centre before the change, or the fix moves the scale-1 landing point.
Refs: design/pointer-motion/PLAN.md v12 §2, §3.2, §4 test 1 (demogeek); vendor cua-driver platform-macos tools/mod.rs desktop_screenshot_point and tools/move_cursor.rs; native.py hover route
