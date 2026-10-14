# Independent simulated controller (SIM4)

The controller is a separate local process that owns an initialized SIM3 episode. A client can
submit an image-bound proposal, disconnect and later read its durable result. Native motion
runs in a worker thread; the service thread answers socket requests and renders fresh observations
when idle. This remains an isolated MuJoCo simulation package. It uses no model API, real camera,
external application or production capability-service change.

Initialize a fresh episode with [EPISODES.md](EPISODES.md) before starting the service. Keep the
controller directory separate from the episode directory, inside the existing private
`tools/physical-workcell/output` tree. Do not reuse SIM3 qualification outputs with changed source.

## Start and contact the service

```sh
tools/physical-workcell/.venv/bin/python tools/physical-workcell/controller.py serve \
  --run-dir ABSOLUTE_INITIALIZED_EPISODE_DIRECTORY \
  --controller-dir ABSOLUTE_PRIVATE_CONTROLLER_DIRECTORY
```

Run this as an owned independent process and retain its process handle and log. The service holds
the existing episode lock for its lifetime; legacy image/body/episode commands and a second
controller cannot concurrently acquire that episode. It also owns a separate controller lock.
Socket clients operate through the service, without acquiring the episode lock themselves.

```sh
tools/physical-workcell/.venv/bin/python tools/physical-workcell/controller.py health \
  --controller-dir ABSOLUTE_PRIVATE_CONTROLLER_DIRECTORY

tools/physical-workcell/.venv/bin/python tools/physical-workcell/controller.py observe \
  --controller-dir ABSOLUTE_PRIVATE_CONTROLLER_DIRECTORY
```

`health` returns `current_incarnation`, `current_health`, the active operation ID, and owned paths.
Each service process gets a new incarnation. Read its UUID before an effect request. Idle health
checks retained state and, after staging, the current exact software artifact. Historical staging
can remain true while a missing or altered current artifact makes current health blocked.

An idle `observe` returns a fresh generation-bound image packet under `observation`, with the
same RGB, task, calibration, perception and budget fields as the existing image-guided route.
Inspect its PNG before proposing an action. While a goal is active, `observe` returns `busy`
without an observation packet; it cannot offer an old image as fresh authority. Unresolved
history or shutdown similarly withholds fresh action authority. Native poses stay private.

## Submit, reconnect and cancel

Prepare a proposal from the current observation using the exact
[proposal schema](proposal.schema.json). Save its bytes privately and compute their SHA256.
Both submit and cancel require the UUID from the current health response:

```sh
tools/physical-workcell/.venv/bin/python tools/physical-workcell/controller.py submit \
  --controller-dir ABSOLUTE_PRIVATE_CONTROLLER_DIRECTORY \
  --expected-incarnation CURRENT_INCARNATION_UUID \
  --operation-id YOUR_SAFE_OPERATION_ID \
  --proposal-file ABSOLUTE_PROPOSAL_FILE --proposal-sha256 EXACT_PROPOSAL_SHA256

tools/physical-workcell/.venv/bin/python tools/physical-workcell/controller.py status \
  --controller-dir ABSOLUTE_PRIVATE_CONTROLLER_DIRECTORY \
  --operation-id YOUR_SAFE_OPERATION_ID

tools/physical-workcell/.venv/bin/python tools/physical-workcell/controller.py cancel \
  --controller-dir ABSOLUTE_PRIVATE_CONTROLLER_DIRECTORY \
  --expected-incarnation CURRENT_INCARNATION_UUID --operation-id YOUR_SAFE_OPERATION_ID
```

The service persists exact proposal bytes, operation identity and acceptance, including a file
and parent-directory sync, before acknowledging submission. It persists running/dispatch intent
before calling the existing image-guided `apply`.
That gate continues to own freshness, perception, calibration, movement limits, completion and
conditional computer publication. The controller chooses no target and supplies no native guidance.

Only one goal may be active. Repeating an ID with identical proposal bytes returns its history;
conflicting bytes refuse. One operation ID owns each proposal token, so another ID cannot alias
the same lower effect. Readbacks and repeat submissions dispatch nothing. Closing a client socket
does not stop the worker. A stale incarnation refuses submit/cancel before changing a goal.

The goal `phase` is `accepted`, `running`, `executed`, `staged`, `cancelled`, `refused` or `unknown`.
`accepted` and `running` are nonterminal. `historical_outcome` reports a terminal goal result;
`current_health` and `current_incarnation` describe the service now. `accepted_incarnation`
retains the original process identity. A terminal lower result appears under `receipt`.

