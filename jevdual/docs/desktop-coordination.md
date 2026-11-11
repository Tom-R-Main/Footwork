# Coordinating operators on a shared desktop

Use a separate explicit `--session DIR` (or `FOOTWORK_SESSION`) for each operator.
The public CLI serializes every session command, including observations, before
loading state. Atomic replacement of `session.json` alone is not a transaction.
The default `runs/session` is still available, but two operators using it share
one state stream rather than gaining separate sessions.

All cooperating CLI processes use `~/.local/state/footwork/coordination.sqlite`.
Changing `--authority` does not select a different resource coordinator. The
coordinator is separate from durable execution journals: it does not settle an
uncertain operation, grant an effect, or certify that an action succeeded.

A command owns its resources through dispatch, settling, readback and driver
shutdown. Native work serializes by app because menu, process keys and document
state can affect several windows. Ordinary browser work serializes by native
browser window. Startup takes the app scope as a barrier; a native Chrome command
also conflicts with every ordinary-browser window. Independent apps and browser
windows can overlap. Same-window tabs are deliberately serialized while CUA's
tab handles remain connection-local. Queued conflicting requests run in order;
unrelated requests can pass them. Acquisition waits up to 30 seconds, then stops
with `coordination_refused` and no dispatch from that command.

Foreground-capable mutation commands acquire the desktop before evaluating the
human-idle gate. This prevents two processes from both passing that gate and
taking the foreground together. The claim lasts through the transaction; it does
not grant permission to interrupt a person. Background-only commands need no
desktop claim and still obey the existing delivery policy. Headed browser startup
also claims the desktop because Chrome launch/recovery can activate a native
window, even when subsequent page actions qualify for background delivery.
On X11, the server in `DISPLAY` identifies the desktop; numeric screen suffixes
and local Unix/loopback host aliases share ownership. Distinct local X servers
can own independent desktops; macOS conservatively uses one console domain per user.
A viewing stream or session name never creates a new pointer.

## Film a take and hand it off

```sh
footwork start 'Film the workflow' --app 'Google Chrome' --window 'Demo' \
  --session runs/film-2 --mode exclusive_desktop --pointer-motion filmed
footwork control status
# Run the take, including gaps between commands.
footwork do click 'Record it' --session runs/film-2
footwork control yield RESERVATION_TOKEN
```

A successful filmed start automatically stores a persistent reservation for both
the desktop and subject app. It survives CLI exit and has no expiry. Other
operators may continue background-only work on independent apps. Background
mutations of the filmed app and foreground/pointer work on the desktop wait.
An ordinary `exclusive_desktop` session acquires a short command claim; it does
not reserve gaps unless explicitly requested:

```sh
footwork control reserve --session runs/operator
footwork control status
footwork control observe --session runs/film-2
footwork control cancel REQUEST_OR_RESERVATION_TOKEN
```

`control status` lists owners, process IDs, resources, waiting requests and exact
ownership tokens. `control observe` reads the last saved observation without
connecting to a driver or sending input; its output explicitly says `live: false`.
It can inspect a take without becoming a controller. Normal `status` remains
available after revocation; `status --reconcile` requires resource ownership.

Yield and cancel revoke only the supplied token. A revoked session cannot resume
input implicitly; `control reserve --session DIR` is the explicit next handoff.
A delayed yield of an older token cannot revoke a newer reservation. A reserved
session cannot be reset with `start`; use a fresh session directory.

Cancellation fences new SDK RPCs and direct accessibility writes. An already
admitted SDK RPC can finish. Pointer playback checks cancellation between samples,
and releases its owned button through its existing cleanup path. Canceling an
async task cannot abandon a mutating worker thread: ownership remains until that
thread has finished cleanup. Readback and driver shutdown remain possible after
revocation, and conflicting work cannot start until the active command exits.
This is cooperative cancellation, not interruption inside an opaque SDK RPC.

A hard kill cannot run cleanup. A dead foreground/pointer owner therefore leaves
an `orphaned` claim that blocks conflicting work. Check and release that owner's
held buttons/modifiers on the actual desktop before explicitly recovering it:

```sh
footwork control recover ORPHAN_REQUEST_TOKEN --input-cleaned
```

Recovery refuses live owners. Persistent take reservations remain held until their
own exact tokens are yielded/canceled. Never delete the registry to clear a lock.

## Keep the original target

New ordinary-browser sessions persist the owned Chrome process incarnation,
configured profile and port, and the original CDP page ID. The bounded loopback
target catalogue is read before reconnecting and at observation/input boundaries.
The initial exact URL must identify one page across the owned browser; duplicate
URLs refuse conservatively. A closed original page stays unavailable even when a
replacement has the same URL. A surviving original page may navigate; a stale
action then requires another observation. Old browser sessions without a persistent
page identity must be restarted before public CLI mutation commands can proceed.
The browser still uses one configured profile and port by default; this change
does not create isolated browsers per session.

Explicit bridge tab handles take precedence over URL matching. Missing explicit
handles never fall back to a surviving tab. Native reconnects revalidate the exact
bound window number rather than picking another window. Native window-birth
identity remains unavailable, so reuse of the same window number within the same
process is still a platform limitation. Owned headless `browser cdp` retains its
existing persistent holder, exact target checks, and narrow action set.

The fixed native capability append worker also participates in app ownership,
including its separate durable execution process. Direct library use, older
installed Footwork versions, arbitrary raw driver calls, other OS users and
external applications do not automatically participate. The coordinator cannot
prevent a person moving the pointer or a third-party application changing a
page. For simultaneous independent pointer work, use independently bound desktops
or VM workers. macOS Screen Sharing is not qualified here as a second independent
pointer desktop.

## Validation

The engineering notebook is
[`2026-11-11-desktop-coordination.md`](notebook/2026-11-11-desktop-coordination.md).
Tests exercise separate processes, state update conservation, resource overlap,
reservations, cancellation, stale tokens, dead owners, thread cleanup and target
replacement. Offline fixtures do not establish live macOS coexistence or filmed
capture quality; those require an actual target desktop and recording rehearsal.
