# Opaque native controls

## O1 · prediction · 2026-11-10 20:13
Hypothesis: the native projection omits unnamed editor buttons even when an independently read exact DOM identifier and document scope could distinguish them without inferring purpose.
Test: public CLI simulated-Mac scenarios expose two unnamed AXButton/AXPopUp controls with exact bound role/frame/PID/window, empty native names, DOM identifiers and closest direct WebArea URLs; exercise numeric action, incomplete/duplicate census and identity/name/scope drift before preflight and dispatch. Add direct AX qualification checks and preserve named-control scenarios.
Predicts: the current public route drops the backed controls; a separate bounded opaque census can expose literal identifiers with persisted provenance, retain readable empty-ID peers as omitted, and refuse unreadable/duplicate/drifting evidence without input.
Against: current CLI already exposes those controls, or safe qualification needs positional identity, semantic guesses, unbounded census, or weaker named-control checks.
Refs: output/suno-20261110/editor-affordances-SUN34.json; results/opaque-native-controls-20261110/

## O2 · update · 2026-11-10 20:23
Resolves: O1 = held
Observed: the public CLI baseline projected an unnamed popup with its generic combobox label instead of the actual identifier. The repair exposes only independently backed enabled button/popup controls with literal IDs and persisted opaque provenance. 46 focused opaque scenarios/AX/inspection checks and 516 affected tests pass, including preflight/final identity drift, named/disabled duplicate-ID peers, unreadable census, readable absent-ID peers and opaque-to-named provenance changes. Ruff and notebook checks pass.
Inferred: projection can expose observed backed controls without asserting their purpose. A bounded direct same-PID parent chain must reach the exact bound window through the actual closest WebArea; unsupported or incomplete backing remains unavailable.
Next: freeze source for parent-owned fresh observation/inspection and run the complete default offline suite separately.
Refs: results/opaque-native-controls-20261110/baseline.txt; results/opaque-native-controls-20261110/scenarios.txt; results/opaque-native-controls-20261110/focused.txt

## O3 · prediction · 2026-11-10 20:23
Hypothesis: the separate opaque-control census leaves existing named controls, grants and default routes unchanged.
Test: complete default offline pytest suite on the frozen source with the focus1 overlay and no live/browser opt-ins; hash all affected production modules before and after.
Predicts: the default suite passes with normal opt-in skips and unchanged measured source.
Against: a named-control/default route regresses or source changes during the run.
Refs: results/opaque-native-controls-20261110/focused.txt
