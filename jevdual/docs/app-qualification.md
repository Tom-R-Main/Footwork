# Diversified app qualification

The October 28 harness covers Finder file organization, Preview image transformation, Chrome ticket submission and interrupted handoffs. The [October 28 installed run](../results/move-submit-20261028/report.md) passed the owned nominal chain and an interrupted chain with truncated HTTP response loss. **The full portfolio gate remains open for disconnects before HTTP response headers**, which produced duplicate ingress and correctly remained unknown. Earlier runs remain linked below as historical evidence.

## Fixture and independent checks

`jevdual.app_oracles.create_fixture(root)` creates a fresh owned scratch tree with an asymmetric PNG, preserved original, same-basename decoy and sibling sentinels. Keep authority, handoff and server databases outside that fixture subdirectory. `check_finder` verifies exact output path, old absence, unchanged bytes and siblings; `check_preview` independently decodes saved pixels/dimensions against the specified clockwise transform. Neither check performs the UI effect or establishes its author.

Start the owned local form with:

```sh
python -m jevdual.app_qualification --root /absolute/run/ticket-fixture --lose-reply-once
```

It prints an owned PID, loopback URL and database. POST ingress and deduplicated rows are recorded separately in SQLite, so one row cannot hide duplicate requests. `TicketStore.check(expected)` checks exact request ID, filename, orientation and digest. With the default response policy, lost responses and fixture restart retain both ledgers. The opt-in sealed policy below prohibits reopening its source.

`HandoffRun(root, authority, epoch)` dispatches no app actions. Call `begin(stage, session_id=...)` before each stage, then `complete(stage, operation_ids, verify, artifact)` after UI execution. It requires settled retained receipts from the bound session/app and an independent check bound to the same artifact identity. Preview preserves its input path and verifies clockwise rotation; Chrome preserves the entire input identity and rechecks the bound ticket database read-only. Stale/tampered input, unknown custody and unbound success dictionaries refuse advancement. Stage checkpoints survive process death; an interrupted active input cannot authorize blind redispatch.

These gates combine custody and current postcondition evidence. They still require a live trajectory showing the intended UI operations; a generic app click plus matching externally modified bytes is not installed UI qualification.

## Chrome route and scope

The semantic browser route lacks durable tab/document incarnation and remains refused for durable admission. The separate native Chrome candidate supports:

```sh
footwork desktop start "Owned local fixture" --app "Google Chrome" --pid OWNED_PID \
  --window FIXTURE_TITLE --native-url EXACT_HTTP_LOOPBACK_URL --native-title FIXTURE_TITLE \
  --authority /absolute/run/authority.sqlite --session /absolute/run/chrome
```

An explicit PID selects only that process, with first-observation app/PID/window checks. URL/title scope is persisted and bound into request identity and receipts. Every fresh/internal observation and input boundary obtains a separate bounded complete trusted-toolbar capture (`chrome.ax-toolbar/v1`), excluding web-content descendants. Exact PID/window, one real toolbar address bar, readable URL and fixture title are required. An incomplete page capture does not invalidate a complete toolbar capture; an incomplete toolbar refuses. Scope coverage is retained with execution evidence. Foreground-key fallback rechecks after its policy wait. Guarded observations withhold screenshots. A native Chrome result does not qualify the semantic browser adapter, arbitrary origins or tab/window birth.

## Owned Finder targets and native predicates

For the synthetic asset fixture, start durable Finder with `--finder-manifest /absolute/fixture/fixture.json`. Startup finds the unique window containing the exact seeded file, even among identically titled windows. Use `do type file:/absolute/fixture/inbox/asset.png renamed.png` for a rename. Grants accept the same selector. Fresh Foundation-resolved AXURL, retained device/inode, manifest scope, complete bounded AX traversal and current geometry establish the target; stale numeric IDs and basename matching do not. Wrong directories, symlinks, replaced inodes, duplicate windows and unreadable subtrees refuse.

The rename producer selects the sole exact row, opens File to validate Rename, enters the real editor, writes its value and sends one foreground Return. It retains acknowledged input counts as a lower bound and qualifies only an observed same-inode path transition. Name-cell display changes alone remain insufficient. The move route requires the owned destination folder to be open in a second Finder window before startup. Startup registers its unique exact protected marker, PID/window and directory identity. Use `do move file:/absolute/fixture/inbox/renamed.png /absolute/fixture/organized` with an exact grant. The producer validates both bindings before input, copies the sole source row, verifies the new clipboard generation and exact file URL, focuses the registered destination and invokes Edit > Move Item Here. It rechecks source bytes, clipboard and destination immediately before the move and qualifies only the same-inode path transition. Missing, duplicate, replaced or unfocused destination windows refuse. This is the pre-bound two-window workflow; Go to Folder remains unqualified.

