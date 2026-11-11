# Opaque native controls

## O1 · prediction · 2026-11-10 20:13
Hypothesis: the native projection omits unnamed editor buttons even when an independently read exact DOM identifier and document scope could distinguish them without inferring purpose.
Test: public CLI simulated-Mac scenarios expose two unnamed AXButton/AXPopUp controls with exact bound role/frame/PID/window, empty native names, DOM identifiers and closest direct WebArea URLs; exercise numeric action, incomplete/duplicate census and identity/name/scope drift before preflight and dispatch. Add direct AX qualification checks and preserve named-control scenarios.
Predicts: the current public route drops the backed controls; a separate bounded opaque census can expose literal identifiers with persisted provenance, retain readable empty-ID peers as omitted, and refuse unreadable/duplicate/drifting evidence without input.
Against: current CLI already exposes those controls, or safe qualification needs positional identity, semantic guesses, unbounded census, or weaker named-control checks.
Refs: output/suno-20261110/editor-affordances-SUN34.json; results/opaque-native-controls-20261110/