`cancel_requested` acknowledges an instruction; it is not stop proof. Before dispatch, a
cancelled goal records `cancellation_stage: before_dispatch` and performs no native action or
generation increment. During motion, cancellation stops advancing the actuator target, holds
the last command and performs bounded native settling. It never assigns body position or velocity.
Terminal `cancelled` requires a persisted integration state and measured stop evidence; failed
stop verification remains `unknown` and blocks more effects.

For motion cancellation, `stop_evidence` includes the native steps completed before cancellation,
linear/angular velocity measurements and limits, held actuator command, settle steps, and exact
`retained_generation`/`retained_state_sha256`. The controller's cancelled goal is distinct from
the lower receipt's `executed` movement phase. `target_trajectory_completed` states whether the
original command trajectory finished; partial movement does not imply arrival at its target.
A late cancellation of an already terminal goal changes nothing. Staged computer effects cannot
be undone by cancellation.

## Shutdown and restart

Send SIGTERM to the exact owned service process. It requests cooperative cancellation, joins
the bounded native worker, records shutdown and removes its owned socket before releasing the
episode lock. SIGKILL cannot run that cleanup; it may leave accepted/running history and an owned
stale socket. The next service incarnation cleans up that socket only after ownership/type checks
and confirmation that no live listener occupies it.

If the native worker is still alive after the 15-second shutdown join, the controller records an
active nonterminal goal as unknown when possible and aborts the whole process with exit code 2.
It does not release its episode/control locks while that worker can write. No verified stop or
clean shutdown is claimed; the socket remains for the next incarnation's owned stale-socket
cleanup. Already terminal historical goals remain unchanged. Restart still requires exact lower
receipts to reconcile an unresolved result and never dispatches it again.

Restart with the same episode and controller directories. Source, case and run bindings must
still match. Terminal records remain historical. Accepted/running records never automatically
dispatch again. An incomplete controller result may be reconciled read-only from exact terminal
image and native receipts, original request bytes, frame/source/case bindings and a verified
retained integration state. The new incarnation is reported separately from the old acceptance.
An `unknown` controller record is also eligible for that exact receipt-only reconciliation,
including a failed final controller write after the lower layers finished. If those receipts
cannot establish the result, it remains unknown.

Missing or corrupted current integration state does not erase a retained terminal goal. The
service can start in a historical-only mode and report that outcome alongside unknown current
health and its reason. Fresh observation and new submission are withheld. A changed source/case
binding still refuses service reuse; historical-only mode does not bypass those bindings.

A missing or pending image receipt, including a native-only terminal receipt gap, stays unknown.
The controller does not call `apply` during recovery or repair the image journal. Current placement
cannot manufacture execution or software-staging history. This recovery scope covers a lost
controller result with intact lower receipts, not every lower-layer interruption window.

## Transport and diagnostic timing

The service exposes a private owned Unix socket. Its short deterministic path is stored in
`controller-binding.json` and lives under the private `output/.s` directory. Each connection sends
one UTF-8 JSON object terminated by a newline and receives one newline-terminated JSON object.
Request size is at most 8192 bytes, read timeout 2 seconds, and client timeout 5 seconds. Duplicate
keys, extra fields, malformed IDs and changed bindings refuse.

RPC fields match the CLI names with underscores: `command`, and for submit `operation_id`,
`proposal_file`, `proposal_sha256`, `expected_incarnation`; cancel uses `operation_id` and
`expected_incarnation`; status uses `operation_id`; health/observe use only `command`.

For process-level fault checks, `serve` accepts `--dispatch-delay-s` from 0 to 5 and `--pace-s`
from 0 to 0.003 seconds per native step. Defaults are zero. Each incarnation records these
diagnostic settings. Pacing changes wall time, not physics timestep, command speed or action bounds.
Development tests use separate private cases and real service/client processes. SIM3 qualification
episodes are preserved; results from deterministic helpers are not AI trials.
File/directory sync supports the acceptance mechanism; these process-fault checks do not qualify
machine failure or power-loss recovery.

Preregistration: `jevdual/docs/experiments/SIM4-independent-controller-recovery.md`.
Notebook: `jevdual/docs/notebook/2026-10-10-independent-controller-recovery.md`.
