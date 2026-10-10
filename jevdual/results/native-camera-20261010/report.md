# Native MacBook camera experiment

The isolated capture CLI is implemented and its conformance checks pass. Native camera discovery is verified on this Mac. **Live frame acquisition remains unverified:** neither trial saved a PNG.

## Artifact identity

- Preregistration: `fb090bd`; experiment `jevdual/docs/experiments/NC1-native-camera.md`.
- Initial frozen source: `2bccd45`; amended fixed-30-fps source: `48b33a1`.
- Source hashes and checks: `conformance.json` and `conformance-v2.json`.
- Implementation: `tools/camera-capture-experiment/`; private evidence: ignored `tools/camera-capture-experiment/output/live-v1/` and `live-v2/`.

## Evidence

| Criterion | Kind | Observation | Result |
| --- | --- | --- | --- |
| Select observed physical camera and exclude OBS/screen | Answer | Public doctor selects only MacBook Pro Camera | Verified discovery; names are not authenticated hardware identity |
| Produce one decoded saved native frame | Historical action/current artifact | Both attempts retained unknown; no PNG in either run | Unverified |
| Retain prior unresolved action across restart | Current record | Repeated live-v1 capture retrieved original unknown intent; live-v2 status retrieved unknown with empty claims | Verified lookup; no exactly-once claim |
| Disable audio and reject substituted sources | Contract | Capture input explicitly camera:none and -an; conformance fixtures challenge virtual/screen/unobserved names | Passed conformance; no microphone opened by configured route |
| Bound acquisition process lifetime | Runtime | Live-v2 returned after bounded attempt; no FFmpeg process observed after termination | Observed cleanup; subprocess descendant case also passed |
| Bind request mode and defend saved evidence | Contract | Tests reject changed/legacy mode, tampered/missing artifacts and lost receipts | Passed fixtures; native artifact integrity not exercised |

All 18 stdlib tests and Ruff pass on `48b33a1`. Tests simulate camera/process boundaries; the real ffprobe test uses a generated fixture. These are not native-camera acquisition evidence.

Live-v1 rejected FFmpeg's default 29.970030 fps. The camera reports modes spanning 15–30 fps. Its record and diagnostic remain unchanged; repeating its token did not create a new intent or image.

Live-v2 explicitly requests 30 fps and no longer reports the unsupported framerate. It timed out with no saved PNG. Diagnostics list supported pixel formats after rejecting default yuv420p, but [FFmpeg documents fallback to the first supported format](https://ffmpeg.org/ffmpeg-devices.html#avfoundation); this message alone does not identify the timeout cause. Swift's inspection still reports not_determined for its own privacy identity; that does not prove FFmpeg's authorization state. The human's observation of any macOS camera prompt is pending.

## Reproduce without another capture

```sh
python3 tools/camera-capture-experiment/capture.py doctor --run-dir tools/camera-capture-experiment/output/live-v2
python3 tools/camera-capture-experiment/capture.py status --run-dir tools/camera-capture-experiment/output/live-v2 --token native-frame-002
python3 -m unittest discover -s tools/camera-capture-experiment -p 'test_*.py' -v
```

Original live commands used exact camera MacBook Pro Camera, token native-frame-001 in live-v1 and native-frame-002 in live-v2, --allow-permission-prompt, and --timeout 30. Existing unresolved operations are never replayed automatically. A future distinct acquisition requires a deliberate new operation after examining the prerequisite/runtime cause.

## Next decision

Establish whether a macOS access prompt appeared and was allowed, then diagnose first-frame delivery on the unchanged camera. Do not treat the remaining timeout as a pixel-format diagnosis. Keep this as an isolated tool until a useful desk workflow has been observed. Core Footwork authority, TextEdit recovery and model routing are unchanged. No provider calls or downloads were needed; images and private diagnostics are excluded from Git.
