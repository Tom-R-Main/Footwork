# D3 authored native fixtures

`app.py` launches a run-owned AppKit accessory process and orders its own window
behind existing windows. It never activates another app or opens user documents.
`evals.d3_native.capture(out)` obtains a real window-bound Cua Driver screenshot
and full native AX tree, supplemented by macOS Vision OCR of the bound screenshot.
No expected labels, fixture config or oracle files enter observed model text.

Families are raster-only PDF cover identity, crop geometry preserving an illustrative
subject, and export progress versus persisted completion. They are native controlled
fixtures, not Finder, Preview, a photo editor or real media-export qualification.
Generated PDFs contain raster content only; immutable source hashes and selected
PDF artifacts are independent identity checks. Crops persist both rectangle and
cropped PNG, checked against the original pixels and independently authored subject
bounds. Exports persist a readable task-owned text artifact; they are a simplified
export-state protocol rather than elapsed video rendering.

The exact raw Cua screenshot is retained separately. Model images use a 256-color
indexed PNG encoding, with raw/model hashes, dimensions, max channel delta and RMSE
recorded. All observed AX and OCR lines remain in the text arm. Capture timing
includes screenshot, AX extraction, OCR and encoding, with constituent phases.

Scripted conformance skips the labelled negative/ambiguous proposal and executes a
separate known-good trajectory. This is mechanics evidence, not proof of a semantic
negative guard. `replay_case(case, accepted, out)` reconstructs the fixed recipe,
reobserves the actual bound window and dispatches only from model acceptance and
fresh AX target availability. It does not use an expected label to skip a wrong
selection or crop. Persisted independent postconditions can consequently fail.
Export completion additionally requires the real output artifact before acceptance.
All processes are terminated after their case; fresh output directories are required.
