# SIM4: Independent simulated controller recovery

Mode: headless local diagnostic and actual-process fault conformance; no robot qualification.

## Hypothesis

A separately running controller can finish bounded image-bound operations after its caller
disconnects, and a returning caller can reconcile durable history without repeating motion.
Cancellation requests can be distinguished from verified controller stop; restart changes
incarnation without inventing missing execution history from a currently satisfied scene.

## Scope and caller

Keep this under tools/physical-workcell in Python with the pinned native MuJoCo engine.
An initialized SIM3 episode is owned exclusively by one controller process. Local private
Unix-socket clients use health, observe, submit, status and cancel. Submission binds a safe
operation ID, exact retained proposal bytes/digest, frame generation and source/case identity.
Only the existing image-guided gate admits motion or conditional local software staging.
The service persists acceptance before acknowledging it and dispatch intent before execution.
The caller may disappear without owning the controller's lifetime.

Use an owned private controller directory separate from the episode's initialization files.
Hold the existing episode lock for the controller's lifetime so legacy commands cannot race
the service. Keep observations free of native poses. Preserve SIM1-SIM3 behavior by default;
add narrowly scoped cooperative cancellation/pacing hooks rather than another physics policy.
Controller status reports historical outcome separately from current evidence.

## Cancellation and restart

Before dispatch, cancellation can prevent the operation. During motion it stops advancing the
target and holds the last commanded actuator target, then performs bounded native settling.
No block teleport, velocity assignment or state reset is allowed. A terminal cancelled result
requires retained state and stop evidence; failure to establish stop remains unknown. Terminal
completion wins a late cancellation race. Computer publication cannot be undone by cancellation.

Each process has a new incarnation. On restart, terminal retained results remain historical;
an incomplete controller record may be reconciled only from an exact bound lower-layer
terminal receipt. Missing/unknown execution evidence remains unknown and blocks further
effects. Accepted-but-undispatched work is never silently replayed. Current placement alone
cannot manufacture a historical result. Source or case changes refuse reuse.

## Checks and measurement

Primary metric: required process-level lifecycle scenarios whose observed state and receipt
history match their expected outcome, with all attempts and failures retained. Cover:

1. Disconnect after durable submit; reconnect to the same ID after completion; no replay.
2. Return while motion is active; observe reports busy and status remains nonterminal.
3. Cancellation before dispatch prevents motion and increments no native generation.
4. Cancellation during native movement reaches a bounded verified stop or stays unknown.
5. Lost controller reply/result after a lower-layer terminal receipt reconciles on restart.
6. Kill the controller during motion; new incarnation retains unknown history and refuses replay.
7. Current scene satisfies an order but execution receipts are unavailable; no success claim.
8. Normal image-guided contact and verified local artifact completion through the service.

Challenge malformed/conflicting IDs and proposals, stale bindings, second owner, changed
source/case and terminal cancellation. Run existing physical-workcell regressions and lint.
Use separate private development cases. Freeze the runtime before the parent independently
drives a new diagnostic set through public clients; do not call these heldout/model benchmarks.
All sleeps/waits are bounded; retain owned process handles and clean up only those resources.
No visible desktop, live camera, model API, installs, production capability-service changes or
external application writes are required. Screensaver and sleep behavior are not qualifications.

## Decision

Adopt the controller lifecycle only if independent process runs demonstrate caller-independent
execution, no duplicate movement, truthful cancellation and conservative restart history.
Otherwise preserve failures and narrow claims. Actual application handoff and physical adapter
promotion remain separate subsequent packages.

## Result

Frozen runtime 5713173 passed 68 scoped tests and Ruff. Nine independent public-service
checks plus a separately preregistered native-step observation probe support all eight
required lifecycle scenarios. Caller loss did not repeat effects; cancellation retained
verified simulated stop evidence; restart reconciled intact lower receipts and kept missing
history unknown. Deliberate current-artifact tamper preserved historical staging while
blocking new effects. All owned trial processes exited and sockets were removed.

The first development implementation failed targeted recovery/binding/ownership checks;
those failures and the corrected prediction are retained. The original timed crash trial
did not prove native stepping; a fresh supplemental case confirmed a real native step
before SIGKILL without changing source/dynamics. Controlled record/history/timing faults
are distinguished from live disconnect and kill. This is process-level simulation evidence,
not hardware, power-loss, AI superiority or application-workflow qualification.

See [report and complete limits](../../results/independent-controller-20261010/report.md),
[qualified evidence](../../results/independent-controller-20261010/qualification.json) and
the engineering notebook for failed and revised predictions.
