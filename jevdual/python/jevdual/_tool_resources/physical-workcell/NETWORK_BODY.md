# Persistent simulated body

The body service retains a MuJoCo bench while a separate client plans from camera images received over TCP. The local service checks proposals and owns every physical effect. This adapter lives inside Footwork's existing workcell package; the browser bench remains a separate local interface.

Start from the repository root with the existing pinned Python environment:

```sh
tools/physical-workcell/.venv/bin/python tools/physical-workcell/body_network.py \
  --root tools/physical-workcell/output/my-network-body --initialize --port 64371
```

Restart the same body by omitting `--initialize`. Body identity, generation, native time, jobs and receipts persist. Restart revokes all leases. The service binds to loopback; this version does not provide authentication or remote deployment.

The body wire and the bench vocabulary now live in separate modules:

| Module | Responsibility |
| --- | --- |
| `body_contract.py` | Adapter/body identity, boot epochs, lease and reconcile schemas, command IDs and digests, receipt envelopes and terminal states |
| `persistent_body_client.py` | Owned client journal, one send intent per command, exact receipt lookup and uncertainty blocking |
| `bench_body_contract.py` | Block job zones, bounded movement, measurement/reset actions, challenge/image bindings and lower unresolved outcomes |
| `body_protocol.py` | Compatibility facade applying the shared wire and bench schemas together |
| `body_client.py` | Existing `BodyClient` bench methods and SHA-verified PNG download |
| `body_network.py` | The simulated bench controller, admission, native execution and lower receipt recovery |

A new operation vocabulary uses `PersistentBodyClient(root, origin, operations)`.
The required `operations` object supplies three hooks:

```python
validate_arguments(operation, arguments)
validate_result(request, result, pinned_identity)
is_unknown(result)  # must return a bool
```

The argument and result hooks must refuse unsupported operations, malformed
schemas and changed bindings. The shared layer verifies the enclosing identity,
request digest, receipt scope and historical epoch. A completed outer receipt
still blocks subsequent commands when `is_unknown` reports an unresolved lower
effect. Receipt recovery uses the same hooks after reopening the client journal.
There is no permissive default operation schema.

The shared modules import no bench or simulator. The development fixture in
`test_body_contract.py` supplies a bounded `aim` operation over real TCP and checks
reply loss, client restart and read-only recovery. Its effect is a synthetic
counter. The production server remains the simulated bench adapter, and shared
identity admission still requires `simulation: true`. A physical controller,
its schema admission and device-specific proof of completion need separate
implementation and qualification.

Changing a pinned module changes the measured source identity. Use a fresh body
and workbench root for the new source; old roots are never silently migrated.
The existing client event-publication and pre-send instruction windows remain
outside the selected workbench recovery qualification. An unresolved host stage
without a durable client command identity must stay blocked; it cannot authorize
reconstructing or resending the action.

The Python client provides the action boundary. To try the following example from the repository root, start an interpreter with:

```sh
PYTHONPATH=tools/physical-workcell tools/physical-workcell/.venv/bin/python
```

```python
from body_client import BodyClient, Uncertain

client = BodyClient("tools/physical-workcell/output/my-network-client",
                    "http://127.0.0.1:64371")
client.acquire()
client.start_job("desk-job-1", {
    "x_min": .035, "x_max": .105, "y_min": -.025, "y_max": .025,
})
challenge = client.observe()  # SHA-verified PNG downloaded into the client root
# A visual model chooses action, intent and finite target coordinates.
proposal = client.propose(challenge["challenge_id"], "move",
                          "Approach the block from its left side", -.25, 0)
try:
    result = client.dispatch(proposal["proposal_id"])
except Uncertain as uncertain:
    receipt = client.reconcile(uncertain.command_id)  # reads; never resends
client.close()
```

The example is one approach move, not a complete manipulation policy. The frozen qualification runner uses actual Codex image decisions for placement, measurement, contact reset and a second job. It needs the already authenticated Codex CLI and retains model inputs, decisions, usage and process outcomes.

```sh
tools/physical-workcell/.venv/bin/python tools/physical-workcell/qualify_network_body.py \
  --root tools/physical-workcell/output/my-network-qualification \
  --source-commit COMMITTED_SOURCE_SHA
tools/physical-workcell/.venv/bin/python tools/physical-workcell/score_network_body.py \
  --root tools/physical-workcell/output/my-network-qualification
```

Run the scorer after the runner has stopped its service and proxy. It reads native states and SQLite separately from planning. Results and the qualification scope are recorded under `jevdual/results/network-body-adapter-20261011/` when available.

Commands have persistent IDs and content digests. Exact duplicates return the historical receipt. Changed arguments under the same ID refuse. If a reply disappears, the client records an unknown outcome and blocks new commands. Receipt lookup can settle a completed command; an expired or revoked lease can prove that an unaccepted command cannot arrive later. An accepted intent without lower-level proof remains unknown. Neither restarting nor reconnecting clears it.

A lease limits admission of new commands. An already admitted action can finish after a disconnect within the existing local force, speed and time limits. This prototype does not claim an emergency stop, robot safety certification, hardware recovery, power-loss durability or secure control across machines.

The diagnostic fault proxy injects bounded delays, discarded requests/replies and exact duplicates. Crash barriers are enabled only for test services and intentionally stop the owned service process so the harness can test receipt recovery. They are absent from normal startup.

Reference: [protocol and ownership](NETWORK_CONTRACT.md); [preregistered experiment](../../jevdual/docs/experiments/SIM9-network-body-adapter.md).

Verification recipe (from this directory):

```sh
.venv/bin/python -m unittest -v test_body_contract test_body_network test_body_client test_network_body_faults
../../jevdual/.venv/bin/ruff check body_contract.py bench_body_contract.py persistent_body_client.py \
  body_protocol.py body_network.py body_client.py \
  network_fault_proxy.py qualify_network_body.py score_network_body.py \
  test_body_contract.py test_body_network.py test_body_client.py test_network_body_faults.py
```

The twelve-case matrix covers network delay, dropped traffic, concurrent duplicates, stale proposals, lease and identity fences, retained restarts, read-only receipt recovery and unresolved crash intents. Server/client checks cover bounded schemas, ownership, malformed replies and image integrity. The actual-model run and its separate scorer qualify the complete camera-to-motion-to-computer workflow; deterministic checks alone do not establish model performance.
