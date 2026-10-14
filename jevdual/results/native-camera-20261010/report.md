# Native MacBook camera experiment

**Frame acquisition is verified on this Mac.** Attended live-v3 acquired one private 1080 × 1920 PNG on frozen source `48b33a1`. Independently run ffprobe and FFmpeg decoded it, and its SHA-256 and byte count match the persisted receipt. Fresh-process capture repeat and status retain the same original intent, receipt and artifact; the ledger bytes are unchanged. Exactly one PNG remains, and no FFmpeg process remained after verification.

## Source and evidence

- Initial preregistration: `fb090bd`; attended-trial preregistration: `c8f71e6`.
- Initial source: `2bccd45`; fixed-30-fps source used for the successful trial: `48b33a1`.
- Implementation: `tools/camera-capture-experiment/`.
- Conformance/source hashes: `conformance.json`, `conformance-v2.json`.
- Live results: `live-v1.json`, `live-v2.json`, `live-v3.json`.
- Private image/diagnostics: ignored `tools/camera-capture-experiment/output/live-v3/`; image has mode 0600. Image contents are not included in this report or Git.

All 18 stdlib conformance tests and Ruff pass on `48b33a1`. Those tests use synthetic camera/process boundaries plus a real ffprobe check on a generated fixture. The separate live-v3 result supplies native-frame evidence.

## Qualification

| Criterion | Evidence | Result |
| --- | --- | --- |
| Select observed physical camera and exclude OBS/screen | Public doctor selects only MacBook Pro Camera | Discovery verified; names are not authenticated hardware identity |
| Acquire a saved native frame | Live-v3 receipt and independent decode/hash readback | Verified PNG, 1080 × 1920, 2,300,920 bytes |
| Preserve repeat operations across process restart | Public capture repeat and status preserve ledger and saved bytes | Verified retained lookup; no exactly-once physical-effect claim |
| Disable audio and reject substituted sources | Explicit camera:none and -an; source-selection conformance cases | Passed configured route and fixtures |
| Bound owned subprocess lifetime | Live termination/readback plus descendant timeout fixture | No FFmpeg process remained |
| Preserve uncertainty and reject corrupt/missing evidence | Earlier live unknown records and conformance fixtures | Passed; original failed trials preserved |

Live-v1 rejected FFmpeg's default 29.970030 fps; the fixed source explicitly requests the observed supported 30 fps. Live-v2 timed out without saving an image. Its pixel-format message does not prove the cause because [FFmpeg documents fallback to the first supported format](https://ffmpeg.org/ffmpeg-devices.html#avfoundation). The user then requested a new attempt after being away. Live-v3 succeeded in about 2.58 seconds from persisted intent to receipt with a 60-second bound. This success does not establish prompt history or why live-v2 timed out.

## Readback and limits

```sh
python3 tools/camera-capture-experiment/capture.py status --run-dir tools/camera-capture-experiment/output/live-v3 --token native-frame-003
python3 -m unittest discover -s tools/camera-capture-experiment -p 'test_*.py' -v
```

The successful capture command used exact camera MacBook Pro Camera, token native-frame-003, run live-v3, --allow-permission-prompt and --timeout 60. Repeating those exact arguments retrieves the retained result. Earlier unresolved records are never replayed automatically.

This qualifies frame acquisition and retained artifact integrity here. It does not qualify exposure freshness, semantic interpretation, useful desk workflows, robot control, power-loss recovery or authenticated hardware identity. Retain the isolated tool until a separately scoped useful workflow is observed. Core Footwork authority, TextEdit recovery and model routing are unchanged. No provider calls or downloads were needed.
