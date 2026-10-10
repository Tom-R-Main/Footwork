# Native camera capture experiment

## NC1 · prediction · 2026-10-10 14:19
Hypothesis: the installed FFmpeg AVFoundation route can acquire one bounded frame from the observed MacBook Pro Camera and persist an operation-bound artifact without introducing camera dependencies into Footwork's native runtime.
Test: isolated public CLI doctor and capture; explicit observed physical camera selection, no microphone or screen capture; inspect the saved image with ffprobe and hash readback. Conformance checks cover repeated tokens, changed arguments, interrupted capture and tampered/missing artifacts. Camera permission refusal remains a missing prerequisite, not successful acquisition.
Predicts: doctor distinguishes the built-in camera from OBS Virtual Camera; when access is granted, capture produces one decodable image with an operation-bound receipt; repeat lookup does not reacquire; uncertain operations remain blocked rather than replayed.
Against: camera selection broadens to screen/virtual sources, microphone opens, an unobserved device is accepted, capture claims success without decodable saved bytes, repeated lookup acquires a second frame, or permission/lost evidence is promoted to verified acquisition.
Refs: tools/camera-capture-experiment/; docs/experiments/NC1-native-camera.md; /Volumes/External SSD/referencerepos/libgphoto2/examples/sample-trigger-capture.c; /Volumes/External SSD/referencerepos/rerun/examples/python/live_camera_edge_detection/live_camera_edge_detection.py
