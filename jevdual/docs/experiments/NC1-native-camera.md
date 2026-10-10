# NC1: Native Mac camera frame acquisition

Mode: bounded engineering feasibility experiment, not a comparative product-value trial.

## Hypothesis

An isolated FFmpeg AVFoundation capture route can acquire a frame from the specifically observed built-in MacBook camera and retain a truthful operation/artifact record.

## Predictions

If supported and authorized, one capture yields a decodable saved PNG and matching receipt. Repeated client tokens retrieve that record without camera dispatch. Missing authorization, missing camera, missing receipt or corrupt bytes never become successful acquisition.

If the hypothesis fails, permission/runtime acquisition or artifact verification cannot establish the requested frame; the failure remains explicit.

## Design

Use the installed FFmpeg and ffprobe binaries and Python standard library. Native permission inspection may use the installed Swift toolchain and AVFoundation. No new package install, provider call, microphone, screen capture, virtual-camera substitution, robot movement, or modification to jevdual production interfaces. Capture private images only in the experiment's ignored output. Use one fixed-operation ledger per run with conservative unresolved outcomes.

Primary metric: successful bounded acquisition with independently decodable saved image and matching hash (binary feasibility result).

Guardrails: exact physical device selection; bounded child lifetime; no microphone; no second dispatch for repeated tokens; artifact tamper/missing refusal; caller restart does not silently repeat an unresolved operation.

Decision rule: advance only frame-acquisition feasibility when all required conformance checks pass and a real native-camera acquisition is verified. Report a permission or runtime prerequisite as unverified. This says nothing about exposure timestamps, scene interpretation, document quality, capture-to-page identity, shutter idempotency, power-loss recovery, exactly-once effects, or useful workflow comparisons.

## Result

Partial result on frozen sources 2bccd45 and 48b33a1: discovery and 18 conformance checks pass; no live PNG was saved. The initial default-framerate rejection was removed by the preregistered 30 fps amendment, but the distinct trial timed out. Actual access and first-frame delivery remain unverified. NC1 stays open pending the human camera-prompt observation. See results/native-camera-20261010/report.md.

## Amendment · 2026-10-10 14:30
Live-v1 on 2bccd45 found FFmpeg default 29.970030 fps unsupported; no PNG exists and its ledger remains unknown. Next frozen version will explicitly request device-reported 30 fps and record it as part of the request. Live-v2 is a distinct operation, without altering or replaying live-v1. Original scope and decision rule remain unchanged.

## Amendment · 2026-10-10 14:40
The user was away during prior attempts and explicitly requested another attempt while present. Live-v3 will use unchanged source 48b33a1 with a 60-second bound, a distinct run directory/token, and the same exact camera and 30 fps mode. Earlier unknown records remain unchanged. This is a new authorized acquisition, not replay or resolution of an earlier outcome.
