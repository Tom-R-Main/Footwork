# Browser workbench with a persistent body

The browser queues camera-guided inspection jobs against a separate simulated body over TCP. The body retains its identity, motion state, measurements and contact resets. The browser host keeps its queue and model history separately. Each job places the part, records its visible footprint with the computer-side measurement worker, then returns the part and pusher home.

Start a new body from the repository root:

```sh
tools/physical-workcell/.venv/bin/python tools/physical-workcell/body_network.py \
  --root tools/physical-workcell/output/my-workbench-body --initialize --diagnostic --port 64371
```

In a second terminal, initialize and serve the browser host:

```sh
tools/physical-workcell/.venv/bin/python tools/physical-workcell/network_bench_operator.py init \
  --root tools/physical-workcell/output/my-network-workbench --body-origin http://127.0.0.1:64371
tools/physical-workcell/.venv/bin/python tools/physical-workcell/network_bench_operator.py serve \
  --root tools/physical-workcell/output/my-network-workbench --port 64372 --backend codex
```

Open the reported browser URL. Add an inspection, choose Near or Far, and add another job to the queue. The existing authenticated Codex CLI plans from exact camera images downloaded over TCP. New jobs can trigger model requests; Pause cancels planning and prevents the next command admission. A command already recorded as in flight may reach the body and finish after Pause. The body still applies its local bounds.

Expand **Test the simulated connection** to lose, delay or duplicate the next dispatch reply. These controls exercise the network boundary around the same local guards. A duplicated command keeps its identity and returns its retained result. Losing a reply creates an uncertain outcome and blocks further effects.

Use **Disconnect** to close the diagnostic link. The last image and completed results remain visible as retained evidence. **Reconnect** restores transport and leaves the agent paused. For an uncertain command, choose **Check receipt**. This reads the exact original result without resending its action. If the receipt proves what happened, choose **Resume** to obtain a fresh observation and continue. Missing proof stays blocked.

**Checking body** means an auxiliary health reply is delayed. Planning may continue; every command still needs a fresh pinned body check before a lease and command stage are accepted. A cached image or old health result supplies no action authority. A known disconnect, changed boot or identity, unresolved effect, or failed command preflight still stops progress. Pause and uncertain-command recovery require the same explicit controls as before.

Restart the body by omitting `--initialize`; restart the host with the same root and exact port. Both identities persist. Body restart revokes leases. Host restart pauses the queue, keeps uncertain commands, and never replays them. Reloading the browser does not restart planning or reset the bench.

A new body boot epoch also pauses planning when a fast restart escaped the outage poll. An earlier model decision cannot acquire authority to continue across that boundary. Pending historical commands keep their original epoch and identity: **Check receipt** reads their retained result, then **Resume** obtains a fresh observation. Workbench restart cancels its owned planner before releasing process ownership; its active unfinished job appears paused or uncertain as appropriate.

For a repeatable mid-job restart trial, use `qualify_workbench_restarts.py run --root NEW_ROOT --source-commit COMMITTED_SOURCE_SHA`. The harness owns the body and workbench processes. Its `request` command checks the current planning or uncertain-command predicate before stopping a role, and restarts only that role at its retained root and port. Browser actions still perform receipt recovery and Resume. Run `score_workbench_restarts.py --root NEW_ROOT` after the harness finishes. These trials cover graceful process restarts; forced termination during native persistence needs a separate experiment.

The link, client, queue, model inputs and receipts live beneath the host root. Native state and measurement SQLite remain beneath the separate body root. An independent post-trial scorer reads the native records after the trial processes stop; they are not model inputs. The previous local workbench uses different source files and roots.

Qualification uses committed source:

```sh
tools/physical-workcell/.venv/bin/python tools/physical-workcell/qualify_network_workbench.py \
  --root tools/physical-workcell/output/my-browser-qualification --source-commit COMMITTED_SOURCE_SHA
```

The harness prints the browser URL and owns both trial processes. Drive the recovery sequence through the UI; retain browser observations with `record_network_workbench.py`. Write `stop-request.json` in the trial root when the queue is finished. Then run `score_network_workbench.py --root` against that root. The scorer checks native placement, SQLite, contact reset, model images and receipts, transport send counts, and the browser transition ledger.

This version binds to loopback and controls a simulation. The queue and model/command journals have finite budgets. It does not provide authenticated control across machines or qualify physical hardware.

