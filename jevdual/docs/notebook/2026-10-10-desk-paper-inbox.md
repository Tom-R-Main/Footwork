# Desk paper inbox experiment

## DI1 · prediction · 2026-10-10 14:52
Hypothesis: local Apple Vision OCR and an explicit digest-bound review can turn a small visible paper note into one private inbox artifact whose exact content Footwork independently verifies.
Test: implement isolated desk tool plus read-only Footwork artifact oracle, freeze source, run real OCR on known synthetic text, exercise the public prepare/review/accept/status boundaries, then attempt one real paper note if the user can position it. Preserve synthetic/live distinctions.
Predicts: accepted text is saved once and Footwork confirms exact bytes; repeats reuse one note; empty/changed/unapproved/tampered evidence refuses or reports unresolved without extra effects. No fake native/browser carries or provider calls.
Against: OCR alone dispatches an action, changed approval/candidate becomes saved text, bytes differ while verification passes, repeated token duplicates a note, or fixture proof is presented as live usefulness.
Refs: docs/experiments/DI1-desk-paper-inbox.md; tools/camera-capture-experiment/; /Volumes/External SSD/referencerepos/cua/libs/lume/src/Utils/VNCDriver.swift:272; /Volumes/External SSD/referencerepos/rerun/examples/python/live_camera_edge_detection/live_camera_edge_detection.py

## DI2 · prediction · 2026-10-10 14:54
Hypothesis: an explicit horizontal-mirror setting, applied to OCR orientation and review presentation while retaining the original source bytes, can handle a mirrored camera feed without silently changing capture evidence or operation identity.
Test: expose --mirror-input at preparation, bind it in source/request provenance, and test real Vision against known normal/mirrored printed fixtures. The user's live note will include LEFT 123 RIGHT to determine the feed's direction.
Predicts: the appropriate explicit orientation yields the original literal line order/text; a changed orientation cannot reuse a prior candidate as though it had the same source request. Original PNG/hash remain intact, and preview names the orientation.
Against: normal text is reversed under its matching setting, mirrored proof silently overwrites source bytes, OCR claims imply mirror classification, or candidate lookup ignores changed orientation.
Refs: docs/experiments/DI1-desk-paper-inbox.md; tools/desk-inbox-experiment/; https://developer.apple.com/documentation/vision/vnimagerequesthandler

## U-DI1 · update · 2026-10-10 15:05
Resolves: DI1 = held
Observed: frozen source 6e93c35 passes 31 focused tests and Ruff. Real Vision exactly recognizes the known printed fixture; blank fixture yields no candidate/note. The user positioned a live handwritten paper, confirmed a separately corrected transcription after seeing raw OCR errors, and authorized saving it. Public Footwork check-artifact independently confirms all 187 approved bytes; fresh-process accept/status preserve the same manifest and one note. Raw OCR and source remain unchanged. Wrong digest refuses; a tampered saved fixture retains historical save but current unknown and repeat acceptance does not overwrite it.
Inferred: reviewed physical-to-digital note feasibility is established on this Mac and one real note; unreviewed handwriting accuracy and daily utility remain unqualified.
Next: close DI1; assess capture/review friction before further workflow expansion.
Refs: results/desk-inbox-20261010/verification.json; results/desk-inbox-20261010/source.json; results/desk-inbox-20261010/report.md; tools/desk-inbox-experiment/output/live-paper-v1/

## U-DI2 · update · 2026-10-10 15:05
Resolves: DI2 = held
Observed: real Vision on normal and horizontally mirrored known fixtures yields the same exact expected three lines under explicit up/upMirrored settings. Original source hashes remain intact; changed mirror request refuses reuse. The live calibration line reads normally in the raw captured frame, so no flip was selected.
Inferred: explicit orientation handling works on these fixtures and the observed feed; this does not classify arbitrary camera mirror state or infer direction from confidence.
Next: keep mirror choice explicit and tied to retained calibration evidence.
Refs: results/desk-inbox-20261010/verification.json; results/desk-inbox-20261010/fixtures.json; tools/desk-inbox-experiment/recognize.swift

## S-DICLOSED · summary · 2026-10-10 15:05
Established: one complete live capture/OCR/review/save/readback handoff, exact approved bytes, repeat lookup and preserved source/corrections; real printed/mirror/blank OCR proof remains distinct from fixture conformance.
Uncertain: raw handwriting quality, daily usefulness, capture-to-page identity, exposure freshness, authenticated review and any autonomous or robotic actions.
Decision: keep an isolated desk tool plus read-only Footwork artifact checker; prioritize image/word review and legibility before task execution. No native recovery, guard threshold or model-default changes were made.
Refs: results/desk-inbox-20261010/report.md; docs/experiments/DI1-desk-paper-inbox.md; 6e93c35
