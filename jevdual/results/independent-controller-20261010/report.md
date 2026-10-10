# SIM4: Independent simulated controller recovery

The simulated body now has a separate process owner. A caller can submit an image-bound
operation, disconnect and return to its retained result without repeating movement.
Cancellation, completed history and current state have distinct evidence. Restart resolves
a lost controller result only when exact lower-layer receipts support it; otherwise the
operation stays unknown and blocks effects.

Frozen runtime: `5713173`. Original preregistration: `c78d2a4`; corrected prediction:
`637666c`; supplemental observation prediction: `578d73d`. All 68 scoped native/renderer
and process tests passed, including 18 controller scenarios; Ruff passed. The independent
driver ran nine public-service checks once each, followed by one fresh supplemental crash
probe. Together they support all eight required lifecycle scenarios, including deliberately
blocked outcomes. This is a small process diagnostic, not a reliability estimate or AI benchmark.

| Required scenario | Observed outcome |
|---|---|
| Caller disconnects before receiving reply | Controller finished; same ID returned exact history, generation and state without another effect |
| Caller returns during work | Status stayed nonterminal; observe returned busy without an authoritative image |
| Cancel before dispatch | Cancelled, with no native operation or generation change |
| Cancel during movement | 156 native steps before cancellation, 500 settling steps, retained generation and independently checked velocity limits |
| Lost controller terminal result | Controlled saved unknown record reconciled from intact exact image/native receipts under a new incarnation |
| Controller dies during movement | Restart stayed unknown; no replay or stale-incarnation effect; supplemental trace confirmed a real native step before death |
| Satisfied scene without execution history | Native condition held, but missing receipts kept controller history unknown |
| Physical fulfillment and computer result | Four contact movements followed by fresh visual/native completion and a Footwork-checked saved order |

Additional admission checks covered malformed/conflicting identity, stale frame/incarnation,
exclusive ownership and changed bindings. Deliberate artifact-byte tamper preserved historical
staging while current checking failed and new work was refused.

## Implementation and use

[controller.py](../../../tools/physical-workcell/controller.py) exposes private Unix-socket
health, observe, submit, status and cancel commands. The service owns both its controller
directory lock and the episode lock for its lifetime. Clients bind effect requests to the
current incarnation and an operation ID with exact proposal bytes. A second owner and legacy
episode commands cannot race it. Acceptance and dispatch intent are persisted before their
respective acknowledgement and execution.

The existing image gate admits proposals. The controller chooses no target and provides no
native pose guidance. Native stepping runs in a worker; rendering stays on the service thread
when idle. Optional diagnostic pacing changes wall time, not simulation timestep or command
bounds. Default legacy motion behavior remains unchanged.

During cancellation, the controller holds the last actuator command and settles through real
native dynamics. It does not assign position or velocity. A cancelled goal can include executed
partial movement; it does not mean the original target was reached. Stop evidence binds the
retained generation and state digest. The independent parent restored that state and measured
block linear speed below 0.002 m/s, angular speed below 0.02 rad/s and pusher speed below
0.002 m/s. These are simulated velocity predicates, not hardware interlocks.

History stays readable when current integration state is unavailable. Fresh observation and
new effects remain withheld. Exact recovery checks proposal/frame/source/case, native request,
work-order/model and historical integration-state digests. It never dispatches during restart
and never substitutes current placement for missing execution history.

SIGTERM requests cooperative cancellation and joins the worker. If its bounded join expires,
the whole owning process aborts before either lock scope unwinds. Unfinished history remains
unknown, with no stopped claim. Restart handles the owned stale socket. This avoids a live
worker writing after ownership was released.

Use the [public controller recipe](../../../tools/physical-workcell/CONTROLLER.md) with a
fresh initialized episode and a separate private controller directory. Code remains Python
inside `tools/physical-workcell`, with MuJoCo doing native physics. No core Footwork physical
adapter or extra runtime dependency was introduced.

## Evidence and retained failures

[qualification.json](qualification.json) contains the independent case summary, original
private evidence/driver paths and hashes, supplemental native-step proof, cleanup and parent
read-only scoring. [checks.json](checks.json) records the final 68-test suite and Ruff;
[source-freeze.json](source-freeze.json) identifies exact runtime/test/documentation hashes.

The private reproducer and full public replies remain at
`tools/physical-workcell/output/s4audit/driver.py` and `verification.json`. The supplemental
driver/proof remain under `output/s4parent/`. Both preserve their owned inputs and processes.
Use a new namespace for another diagnostic; do not overwrite the retained runs.

The original timed running-kill trial established dispatched uncertainty and no replay, but
could not prove native stepping from its post-crash files. A separately preregistered fresh
probe wrapped the real `mj_step` call, forwarded its inputs and return unchanged, and wrote
an observation-only marker after its first return. The marker identifies the killed PID and
the native motion caller before SIGKILL. Restart used the uninstrumented frozen controller.
Tracing added observation overhead; no source, native dynamics or proposal settings changed.
Both trials are retained, rather than presenting the first trial as stronger evidence.

[development-attempts.json](development-attempts.json) retains failure summaries and private
log hashes. The initial driver had nine startup failures from incorrect socket discovery;
no goals were sent. Another driver assertion excluded a correctly blocked observation.
Product regressions failed before fixes for unknown-fallback reconciliation, live retained
binding validation and shutdown ownership. A source review also separated historical status
from unreadable current state and added directory sync before acceptance acknowledgement.
The pre-shutdown 67-test pass remains separately recorded: passing that suite did not cover
the ownership defect later reproduced with a slow read-only checker and shortened join.

The first notebook prediction is marked failed; the corrected and supplemental predictions
are resolved against the frozen independent evidence. Controlled saved-record/history faults
and the shutdown timing injection are explicitly distinct from live socket loss and SIGKILL.

## Limits and next decision

All owned diagnostic processes exited and their automatic sockets were removed. Parent
native/file scoring preserved run-file hashes. The physical/software trial's original saved
order was independently checked again after its deliberate current-file tamper; the tampered
current file is not claimed correct. Raw negative-test artifacts remain intact.

This qualifies simulated process ownership and bounded recovery paths. It does not qualify
power loss, hardware, a real camera, general perception, real-time scheduling or application
fulfillment. A native-only terminal receipt with a pending image wrapper stays unknown; this
package does not repair every lower-layer interruption window. The comparative value of AI
planning remains unmeasured here; diagnostic targets came from a deterministic RGB helper.
Screensaver/sleep behavior was not tested, and the workflow required no visible desktop.

Adopt this controller in the experiment area. The next useful package is a versioned local
browser work-order application: bind an order, stage the part, verify placement, update that
same order and read its saved state. Include an order changed/cancelled during movement and
a lost application reply. Promote a physical adapter into Footwork core only when a real
capability-service caller needs the qualified lifecycle.