To qualify delayed health checks, run `qualify_workbench_health.py trial --root NEW_ROOT --source-commit COMMITTED_SOURCE_SHA`. Its owned relay delays only tagged auxiliary identity/state replies by 1.2 seconds. Full command checks and effect payloads pass through unchanged. Retain a `healthy_checking` browser step while a job runs, plus the usual uncertain-command recovery steps. The owned `health-relay-control.json` accepts `{"enabled":true,"paths":["/state"]}` to exercise state checks separately, or `{"enabled":false,"paths":[]}` to turn injection off. Stop through `stop-request.json`, then run `score_workbench_health.py --root NEW_ROOT`. The score checks fresh pinned proof before every command, zero unexpected halts or cancelled decisions, and joined health readers, in addition to native placement, measurement, reset and receipt recovery.

References: [integration contract](NETWORK_WORKBENCH_CONTRACT.md), [body adapter](NETWORK_BODY.md), [preregistered experiment](../../jevdual/docs/experiments/SIM10-network-workbench.md).

Hard-crash qualification uses `qualify_workbench_crashes.py run --case CASE --root NEW_ROOT --source-commit COMMITTED_SOURCE_SHA`. Each case owns fresh simulation processes and records a SIGKILL exit, exact command identity and retained evidence. `host-inflight` holds a completed body reply before killing the workbench. `body-native-gap` kills the body after native state is saved but before its completion receipt is committed. These two gates fire automatically. For `body-uncertain` and `host-uncertain`, use **Lose next reply** in the browser, then request the matching role's crash with `request --root NEW_ROOT --action crash-role --role body` or `--role workbench`.

Capture the outage, then use `request --root NEW_ROOT --action start-role --role ROLE`. Reload after a workbench restart. **Check receipt** reads the original command; where a conclusive result exists, the agent remains paused until **Resume**. A native receipt gap stays blocked even after another receipt check: saved motion or a familiar camera position cannot prove completion. This case cannot complete its job or accept another effect. Keep the unresolved root as evidence.

Retain browser text and screenshots with the harness's read-only `record` command; it labels unavailable host state separately from cached evidence. Finish with `request --root NEW_ROOT --action finish`, then independently run `score_workbench_crashes.py --root NEW_ROOT` before restarting that root for handoff. The trial has a twenty-minute bound. These selected process-kill gates do not qualify arbitrary instruction-level crashes, power loss, physical hardware or a host killed during active planning. See [SIM13](../../jevdual/docs/experiments/SIM13-workbench-hard-crashes.md).

The host validates its immutable event journal on startup. A complete event saved just before its manifest index is retained as history; it does not prove that an action completed. An unfinished command still requires **Check receipt**, followed by explicit **Resume**. Missing, conflicting, malformed or noncontiguous history refuses startup instead of overwriting evidence.

AI planning runs under a supervisor with a host-liveness pipe and a call ownership lock. Restart waits for proven planner cleanup, changes the planning owner and pauses unfinished jobs. An old model reply cannot authorize a new action. If cleanup proof is missing, restart refuses control. **Previous planner retired** in Activity explains when Resume can request a fresh image.

To test these selected host interruption windows, run `qualify_workbench_recovery.py run --case host-publication --root NEW_ROOT --source-commit COMMITTED_SOURCE_SHA`, or use `--case host-planning` with a separate fresh root. The diagnostic launcher stops the host after publishing the first executed move's audit event, or while the actual Codex planner is active. The harness kills only its registered host PID; the planner supervisor must clean up independently. Capture `crash-offline`, request `start-role --role workbench`, reload and capture `restored`. For the publication case, use **Check receipt** and capture `recovered` while paused. Then explicitly **Resume**, capture `resumed`, and retain `completed` after measurement and contact reset. Capture each step through the harness's `record` command with the actual browser text and screenshot. Finish with `request --action finish`, then run `score_workbench_recovery.py --root NEW_ROOT` after the actors stop. See [SIM14](../../jevdual/docs/experiments/SIM14-reusable-body-recovery.md).

The shared identity, lease and receipt contract and durable transport now live in `body_contract.py` and `persistent_body_client.py`. Bench operations and camera-result validation live in `bench_body_contract.py`; existing callers use the `BodyClient` facade. Another adapter must supply explicit argument, result and lower-uncertainty schemas. The current identity admission remains simulation-only. A physical controller needs its own qualified bounds and evidence before it can use this contract.
