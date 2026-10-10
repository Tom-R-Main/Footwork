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
