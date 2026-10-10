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
