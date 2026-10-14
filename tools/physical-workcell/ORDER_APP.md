# Browser orders and physical fulfillment (SIM5)

This local application connects a versioned browser order to the existing image-guided
simulator and independent controller. SQLite records order revisions, immutable leases and
application fulfillment receipts. The browser shows the actual native RGB workcell image;
the host still plans physical actions through the public handoff tools.

The application binds only to IPv4 loopback. It uses Python's standard library, SQLite and
plain HTML/JavaScript, with the existing pinned physical environment for controller verification.
It uses no model provider, credentials, external application or production capability-service
protocol. Shared same-user fixtures and process checks are not a production security claim.

## Initialize and serve

Prepare a private JSON order containing exactly the existing work-order fields plus `revision`
and `state`:

- `version`: 1
- `order_id`: an exact bounded safe identity
- `project`: exactly `namespace` and `project_id`
- `part_id`: `block`
- `target_zone`: exactly `x_min`, `x_max`, `y_min`, `y_max`, as finite bounded coordinates
- `revision`: a positive bounded integer
- `state`: `open` or `cancelled` at initialization

A seeded `fulfilled` state refuses because it has no real application receipt. Target zones
retain the existing tabletop bounds: x within −0.35 to 0.35 m, y within −0.2 to 0.2 m, with
strictly increasing minimum/maximum edges.

```sh
shasum -a 256 ABSOLUTE_ORDER_FILE

tools/physical-workcell/.venv/bin/python tools/physical-workcell/order_app.py init \
  --app-dir ABSOLUTE_PRIVATE_APP_DIRECTORY \
  --order-file ABSOLUTE_ORDER_FILE --order-sha256 EXACT_ORDER_SHA256

tools/physical-workcell/.venv/bin/python tools/physical-workcell/order_app.py serve \
  --app-dir ABSOLUTE_PRIVATE_APP_DIRECTORY --port 0
```

Use an owned private directory under `tools/physical-workcell/output`. Initialization retains
the seed, immutable `app_id`/store identity, source fingerprints and SQLite store binding.
Identical initialization returns the existing order; another seed, altered source/store or
unreceipted partial setup refuses reuse. No implicit reset exists.

Run the server as an owned process and retain its handle. `readiness.json` records its actual
`http://127.0.0.1:PORT` origin, PID, server incarnation and source fingerprints. Open that origin
in the isolated browser. Restart the same application with the exact previous actual port:

```sh
tools/physical-workcell/.venv/bin/python tools/physical-workcell/order_app.py serve \
  --app-dir ABSOLUTE_PRIVATE_APP_DIRECTORY --port PREVIOUS_ACTUAL_PORT
```

The app identity, leases, origin and receipts survive restart; the server incarnation changes.
Changing the origin or requesting another ephemeral port after initial startup refuses.
Explicit origin rebinding is outside this package. One app-directory lock excludes a second
server. Graceful shutdown joins active request handlers before releasing ownership.

## Browser flow

Read the order ID, revision and requested staging region. **Bind current revision** creates
one lease for that application/order/revision. A repeated exact binding operation returns the
same lease; a different binding operation for an already leased revision refuses.

The lease retains the exact work order and its canonical SHA256, stable physical and application
completion IDs, and server-assigned private directories. The work-order digest uses sorted,
indented JSON plus a final newline, matching the simulator's canonical encoder. The server
assigns `APP/workcells/LEASE/{r,c,h}` for the episode, controller and handoff journal. Browser
requests cannot select another run, controller, artifact path or success flag.

Use the separate [handoff adapter](app_handoff.py) to prepare the lease's physical episode,
inspect fresh RGB and submit image-bound proposals. The host chooses targets. The physical
completion operation and proposal token must both equal the lease's `physical_completion_id`.
No adapter call fulfills the application on its own.

The browser's workcell panel shows the SHA-checked actual PNG from the assigned live controller.
A busy or unknown controller supplies no fresh frame. A cached image is labeled with its last
observed generation and unavailable current evidence. Acquired images with unsupported recognition
or calibration remain visible, while the UI withholds verification. No generated scene or native
pose is presented as current evidence.

After a staged physical receipt, choose **Verify and fulfill**. The app independently checks
the assigned controller's exact staged operation, current artifact byte check, fresh RGB/calibration,
task intent, work-order digest, part/zone and bound image/state generation. It then rereads the lease
and current order in a SQLite transaction. Only the same still-open revision can advance to
`fulfilled`. The revision update and one application receipt commit together.

**Edit target** and **Cancel order** advance the revision. The handoff guard withholds more
submissions for a changed/cancelled lease and requests cooperative cancellation for an active
goal. Motion already admitted may partially execute; cancellation does not roll it back. A stale
lease cannot fulfill even if physical staging later succeeds. No atomic physical/application
transaction is claimed.

## Public API and readback

GET routes:

- `/api/health`: `app_id`, `app_dir`, exact `origin`, `server_incarnation`, readiness and fingerprints
- `/api/orders`: current orders
- `/api/orders/ORDER_ID`: `{app_id, order}`
- `/api/leases/LEASE_ID`: `{app_id, lease}`
- `/api/leases/LEASE_ID/frame`: current SHA-checked PNG, with generation/perception/calibration headers
- `/api/operations/OPERATION_ID`: `{app_id, receipt, current_order, historical: true}`

Missing identities return HTTP 404 with `phase: unavailable`. Mutations require the exact loopback
Host and Origin plus one `X-Footwork-App-ID` header matching the immutable app identity from health.
The server checks that identity before any mutation, so a cached page cannot edit a replacement
application that later reuses the same port. Writes also require one bounded JSON body and exact fields. Duplicate keys, nonfinite values, extra
fields, conflicting identities and unsupported evidence refuse with HTTP 409. No redirects or
cross-origin write authority are provided.

POST routes under `/api/orders/ORDER_ID/`:

| Route | Exact JSON fields |
| --- | --- |
| `bind` | `expected_revision`, `binding_operation_id` |
| `edit` | `expected_revision`, `target_zone` |
| `cancel` | `expected_revision` |
| `fulfill` | `lease_id`, `completion_operation_id` |

For example, a bind request sends `Content-Type: application/json`, the current exact `Origin`
and `X-Footwork-App-ID`, with this body (replace the revision and operation ID for the actual order):

```json
{"expected_revision": 1, "binding_operation_id": "bind-current-order"}
```

Bind returns `{app_id, lease, order, historical}`. Fulfillment returns the operation readback
envelope. The completion operation ID is assigned by the server and stays stable across a lost
reply. Exact repeated completion looks up the committed receipt before consulting potentially
unavailable current physical evidence; it returns that original receipt and the current order.
Conflicting operation/lease reuse refuses and creates no second effect.

Application receipt fields include `app_id`, `order_id`, `lease_id`, `completion_operation_id`,
`physical_completion_id`, `leased_revision`, `fulfilled_revision`, `work_order_sha256`, saved state
and commit time. `physical_proof.historical` explicitly labels the proof at fulfillment. A later
controller outage or altered artifact does not erase committed application history, and that
history cannot authorize a new fulfillment lacking current evidence.

The owned `orders.sqlite3` tables are `meta`, `orders`, `leases` and `operations`. Read-only
verification can inspect the exact order row and count `operations.kind = 'fulfill'` for its
application completion ID. SQLite owns compare-and-swap and receipt atomicity; private fixture
fault checks do not establish machine/power-loss durability or general physical resource arbitration.

Preregistration: `jevdual/docs/experiments/SIM5-versioned-application-fulfillment.md`.
Notebook: `jevdual/docs/notebook/2026-10-10-versioned-application-fulfillment.md`.
