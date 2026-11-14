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
A drag stopped before the press writes its line with `outcome: "not_pressed"` and no
posted samples.

The command's exit says how far it got, and the JSON says the rest:

| Exit | Meaning | In the JSON |
|---|---|---|
| 0 | Pressed at the start, released at the end, the button reads up. | `outcome: "dropped"` |
| 4 | Nothing was posted. | `outcome: "refused"`, `code`, `reason` |
| 5 | The pointer was moved; the button was never pressed. | `outcome: "approach_aborted:<cause>"` |
| 6 | Pressed, and released otherwise than asked; the button reads up. | `outcome`, `released_at`, `escape_sent`, `stopped_by`, `error`, `extra_release` |
| 8 | Pressed, and the command cannot say the button is up. | `claim_kept` (the registry token), `button_up`, `releases_posted` |

After exit 8 the desktop stays claimed in the coordination registry, and every other
owner of it is refused, until someone has looked at the button and run
`footwork control recover TOKEN --input-cleaned`. The command comes to exit 8 only after
posting a second release where the pointer is: when no release's post returned, when
the button still read down 250 ms after one did, or when the button could not be read
(`button_read_error`). From the moment the press is dispatched the claim is kept unless
the command knows that nothing was pressed or that the button reads up after a posted
release.

A session's `footwork do drag` uses the same engine. When neither post of its release
returns, its command's claim is kept in the same way, and the receipt's error begins
with the recover command and the token.

`no_stop_signals` (exit 4) is refused for the same reason: the command cannot take the
stop signals when it is not on its process's main thread.

### Where the press goes

`--app NAME` is required. It names the application both points are in. The command
presses only when a system-wide accessibility hit test at the start point and at the end
point both find that application. It reads them before anything is posted and again
immediately before the press.

| Refusal | When |
|---|---|
| `app_required` (exit 4) | No `--app`. |
| `point_covered` (exit 4; exit 5 as `approach_aborted:point_covered` after an approach) | A hit test at one end found another application: a system prompt, an alert, another application's window. `reason` names the end, what was found and what was named. |
| `recipient_unreadable` (exit 4 or 5) | The hit test could not be read. |

What this does and does not establish:

- It refuses a press that would land on a system prompt or on another application.
- It does not refuse for a window that only overlaps a point and passes input through
  (a dictation or recording overlay): the hit test does not find such a window.
- It is accessibility's answer at two points at two moments. It is not the event
  system's own routing, it does not cover the path between the points, and a window that
  appears after the second reading is not seen.
- It establishes the application, not what inside it is at the point. A menu, a popover
  or a dialog of the same application passes. That is the caller's to know.

A caller filming a take should still look at the screen before it starts. The command no
longer depends on that for the press itself.

SIGINT, SIGTERM and SIGHUP stop a drag the way foreign input does (Escape, then one
release where the drag had got to), and the command still prints its JSON; `stopped_by`
names the signal. SIGKILL cannot be handled: the registry then marks the request
orphaned, and the button is whatever it was.

`button_up_ms_after_release` is the time from the return of the release's post to the
reading that said the button was up. `claimed` lists what was claimed: the desktop and
the application named with `--app`. `--duration` takes at most 30 s, and a slower drag has more posts along the same
path, none planned further apart than the plain drag's.