Preview's first Rotate Left/Right can qualify a new exact Undo Rotate marker on the same bound document. Save qualifies only an observed edited-state or file-digest transition following its acknowledged menu press. A plain menu acknowledgement stays unknown. Preview can autosave independently; saved pixels and persistence require the separate oracle. These narrow native predicates are checked against the admitted operation, arguments, PID/window and producer schema before reconciliation.

## Installed qualification gate

All Finder/Preview/Chrome nominal cases, their assigned challenges and the interrupted connected chain must pass before the portfolio is qualified. Offline artifact transformations and HTTP calls only qualify harness components. Do not substitute direct filesystem/image/API edits for missing UI operations, clear unresolved history, change authority domains to retry uncertain work, or count a refusal as completed work.

The first installed run bound owned Finder/Preview resources, but Finder returned unknown delivery, Preview was blocked downstream, and Chrome refused incomplete scope evidence. Fixtures remained unchanged, the ticket ledger had zero requests, and owned windows/processes/listener were cleaned up. Stable file targeting, qualified native delivery and complete Chrome scope capture remain the concrete live gaps.

The [repair rerun](../results/app-repair-20261028/report.md), on frozen commit `4c2c4cf`, completed installed exact rename and Preview rotation/autosave, plus controller-kill recovery between them. Trusted Chrome scope admission and mismatch refusal passed. The installed Chrome form remained unavailable in the background while foreground setup yielded to user activity. The required Finder move and Chrome submission/reconciliation remain open; the rename-only partial chain does not qualify the full portfolio. All old unknown operations remain retained.

## Pre-admitted Chrome submission evidence

For the fresh owned ticket fixture, additionally pass `--ticket-manifest /absolute/run/ticket-manifest.json` at native Chrome startup. Its required keys are `database`, `url`, `expected`, `artifact`, and `root`; the optional `completion_policy` defaults to `response` (v2). `expected` contains the fresh UUID4-hex request ID, artifact basename, `clockwise90` orientation and SHA-256 of the saved artifact. Bind the empty ledger, its persistent fixture ID, response mode and exact numeric-loopback origin before form input. The registered artifact must retain its path, bytes and identity through submission.

Only the exact `click button:Register asset` with all four expected observed form values can carry that preparation into admission. `status --reconcile` may resolve an unknown started attempt from one new matching ingress, one durable row and the v2 producer's supported response-boundary event, with the exact request body, origin, source and artifact bindings. The handler records that event only after flushing headers for a normal or truncated response. Pre-header-disconnect mode never qualifies under v2, including before a retry reaches the ledger. Duplicate ingress, missing records, changed sources, reused nonce or mismatched fields leave it unknown. Historical operations cannot enroll after execution. The independently retained `ticket_submission` receipt survives controller death before finalization; it does not invent a native delivery count or replace the original uncertainty capsule. Token replay and reconciliation send no input.

The response-loss fixture has distinct modes: default `--lose-reply-once` disconnects before response headers; `--lose-reply-once --reply-loss truncated` sends headers and loses the body. Qualification reports each mode separately. A deduplicated server row alone never proves one submission.

## October 28 final installed boundary

Frozen runtime `2ae0a5f` completed Finder rename/move, persisted Preview clockwise rotation and Chrome submission/reconciliation on fresh owned fixtures. A connected trial recovered after actual controller kills at both app boundaries and after submission ingress, together with truncated HTTP body loss; it retained exactly one ingress. Original-token replay added no request. The full suite passed 2142 tests, with 26 skipped.

Rename now reacquires only its owned window after the actual rename and requires the normal filename AXURL to return. Finder may replace the transient editor, so that setup step binds the current expected-name editor to the exact main window; file input still requires strict URL/inode identity. Preview obtains the existing Undo/save predicate before foreground restoration and checks exact ownership around input/readback. These live trials use a reserved desktop and a fresh owned Preview process with state restoration suppressed.

