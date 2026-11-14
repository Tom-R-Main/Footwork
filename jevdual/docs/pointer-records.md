# Filmed pointer records

`footwork park X Y --session S` (an initialized native `--pointer-motion filmed`
session) appends one compact JSON line to **`S/pointer-gestures.jsonl`**. `point`,
automatic approaches before actions, and filmed drags use the same file. The old
summary/stdout and latest-50 summary list are unchanged; the separate JSONL has no
retention cap. A filmed start reserves the desktop, and a reserved session cannot
be restarted in place: start each take in a fresh session directory, after
`footwork control yield TOKEN` for the previous one. A refused start leaves the
old file intact. No filesystem work runs per sample.

Each line has `schema: "pointer_gesture/1"`. This is the D1 series subset of the
pointer-motion plan's proposed record, not a claim that all of plan section 3.6
is implemented (planner provenance and series hash remain future work).

- `clock`: `CLOCK_UPTIME_RAW`; `timestamp_unit`: `ns`. These are macOS raw uptime
  nanoseconds, convertible to mach host ticks with the machine's timebase.
- `recording_started_ns`: recording-context start before display metadata reads.
  `playback_started_ns`: scheduler start for a planned move, or the first owned
  post boundary for a drag/one-shot. It is null for no-input and opaque SDK rows.
  `t0_ns`: scheduler motion-start anchor; for a drag, this is **after** its
  button-down/press hold; for an owned one-shot, the first post boundary. The scheduler still uses its original
  `time.monotonic()` clock; a bracketed clock pairing maps its start into raw
  uptime. `clock_mapping_uncertainty_ns` is the width of that pairing interval.
- `planned_samples`: objects `{t_ns,x,y}` at absolute scheduled raw times. The
  initial start sample is admitted but is not posted again. `posted_samples`:
  `{t_ns,post_returned_ns,x,y,event,backing_scale}`. For the real Quartz poster,
  entry/return bracket **CGEventPost**; fake posters bracket the fixture method.
  `posted_basis` says which. Events include `move`, `down`, `drag`, `up`, `warp`.
  They prove posting calls, not OS delivery or the continuous physical path.
- `start`, `requested_target`, `final_location`: `[x,y]` in global screen points;
  `final_measured_ns` dates the fresh final pointer read. Moves measure after
  their existing dwell; drag measures after its existing settle/release. No new
  wait or pointer correction is introduced. A final read is not arrival proof.
- `space`: `{coordinates:"global_screen_points",origin:"top_left",unit:"pt"}`;
  `window_origin`, `content_origin`: recorded filmed geometry used for viewport
  CSS-pixel conversion at 100% zoom. `displays`: actual active display IDs,
  global point bounds and each `NSScreen.backingScaleFactor`; root
  `backing_scale` is the requested target's display scale, and each posted sample
  names its own scale. These metadata are read before playback, not per post.
- `outcome`, `posted`, `max_gap_s`, `lateness_s`, `causes` retain player results;
  `post_errors` means a call raised and delivery of that attempt is unknown.
  Partial successful calls are kept when playback aborts or raises.
- `completeness:"complete"` means owned post capture is complete;
  `geometry_complete` independently identifies missing display metadata.
  `completeness:"post_error_outcome_unknown"` marks an uncertain failed post.

**Current SDK gap.** A filmed hover still does its ordinary CUA `move_cursor`
after its approach, and explicit foreground click uses CUA's native click.
Those SDK internals do not expose their samples. Their additional lines have
`completeness:"unavailable_sdk_samples"`, `planned_samples:null`,
`posted_samples:null`, raw `call_started_ns`/`call_returned_ns`, and measured
before/after locations. They are **not complete D1 paths**. Capture requires a
separate native SDK telemetry build; nothing substitutes or refuses those inputs.
The owned title-bar fallback records its down/up and restore warp separately.

Recording failures print `pointer recording failed` on stderr and do not change
the pointer action's existing outcome. No success should be inferred for a
missing or incomplete artifact. The JSONL may hold page labels and geometry;
it belongs with private take traces rather than published source fixtures.

## A drag between two points, with no session

`footwork drag-points X0 Y0 X1 Y1 --mode exclusive_desktop --record FILE` appends the
same `pointer_gesture/1` line to `FILE`, with `kind: "drag"` and `label: "drag-points"`.
The command has no window, so `window_origin` and `content_origin` are `[null, null]`;
its points are already global screen points. Only the drag is recorded (`down`, the
`drag` posts, `up`); the approach to the start, when there is one, is not. The command's
own JSON on stdout gives the press and release points and the raw-uptime time of the
call that posted each (`pressed_ns`, `released_ns`), which are post times, not delivery.
