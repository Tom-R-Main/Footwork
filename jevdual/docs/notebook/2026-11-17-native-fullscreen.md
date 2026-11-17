# Qualified native fullscreen control

## FS1 · prediction · 2026-11-17 03:54
Hypothesis: the existing public CLI cannot offer the bound window's unlabeled fullscreen button because the SDK omits subrole and projection prunes unnamed buttons; a separately qualified exact-window identity can expose only this button without weakening menu ambiguity or unnamed exclusions.
Test: first reproduce with public start/look/do against the existing simulated Mac, retaining red output on SSD before source changes. Then qualify exact PID/window, full-screen button subrole/enabled/AXPress/state, persist identity across CLI calls, requalify immediately before dispatch, and read back the actual transition. Exercise wrong PID/window, missing/duplicate/disabled/replaced control, state changes, token/index reassignment, no-transition acknowledgements and other unnamed controls.
Predicts: public CLI reproduction fails before repair with no available fullscreen candidate; after repair only the uniquely qualified fullscreen button is offered, mutations refuse without input, and only an observed state transition confirms effect. Duplicate menu paths still refuse.
Against: reproduction already offers a safe target; a mutation dispatches; ordinary unnamed controls become clickable; or acknowledgement without transition is reported confirmed.
Refs: /Volumes/External SSD/demoApps/demo/films/showcase-2026-11-17/workspace/capture/window-prep-002/CONTROL-DIAGNOSIS.md; tests/test_session_scenarios.py; tests/fixtures/native_world.py
