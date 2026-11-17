# Qualified native fullscreen control

## FS1 · prediction · 2026-11-17 03:54
Hypothesis: the existing public CLI cannot offer the bound window's unlabeled fullscreen button because the SDK omits subrole and projection prunes unnamed buttons; a separately qualified exact-window identity can expose only this button without weakening menu ambiguity or unnamed exclusions.
Test: first reproduce with public start/look/do against the existing simulated Mac, retaining red output on SSD before source changes. Then qualify exact PID/window, full-screen button subrole/enabled/AXPress/state, persist identity across CLI calls, requalify immediately before dispatch, and read back the actual transition. Exercise wrong PID/window, missing/duplicate/disabled/replaced control, state changes, token/index reassignment, no-transition acknowledgements and other unnamed controls.
Predicts: public CLI reproduction fails before repair with no available fullscreen candidate; after repair only the uniquely qualified fullscreen button is offered, mutations refuse without input, and only an observed state transition confirms effect. Duplicate menu paths still refuse.
Against: reproduction already offers a safe target; a mutation dispatches; ordinary unnamed controls become clickable; or acknowledgement without transition is reported confirmed.
Refs: /Volumes/External SSD/demoApps/demo/films/showcase-2026-11-17/workspace/capture/window-prep-002/CONTROL-DIAGNOSIS.md; tests/test_session_scenarios.py; tests/fixtures/native_world.py

## FS2 · update · 2026-11-17 03:55
Observed: the real public start/look scenario fails at saved candidate981 missing (KeyError), while unnamed close/minimize are excluded; no source changed before this reproduction.
Next: implement qualified window identity and failure/readback discrimination.
Refs: /Volumes/External SSD/Footwork-native-fullscreen-evidence-20261117/red.txt; tests/test_session_scenarios.py::test_native_fullscreen_public_cli_offers_only_qualified_window_control

## FS3 · prediction · 2026-11-17 03:55
Hypothesis: CoreFoundation CFHash of the same window/button AX references is stable across separate observer processes, allowing a bounded additional replacement discriminator alongside exact PID/window/subrole and current state. It is not treated as a globally unique identity or sufficient dispatch authority.
Test: two independent read-only AX queries of the already authorized exact Chrome PID82786/window635573, compare window/button hashes without input; fixture mutations test changed hashes and same-process AX reference equality immediately before dispatch.
Predicts: the two independent observations agree on hashes and state, and replaced references are refused at dispatch.
Against: hashes vary across observers of the unchanged control, or a replaced reference passes fresh qualification.

## FS4 · update · 2026-11-17 04:03
Observed: two independent read-only installed-runtime AX observers returned matching window/button hashes and fullscreen state. The focused fullscreen scenarios initially exposed a second defect: generic visual diff confirmed a changed button label even when exact fullscreen readback failed. The new scoped receipt rule keeps that case unverifiable. All 28 fullscreen scenarios now pass, including replacement with unchanged hash during foreground preparation; the six affected native/session/menu test files pass 571 tests. The reproduction fixture's recorded Calculator PID was corrected to its simulated PID77, and qualification deliberately uses the complete native title-bar census rather than requiring a complete SDK page tree.
Inferred: the projection mechanism is reproduced and repaired in fixtures; CFHash agreement is bounded to two reads of this unchanged window, not a uniqueness guarantee. No fullscreen input or live qualification occurred.
Resolves: FS1 = held; FS3 = held
Next: independent Sol and Opus input-control reviews, then reviewed integration and installed byte/discovery qualification; live preparation remains held until installed receipt.
Refs: /Volumes/External SSD/Footwork-native-fullscreen-evidence-20261117/red.txt; /Volumes/External SSD/Footwork-native-fullscreen-evidence-20261117/readonly-hash-stability.json; /Volumes/External SSD/Footwork-native-fullscreen-evidence-20261117/focused.txt; docs/native-fullscreen.md
