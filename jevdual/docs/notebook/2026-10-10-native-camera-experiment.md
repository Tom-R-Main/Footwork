# Native camera capture experiment

## NC1 · prediction · 2026-10-10 14:19
Hypothesis: the installed FFmpeg AVFoundation route can acquire one bounded frame from the observed MacBook Pro Camera and persist an operation-bound artifact without introducing camera dependencies into Footwork's native runtime.
Test: isolated public CLI doctor and capture; explicit observed physical camera selection, no microphone or screen capture; inspect the saved image with ffprobe and hash readback. Conformance checks cover repeated tokens, changed arguments, interrupted capture and tampered/missing artifacts. Camera permission refusal remains a missing prerequisite, not successful acquisition.
Predicts: doctor distinguishes the built-in camera from OBS Virtual Camera; when access is granted, capture produces one decodable image with an operation-bound receipt; repeat lookup does not reacquire; uncertain operations remain blocked rather than replayed.
Against: camera selection broadens to screen/virtual sources, microphone opens, an unobserved device is accepted, capture claims success without decodable saved bytes, repeated lookup acquires a second frame, or permission/lost evidence is promoted to verified acquisition.
Refs: tools/camera-capture-experiment/; docs/experiments/NC1-native-camera.md; /Volumes/External SSD/referencerepos/libgphoto2/examples/sample-trigger-capture.c; /Volumes/External SSD/referencerepos/rerun/examples/python/live_camera_edge_detection/live_camera_edge_detection.py

## U-NCACCESS · update · 2026-10-10 14:22
Observed: system camera inventory includes MacBook Pro Camera and OBS Virtual Camera; installed FFmpeg AVFoundation inventory matches exactly one MacBook Pro Camera. A separate Swift AVFoundation authorization query returns notDetermined. No camera has been opened and no image exists.
Inferred: built-in camera discovery is supported here; Swift permission state does not qualify the FFmpeg process identity or actual frame acquisition.
Next: complete isolated CLI conformance, freeze implementation, then explicit camera-only first-use capture under the user's authorized scope; OS permission and saved-image proof remain necessary. NC1 stays open.
Refs: results/native-camera-20261010/preflight.json; tools/camera-capture-experiment/

## U-NCMODE · update · 2026-10-10 14:30
Observed: frozen source 2bccd45 passed 18 conformance checks and Ruff. Live-v1 FFmpeg dispatch rejected its default 29.970030 fps; private diagnostic lists device modes spanning 15 to 30 fps, and no PNG was saved. Repeat of the identical token returns the original unknown operation without a new intent. NC1 remains open.
Inferred: a mode prerequisite, rather than saved-image verification, prevented acquisition; actual permission and acquisition remain unqualified.
Next: preregister explicit 30 fps and preserve live-v1 unchanged; a distinct trial is a new capture operation.
Refs: results/native-camera-20261010/conformance.json; results/native-camera-20261010/live-v1.json; tools/camera-capture-experiment/output/live-v1/

## NC2 · prediction · 2026-10-10 14:30
Hypothesis: explicitly requesting the device-reported 30 fps eliminates the unsupported-default frame-rate failure while preserving capture argument binding and unknown outcomes.
Test: add a fixed 30 fps input option and bind it into the request; retain conformance checks, freeze amended source, and perform one distinct live-v2 native-camera operation.
Predicts: command requests 30 fps; live-v2 no longer fails with unsupported 29.970030 fps. Successful acquisition additionally requires permission and a decoded saved artifact; another failure remains unknown.
Against: FFmpeg still rejects 30 fps as unsupported, the request omits the mode, changing a retained mode replays an operation, or failure becomes a success without artifact proof.
Refs: results/native-camera-20261010/live-v1.json; docs/experiments/NC1-native-camera.md

## U-NC2 · update · 2026-10-10 14:33
Resolves: NC2 = held
Observed: amended source 48b33a1 binds fixed 30 fps; all 18 conformance checks and Ruff pass. Live-v2 does not report unsupported framerate, but reaches its bounded timeout with no saved PNG. Status after process restart retains unknown and empty claims. No FFmpeg process remained. Swift still reports not_determined for its separate privacy identity. NC1 remains open.
Inferred: the 30 fps change removes the known mode failure but does not establish actual authorization or first-frame delivery. The unsupported default pixel-format message is not a sufficient cause: FFmpeg documents automatic fallback to its first supported format.
Next: establish the human's observation of any macOS camera prompt before further live acquisition; preserve both prior operations unchanged.
Refs: results/native-camera-20261010/live-v2.json; results/native-camera-20261010/conformance-v2.json; results/native-camera-20261010/report.md; https://ffmpeg.org/ffmpeg-devices.html#avfoundation

## S-NCPARTIAL · summary · 2026-10-10 14:33
Established: an isolated public capture/status CLI, exact local discovery, conservative unknown outcomes and restart lookups; fixture conformance and lint pass. A committed explicit 30 fps setting eliminates the observed unsupported-default frame-rate failure.
Uncertain: live native-frame acquisition, camera permission identity and first-frame delivery; exposure freshness, scene semantics and useful desk workflows remain unqualified.
Decision: retain the bounded prototype in tools/camera-capture-experiment, leave NC1 open, and hand off the permission observation prerequisite before another distinct live trial. No production native-runtime adoption is supported by these results.
Refs: results/native-camera-20261010/report.md; docs/experiments/NC1-native-camera.md; 48b33a1

## NC3 · prediction · 2026-10-10 14:40
Hypothesis: the user being present to answer a first-use prompt, with a 60-second capture bound, allows the unchanged 30 fps route to establish frame acquisition if unattended authorization was the remaining prerequisite.
Test: the user explicitly requested another attempt after being AFK; preserve prior unknown operations, use a distinct live-v3 run and token, fixed source 48b33a1, and a 60-second bound. Verify any saved PNG independently, then repeat the token and status without new acquisition.
Predicts: if a prompt was the prerequisite and is allowed, the new operation yields one decoded saved PNG and retained receipt. Otherwise it remains unknown/refused, which does not diagnose permission as the cause.
Against: authorization is confirmed yet no frame is acquired within the bound, or repeated lookup reopens the camera or promotes missing evidence.
Refs: results/native-camera-20261010/report.md; tools/camera-capture-experiment/output/live-v3/; 48b33a1
