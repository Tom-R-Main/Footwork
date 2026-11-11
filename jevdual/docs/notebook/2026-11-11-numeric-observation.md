# Numeric control observation

## NUM1 · prediction · 2026-11-11 00:11
Hypothesis: sliders and incrementors lose their observed numeric values and range in Footwork's native menu projection, even when the SDK snapshot supplies them; preserving bounded finite metadata can restore read-only assessment without adding mutation authority.
Test: public CLI simulated-Mac start/look with a slider and incrementor carrying finite values, descriptions and optional SDK min/max. First demonstrate absent numeric readout, then add bounded projection and check incomplete, nonfinite, malformed and missing fields plus unchanged click-only operations and text-only exact-value storage. The pinned WindowElement contract supplies min/max, value and value_description; no direct AX read, UI input or provider call is needed.
Predicts: baseline CLI drops the values; repaired CLI displays current values and retains structured snapshot provenance/ranges/descriptions when supplied. Invalid/absent fields remain unavailable, no units are inferred and no setter/key authority is added.
Against: the baseline already retains these values; projection manufactures bounds or a current value, changes action semantics, stores numeric controls as exact editable text, or fails to make their readout available through the public CLI.
Refs: python/jevdual/native.py; python/jevdual/menu.py; tests/test_session_scenarios.py; tests/contract/test_cua_driver_seams.py
