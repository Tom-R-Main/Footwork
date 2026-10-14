# Native camera capture experiment

Acquire one saved PNG from an exactly selected physical Mac camera. This is an isolated
Footwork experiment using Python's standard library and installed FFmpeg/ffprobe. It does
not change Footwork's runtime, TextEdit recovery, or production adapter interfaces.

The experiment asks whether a requested frame can be acquired, decoded, and associated
with a retained operation record. It does not establish exposure freshness, scene meaning,
document quality, page identity, or exactly-once physical execution.

## Inspect and capture

Run from the repository root. Private run directories must be descendants of this package's
ignored `output/` directory. Directories use permissions 0700; records and diagnostics use 0600.
The program creates a missing run directory and refuses symlinked or publicly readable directories.

```sh
python3 tools/camera-capture-experiment/capture.py doctor \
  --run-dir tools/camera-capture-experiment/output/desk-session
```

`doctor` reports model names from `system_profiler`, FFmpeg's AVFoundation video inventory,
their unique physical-name intersection, and camera authorization status. It excludes known
screen, virtual, OBS, and Continuity routes. Device IDs and microphone inventory are omitted.
Inventory is a selection aid, not authenticated hardware identity or proof of access.

The optional Swift helper only queries `authorizationStatus(.video)`; it never requests
permission. Its status is specific to that process's privacy identity and does not prove
FFmpeg is authorized. An unavailable Swift query is reported explicitly.

Use an exact name from `eligible_cameras`:

```sh
python3 tools/camera-capture-experiment/capture.py capture \
  --run-dir tools/camera-capture-experiment/output/desk-session \
  --camera 'MacBook Pro Camera' --token frame-001
```

If the status is undetermined or unavailable, an intentional first capture requires
`--allow-permission-prompt`. That lets FFmpeg's explicit camera acquisition trigger the
macOS authorization flow. `doctor` never opens the camera or requests access. A queried
denied/restricted status is refused; inspect macOS privacy settings before proceeding.

Capture selects the observed device by name, explicitly disables microphone capture,
and saves one PNG without overwriting an existing artifact. It explicitly requests 30 fps,
a supported mode reported by this MacBook camera during NC1. It makes no resolution
assumption. Another device may reject this fixed mode; there is no mode fallback.
Capture defaults to a 15-second timeout; `--timeout` accepts 1-60
seconds. Inventory and permission inspection have separate bounded process lifetimes.
FFmpeg and its descendants are terminated on completion, timeout, or cancellation.

## Read the result

```sh
python3 tools/camera-capture-experiment/capture.py status \
  --run-dir tools/camera-capture-experiment/output/desk-session --token frame-001
```

An `acquired` result means FFmpeg completed and ffprobe decoded one PNG frame, with
positive dimensions and a matching retained hash/byte count. `status` rechecks that saved
artifact without opening a camera. It provides no exposure timestamp or semantic claim.

The ledger records intent before dispatch. Repeating the same token and arguments reads
the existing record, even in a fresh process. The request binds the fixed `framerate_fps: 30`
alongside camera, timeout and permission-prompt arguments. Changed arguments or an older
request without that mode are refused by `capture`; `status` can still inspect the earlier
record. A nonblocking process lock permits one owner per run.

After dispatch, any incomplete capture or receipt produces `unknown`, including the first
CLI response. A pending ledger found after a restart remains unknown. A valid image without
a completed receipt cannot promote it to acquired. Unresolved operations block further
captures in that run; there is no automatic replay or reset command.

If an acquired image later disappears or changes, current `state` becomes `unknown` and
claims are empty. `acquisition_outcome` and the persisted original receipt still retain the
historical acquisition; the current artifact is unusable. New captures in that run are blocked.

FFmpeg stderr is retained in a private, bounded diagnostic file named in the record. It
is not printed by the CLI. Use it to distinguish permission, device-format, or runtime
failures. The experiment never retries by changing camera modes or selecting another device.
Inspect an unresolved run manually before deliberately beginning a new run. A new run is
a new operation, not proof that the earlier operation did not happen.

Exit code 0 means the inventory completed, a retained acquisition is currently verifiable,
or a status token is absent. Exit code 2 means refusal, unknown outcome, or invalid retained
evidence. JSON `state` distinguishes those cases. This is process-restart testing; power-loss
recovery, hostile replacement, and cross-run camera exclusivity are not qualified.

## Conformance checks

```sh
python3 -m unittest discover -s tools/camera-capture-experiment -p 'test_*.py' -v
```

Tests use synthetic inventory and subprocess fixtures, never a live camera. One test uses
installed ffprobe to decode a tiny generated fixture. Live acquisition belongs to the
preregistered NC1 experiment and its engineering notebook. Private images, device diagnostics,
Swift module cache, and test scratch files remain under ignored `output/`.

## Reference seams

- Rerun's local `examples/python/live_camera_edge_detection/` illustrates camera acquisition
  and visual inspection. A later exporter can project saved frames and operation events.
- libgphoto2's `examples/sample-trigger-capture.c` illustrates camera event and file handling.
  A tethered still-camera transaction needs its own interface and qualification.
- Footwork's capability backend has validation, dispatch and readback seams. This experiment
  deliberately keeps its acquisition ledger separate from native document recovery.

Preregistration: `jevdual/docs/experiments/NC1-native-camera.md`.
Notebook: `jevdual/docs/notebook/2026-10-10-native-camera-experiment.md`.