The pre-header-disconnect trial again produced two ingress events and one row. It has no qualified service receipt, remains unknown, and cannot advance Chrome. The [final report](../results/move-submit-20261028/report.md) records the successful boundaries, complete trial accounting, retained failures and cleanup.

## October 29 review corrections

Qualification now requires v2 service-response provenance and an exact correlation between the admitted submission receipt and the Chrome oracle's ledger, origin, nonce, fields and artifact. Generic Chrome click receipts and unrelated matching databases cannot advance the handoff. Historical v1 records remain readable; new qualification cannot enroll old unknowns. The review also adds deterministic unresolved-custody checks to `done`, repairs interrupted projection logs without discarding their bytes, and requires qualified no-send before a second key input. These changes do not fix or qualify duplicate ingress after pre-header disconnects.


## October 30 transport diagnosis and terminal fixture policy

The [diagnostic controls](../results/preheader-20261030/controls/summary.json) separate native input from browser transport. In the observed Chrome form-navigation disconnect controls, one submit event and one logical CDP POST led to two handler invocations on separate connections with identical request bodies. Chromium NetLog records `HTTP_TRANSACTION_RESTART_AFTER_ERROR` with error `-324` between two `POST /tickets HTTP/1.1` sends on the same transaction. Direct HTTP controls produced one ingress. Both explicit Chrome fetch controls produced one ingress without that restart. These are finite diagnostic observations, not native UI qualification or a universal transport guarantee.

The fixture retains `--submission-route navigation` as its default and duplicate-ingress challenge. Opt-in `--submission-route fetch` intercepts the form submission, encodes the same fields, makes one guarded fetch call, and disables further submission in that document. It displays returned text through `textContent`; an unavailable response instructs the operator to reconcile. This changes the observed submission route while preserving the original pre-header disconnect fault.

A separate opt-in v3 `sealed_fixture` policy can qualify the final history of an owned producer epoch. Start a fresh fixture with:

```sh
python -m jevdual.app_qualification --root /absolute/run/ticket-fixture \
  --submission-route fetch --completion-policy sealed_fixture \
  --lose-reply-once --reply-loss disconnect
```

Record the printed PID, URL and database. Before native input, enroll the empty source using the usual ticket manifest plus the exact field `"completion_policy": "sealed_fixture"`. For example:

```json
{
  "database": "/absolute/run/ticket-fixture/tickets.sqlite",
  "url": "http://127.0.0.1:ACTUAL_PORT",
  "expected": {
    "request_id": "FRESH_UUID4_HEX",
    "artifact": "renamed.png",
    "orientation": "clockwise90",
    "digest": "ACTUAL_SAVED_ARTIFACT_SHA256"
  },
  "artifact": "/absolute/run/fixture/organized/renamed.png",
  "root": "/absolute/run",
  "completion_policy": "sealed_fixture"
}
```

Replace placeholders with the exact printed origin, fresh nonce and independently checked artifact digest. Pass this file through `footwork desktop start ... --ticket-manifest /absolute/run/ticket-manifest.json` together with the native Chrome PID, window, URL/title scope and shared authority shown above. The fixture and manifest must select the same completion policy before admission; existing unknowns cannot enroll afterward.

An open v3 source remains unknown even when it contains one matching ingress. For the owned qualification workflow, retire the exact owned browser after its submission attempt, then send cooperative SIGTERM to the recorded fixture PID and wait for its exit. The CLI exits through its context manager: it stops accepts, closes the listener, joins all accepted non-daemon handlers, and atomically seals the final ledger snapshot. SQL guards/triggers reject later writes; a v3 source cannot reopen, whether still open or sealed. SIGKILL, a missing seal, an active handler, a quiet interval or process absence alone supplies no closure proof.

Only then may read-only reconciliation validate the pre-admitted epoch, origin, identity, exact body/artifact, unique ingress/row and seal digest. Duplicate, changed or incomplete evidence preserves unknown custody. The retained v3 service receipt supplies no native input count. Chrome handoff validates it and independently recaptures the same sealed source.

The terminal boundary is the cooperative fixture source epoch. It does not certify browser/network termination, prevent every later wire attempt, authenticate hostile SQLite files or establish universal exactly-once behavior. Default v2 response-boundary qualification and historical v1 reads remain separate; old unknowns are not upgraded. Installed v3 qualification is pending; the [phase report](../results/preheader-20261030/report.md) records the eventual build, trial accounting and verdict.
