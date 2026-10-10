# Camera paper inbox: first desk experiment

**The live physical-to-digital handoff worked after review.** A deliberately captured handwritten note was recognized locally, corrected in a separate file, confirmed by the user, saved once and independently checked through the real Footwork CLI. The saved note equals all 187 approved bytes. A fresh-process accept/status repeat preserves the same manifest and one note. The original frame and 180-byte raw OCR candidate remain unchanged.

## What was built

- `tools/desk-inbox-experiment/`: saved-frame preparation, local Apple Vision OCR, private review HTML, explicit digest-bound acceptance and status.
- `footwork check-artifact DEST --expected-file REVIEWED --expected-sha256 DIGEST`: a provider-free, read-only exact-byte check. It uses no fabricated native/browser Carry and does not grant action or native-completion authority.
- Original capture stays in `tools/camera-capture-experiment/`; the new tool reads acquired receipts without reopening the camera.

Frozen implementation: `6e93c35`; preregistration: `e62fb47`, mirror amendment: `3e63656`. Source identity and commands are in `source.json`. All 31 focused tests and scoped Ruff passed. Existing CLI/carry tests are included. No provider calls or downloads were needed.

## Observed evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Printed note, real Vision | Independently drawn known three-line fixture | Exact text match |
| Normal and mirrored text | Known calibration fixtures; explicit up/upMirrored | Same expected text and candidate digest; source bytes retained |
| Blank image | Real Vision | needs_text; no note; acceptance refused |
| Wrong approval digest | Public accept | Refused before writing a note |
| Tampered saved fixture | Public status and repeat accept | Current unknown, historical save retained; no overwrite/replay |
| Live handwritten note | User-positioned physical paper and actual camera receipt | Acquired, recognized and reviewed |
| Live mirror direction | Readable calibration line in original frame | Not mirrored; explicit up used |
| Saved text | User-confirmed correction and independent public Footwork check | Exact bytes match, one note |
| Restart/repeat | Public fresh-process accept/status and unchanged manifest | Existing note reused; raw OCR preserved |

Private live output is under `tools/desk-inbox-experiment/output/live-paper-v1/`; camera output is under `tools/camera-capture-experiment/output/desk-paper-v1/`. Images, OCR, candidate/corrected text and note contents are ignored and excluded from this report. `verification.json` records hashes, byte counts, checks and limits. Fixture identities are in `fixtures.json`; fixtures prove synthetic behavior rather than human handwriting quality.

## What the handwriting test showed

Raw OCR contained missing spaces, casing/punctuation differences and word substitutions. It did not match the user's note cleanly. The separate corrected text was explicitly confirmed before saving, with the original header retained. This qualifies a reviewed workflow on one note, not autonomous transcription or calibrated handwriting accuracy.

The helper uses [Apple Vision text recognition](https://developer.apple.com/documentation/vision/vnrecognizetextrequest) in accurate mode, en-US, with language correction disabled. An explicit --mirror-input chooses [upMirrored orientation](https://developer.apple.com/documentation/imageio/cgimagepropertyorientation/upmirrored); it never rewrites the original PNG or classifies direction from confidence. Lines retain confidence and bounds, which do not establish correctness.

Local reference seams: Cua `libs/lume/src/Utils/VNCDriver.swift:272` for Vision recognition; Rerun `examples/python/live_camera_edge_detection/` for acquisition/visual inspection. Footwork's existing Carry semantics were preserved because they require real native/browser observations.

## Readback

```sh
python3 tools/desk-inbox-experiment/inbox.py status --run-dir tools/desk-inbox-experiment/output/live-paper-v1
jevdual/.venv/bin/footwork check-artifact tools/desk-inbox-experiment/output/live-paper-v1/inbox/note.txt --expected-file tools/desk-inbox-experiment/output/live-paper-v1/reviewed.txt --expected-sha256 6d4fb067193c2c1f48d3e57c130fee9cf9540651c7b77946e020b13a8e71847c
```

## Decision

Keep the workflow isolated in Footwork's tools directory. The integration proves exact saved-artifact equality to an explicitly reviewed source. It does not establish exposure freshness, authenticated physical page/hardware/review identity, exactly-once physical effects, power-loss recovery or native UI completion.

Improve capture/review friction next: paper-region selection, a legibility check and word-level review against the image. Compare this with ordinary note entry before adding automated task creation. The technical opportunity is a source-preserving physical observation that can support a later bounded digital action; demand and daily utility remain unvalidated.
