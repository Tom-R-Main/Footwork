# Network browser workbench integration contract

The browser uses a new network Operator; it does not instantiate Bench or AgentBench. BodyClient and the existing body service retain effect authority. The old local operator and its live root remain unchanged.

New modules:

- `workbench_link.py`: `WorkbenchLink(origin, root, port=0).start()` exposes `.origin`, `.state()`, `.set_connected(bool)`, `.arm(mode, operation='dispatch', delay_s=.2)` and `.close()`. Modes `drop_after`, `delay_after`, `duplicate`. Exact payload bytes and identity headers are forwarded. The same journal restarts on its retained port and upstream; faults are diagnostic and bounded. Offline requests close without forwarding. Reconnect never replays. The link may run in the browser process; the body is independent.
- `network_operator_runtime.py`: `initialize(root, body_origin, link_port=0)` sets up an app/client/link root and returns app ID. `Operator(root, policy, start_worker=True)` owns the link and durable client, queue, model cancellation and pending-stage context. Existing `state/frame/enqueue/pause/resume/close` interfaces plus `disconnect/reconnect/reconcile/fault(request)`. A manifest has `app_id` for existing origin guards. State retains existing job/camera/activity fields and adds `connection` and `recovery` described below. Source pins cover new product modules, link, client and unchanged model policy; body pins are separate.
- `network_bench_operator.py`: init/serve CLI and guarded loopback HTTP. Mutations require exact Host, Origin and app ID. POST `/api/disconnect`, `/api/reconnect`, `/api/reconcile` take empty JSON; `/api/fault` takes `{mode, delay_s}` with mode above and delay in [0,2], always dispatch-only. Existing job/pause/resume routes retain their schemas.
- `network_bench_operator.html`: live queue, exact downloaded camera frames, computer measurement, reset result, activity and network controls.

`connection`: `{state: 'connected'|'disconnected'|'unavailable', body_id, adapter_id, epoch, reason, fault: null|{mode, operation, delay_s}}`. Disconnected is the intentional diagnostic gate; unavailable means the real upstream is unreachable. Transport status does not establish freshness of a cached frame.

`recovery`: `{state: 'none'|'uncertain'|'recovered'|'blocked', command_id: null|string, operation: null|string, reason}`. Unknown blocks effects and lease rotation. Reconcile reads exact retained results and applies the pending host stage once; not-seen remains unknown until fenced. Recovered is paused until explicit Resume. UI shows an old frame as retained and never calls it live. Completed results remain visibly historical during disconnect.

The host writes stage/job/action/proposal context and the pre-send client command index before a client command, associates the unique new command, and clears the stage only after applying its result to queue/history. On restart, terminal client receipts may be read to settle that exact stage; unknown receipts remain blocked. No restart sends actions or automatically resumes. Resume observes a fresh TCP image before the next model decision. Control calls cancel pending model work; an unadmitted decision from an earlier control epoch cannot become a command.

Host admission occurs when the checked command stage is durably persisted under the control lock. After this point its network request is in flight and may reach the body after Pause or Disconnect; those controls prevent subsequent admissions. The body separately checks its own lease, freshness and limits before accepting any physical effect. Pause is not an interruption guarantee for a command already admitted by the host. If transport disappears, retain and reconcile that exact command.

The final product replaces the idle old browser server only after separate qualification, retaining its old root. The new workbench and body keep their own private output roots and immutable source identities.
