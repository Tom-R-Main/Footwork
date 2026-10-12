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

References: [integration contract](NETWORK_WORKBENCH_CONTRACT.md), [body adapter](NETWORK_BODY.md), [preregistered experiment](../../jevdual/docs/experiments/SIM10-network-workbench.md).
