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

## O4 · update · 2026-11-10 20:28
Resolves: O3 = held
Observed: full default offline pytest on frozen1bdcd0b passed3301 tests with62 opt-in skips in203.87seconds, exit0. Hashes of ax/native/session/menu match before and after. No live/browser opt-ins were active.
Next: hand off completed offline evidence; parent retains all live observation, inspection and editing.
Refs: results/opaque-native-controls-20261110/full-default.json

## O5 · summary · 2026-11-10 20:28
Established: supported enabled unnamed buttons/popups can carry literal DOM identifiers with explicit persisted opaque provenance, exact process/window/document backing, observed-peer ID census and unchanged named-control qualification. 46 targeted opaque checks,516 affected tests and3301 full default tests pass with62 opt-in skips.
Uncertain: the worker did not perform live native input. SUN34 did not prove every peer's full direct parent chain to the bound window; fresh live qualification may conservatively omit controls. The literal identifier proves no semantic purpose, and incomplete SDK coverage remains explicitly incomplete.
Decision: close this source package at1bdcd0b with separate full regression evidence, no SDK build, runtime installation or UI action.
Refs: results/opaque-native-controls-20261110/report.md; docs/native-opaque-controls.md
