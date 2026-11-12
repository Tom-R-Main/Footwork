# Numeric control observation

## NUM1 · prediction · 2026-11-11 00:11
Hypothesis: sliders and incrementors lose their observed numeric values and range in Footwork's native menu projection, even when the SDK snapshot supplies them; preserving bounded finite metadata can restore read-only assessment without adding mutation authority.
Test: public CLI simulated-Mac start/look with a slider and incrementor carrying finite values, descriptions and optional SDK min/max. First demonstrate absent numeric readout, then add bounded projection and check incomplete, nonfinite, malformed and missing fields plus unchanged click-only operations and text-only exact-value storage. The pinned WindowElement contract supplies min/max, value and value_description; no direct AX read, UI input or provider call is needed.
Predicts: baseline CLI drops the values; repaired CLI displays current values and retains structured snapshot provenance/ranges/descriptions when supplied. Invalid/absent fields remain unavailable, no units are inferred and no setter/key authority is added.
Against: the baseline already retains these values; projection manufactures bounds or a current value, changes action semantics, stores numeric controls as exact editable text, or fails to make their readout available through the public CLI.
Refs: python/jevdual/native.py; python/jevdual/menu.py; tests/test_session_scenarios.py; tests/contract/test_cua_driver_seams.py

## NUMU1 · update · 2026-11-11 00:15
Resolves: NUM1 = held
Observed: the public simulated-Mac start scenario failed because Track volume had no displayed value. After bounded projection, start/look display the supplied spelling and session/inspection records retain finite numeric metadata, explicit source, optional range and a bounded description with clipping provenance. Text exact-value storage stays empty and controls remain click-only. The affected native/menu/session/SDK checks pass483tests; visual inspection plus numeric checks pass49tests, including a read-only inspection with no model/dispatch. An initial contract run through the base environment failed its pinned SDK-version check; the proper project focus1 overlay passes, with no installation or source workaround.
Inferred: the projection loss is repaired at the public CLI boundary for controls already offered by the SDK. It neither restores controls absent from its snapshot nor qualifies actual Studio fader editing, renderer agreement or saved numeric state.
Next: hand the generic observation repair to the parent for integrated source validation and actual Studio observation. Do not add numeric setters or arbitrary unnamed target authority in this package.
Refs: output/numeric-observation-red.txt; output/numeric-observation-affected.txt; output/numeric-observation-inspection.txt; results/numeric-observation-20261111/report.md

## NUMS1 · summary · 2026-11-11 00:15
Established: finite supplied numeric values, optional SDK bounds and bounded value descriptions survive native menu, public CLI look, saved session and target inspection. Missing, malformed, nonfinite or excessive inputs are omitted; contradictory finite bounds are marked invalid. Snapshot provenance is explicit, units are never inferred and no numeric edit operation was added.
Uncertain: actual app renderer agreement, persistence and Studio controls omitted by the SDK remain unqualified. Structured numbers use floating-point approximation while display keeps the supplied numeric spelling; this is not exact text authority.
Decision: close the bounded read-only projection package and retain the simulator reproduction, negative cases and pinned SDK contract checks for the parent integration.
Refs: results/numeric-observation-20261111/report.md
