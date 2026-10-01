# Portable browser capture harness

The module does not navigate, attach to a profile, import a browser package, or start recording when imported. Inject the already selected Browser plugin `tab` and CDP objects from the permitted Node REPL environment. No dependencies or live provider calls are needed.

```js
const { createCapture } = await import('/Users/thomasmain/projects/footwork/tools/browser-inspection/capture.mjs');
var capture = createCapture({
  tab: existingTab,
  cdp: existingCdp,
  projectRoot: '/Users/thomasmain/projects/footwork',
  allowedOrigin: 'https://example.test',
  outputName: 'browser-inspection',
  // Pass a confirmed session/target if the CDP bridge exposes one.
  // target: { sessionId: 'observed-session-id' },
  domainsToEnable: ['Network'],
  // Set true only if these domains are not owned by another recorder on this target.
  ownDomainLifecycle: true,
});
await capture.start(); // Must already be on the declared HTTPS origin.
await capture.startPolling({ intervalMs: 1000 }); // Actual timer; persistent runtime required.
await capture.mark({ workflowId: 'fixture-project', stepId: 'before-projects', note: 'Before reviewed UI action' });
await capture.snapshotNow({ label: 'initial', workflowId: 'fixture-project', stepId: 'before-projects' });
await capture.step({
  workflowId: 'fixture-project',
  stepId: 'open-projects',
  intent: 'Open Projects and observe the list',
  action: async () => {
    // One reviewed, permitted UI action through the existing tab API.
  },
});
await capture.mark({ workflowId: 'fixture-project', stepId: 'after-projects', note: 'Operator observed the resulting state' });
await capture.snapshotNow({ label: 'result' });
await capture.stopPolling(); // Cancels timer and waits pending evidence operations.
await capture.stop(); // Waits pending UI/evidence work, closes writers, seals hashes.
```

`ownDomainLifecycle` is explicit because CDP does not expose the existing enable state to this harness. If another recorder already owns the domains, use `domainsToEnable: []`; stop then leaves all domains alone. Successful enable calls are the only domains this harness disables. Failed enables are marked unsupported. Runtime console/exception coverage requires explicit `domainsToEnable: ['Network', 'Runtime']` ownership. Request extra-info, cookies, browser storage and auth internals are never queried. Event header/cookie fields are omitted before disk; response-extra-info retains only identity/status.

Journals are append-only per run, under `output/browser-inspection/<runId>/`. Run IDs cannot escape the output directory and existing runs cannot be overwritten. Files have mode `0600` and new directories `0700`. Ancestor symlinks that escape the project are rejected. The private output directory must remain Git-ignored. No output produced by a live account belongs in a commit.

`events.jsonl` records `{schemaVersion,type:'event',recordedAt,runId,event:{method,sequence,source,params}}`; params contain only metadata selected by the serializer. Reused request IDs remain separate journal events. `actions.jsonl` records capture lifecycle and `step_begin`/`step_end`, including workflowId, stepId, intent, before/after snapshot references and correlation cursors. `gaps.jsonl` records truncation, bounded drain limits, unsupported capabilities and evicted/unavailable bodies. `bodies.jsonl` records requestId, source, sanitized URL, MIME, captureMode, status and bounded structure. Journal writes use serialized FileHandle.write + sync before acknowledging marks/drains. Artifact writes also sync before acknowledgement. The stop barrier closes writers before hashing every journal and artifact with SHA-256 and includes byte sizes. It detects subsequent changes; it does not sign or authenticate the recorder's observations.

Default capture stores no body values, console arguments, full headers, request bodies or private DOM/screenshots. URLs omit all query values, URL credentials and fragments. JSON shapes omit scalar values and redact sensitive or dynamic field names. Default body retrieval is limited to JSON MIME responses at the exact declared origin, after a fresh current-origin check. Other textual responses such as JavaScript, CSS and HTML record omitted-content-policy with observed loadingFinished encodedBytes, without making a getResponseBody call. This encoded measurement is not a decoded-content byte count. Eligible synthetic fixture text and explicitly enabled delivered JavaScript source remain separate opt-ins. JSON served under an unrelated MIME is omitted by the default policy. Binary, oversized, cross-origin and SSE response bodies are omitted. Encoded-size checks happen before retrieval and decoded-size checks happen immediately afterward. Browser transport can still return a body larger than the requested cap; the bridge has no ranged body API.

`fixtureBodyValues: true` is reserved for an explicitly dedicated synthetic-fixture run: it preserves bounded synthetic values after credential redaction. It is not appropriate for an account-wide recording. SSE values require an observed same-origin response. WebSocket text values require an observed webSocketCreated event whose wss host maps to the declared HTTPS origin. Unassociated, cross-origin and binary WebSocket values are omitted. Protocol metadata is captured in both cases. Arbitrary obfuscated credentials cannot be recognized perfectly; keep credential-bearing screens and payloads outside fixture runs.

`privateDom: true` and `privateScreenshots: true` are separate explicit private-artifact opt-ins. Screenshot capture requires DOM capture and suppresses images when credential-related labels appear in the DOM. Operator preinspection remains necessary: this heuristic cannot prove an image contains no secrets. DOM strings receive best-effort text redaction before disk. With these options off, the wrapper records URL and artifact-disabled status before and after each action. Screenshots use the current viewport to bound collection. All these artifacts remain private and uncommitted.

The action wrapper reads the event cursor before the action, records intention first, executes once, then drains and records after-state even if the action throws. Thrown error messages and action return values are not persisted. The return value remains available to the operator in memory. Visible effect text and acknowledgement are operator-supplied observations; the wrapper records `visibleEffectVerified:false` so a completion record cannot be confused with proof of product success. Distinguish a successful HTTP response from rendered state, durable state after reload, and outcome correctness.

`startPolling({intervalMs})` starts a real timer (1000ms default, 100..10000ms allowed), with one serialized drain at a time. `stopPolling()` cancels it immediately and waits for evidence operations already queued. The same evidence queue serializes drains, marks, snapshots and writes. UI action/generation waits occur outside that queue so polling continues through them. `stop()` cancels polling, waits an active UI step and pending evidence work, attempts owned-domain cleanup, closes journal handles in a finally block, then seals the manifest. Duplicate step IDs and artifact labels are refused before a second action or overwrite.

Polling requires a persistent Node/browser runtime. A tool-session disconnect, runtime reset or runtime suspension can interrupt it; there is no unattended-across-turn or reconnect-survival guarantee. Each CDP operation requests `eventTimeoutMs` (500ms default, 50..1000ms allowed); an adapter that ignores that timeout can still delay shutdown. A failed poll pauses once rather than creating a tight retry loop. An unavailable current-origin check records a distinct origin-check-unavailable gap and pause cause, rather than claiming the tab moved. Browser plugin transport may require an actively awaited Node tool invocation; a timer that outlives that invocation can lose browser-call context even though the JavaScript timer itself still runs. Keep an awaited recording interval active when that bridge requires it, and calibrate this behavior before claiming background coverage. A fresh origin check runs before and after event reads, before body retrieval, and before writing late body/snapshot results. Leaving the declared origin records one gap and permanently pauses collection for that run; returning requires a new scoped run. The stop lifecycle still records cleanup and seals the private evidence packet.

Network enable requests 4MiB total retention by default (`networkBufferBytes`, max 4MiB), a per-resource buffer no larger than 1MiB (`resourceBufferBytes`), and `maxPostDataSize` no larger than the body cap. A rejected command is recorded as unsupported; the harness does not open a standalone CDP socket or another browser profile to bypass that rejection. CDP retention can still evict events/bodies. `hasMore` pages flush immediately and truncation/gaps remain evidence. `configureDurableMessages` and `streamResourceContent` are not enabled; fetch streaming chunk content is not implemented, while dataReceived retains byte metadata. No model, server implementation or true request causality can be deduced from timing alone. Offline mocks establish the harness contract; live bridge capabilities require separate calibration.

Offline tests: `node --test tools/browser-inspection/capture.test.mjs`. Tests leave synthetic-only evidence in project-local `output/browser-inspection/test-*` for inspection and perform no browser/provider calls.

`allowedOrigin` is required and must be an exact HTTPS origin, with no path, query, fragment or credentials. `outputName` defaults to `browser-inspection` and accepts only a safe single directory name. JSON request postData is recorded as structure by default; non-JSON request data records byte count. Initiator metadata includes only sanitized direct URL and numeric location, with no stack frames. Extra-response-info capture records request identity and status code only, never headers or cookies. Fetch streaming chunk contents are not implemented; `Network.dataReceived` preserves byte and timing metadata only.

`mark({stepId,workflowId,note})` appends a sanitized `type:mark` action with a drained cursor. `snapshotNow({label,stepId?,workflowId?})` records a `type:snapshot` action with before/after cursors and private artifact references when enabled. These markers can bracket UI operations driven outside the step wrapper. `deliveredSourceText:true` separately opts into sanitized same-origin JavaScript response text only when the MIME is JavaScript and the URL ends in .js or .mjs, within the existing body cap. It uses `captureMode:delivered-source`, records redactionApplied/sourceAltered/truncated, and leaves HTML and cross-origin content omitted. This observes newly delivered source; it cannot recover initial requests made before recording.

## Observed calibration status

October 1, 2026: the supported Chrome tab/CDP bridge accepted owned Network/Runtime domains and saved private DOM/screenshots/frontend inventories. Polling worked during actively awaited tool invocations; timer calls outside an invocation paused on unavailable browser context. A cached two-route packet recorded 334 events/50 hops with zero reported gaps and eighteen hash-verified files including exact recorder source. A heavier first transition lost events; a bulk source-capture transition recorded unavailable bodies. Thus bounded live observation is established, while unattended/cold-load/worker completeness remains unproven. Site-specific details and private packets stay in Best-Edit's Symbolic research area.

Root verification includes the sibling offline comparator, coverage audit and event-ring packages: 44 tests passed together. The coverage audit verifies packet integrity and reports explicit/lifecycle gaps independently; its no-reported-capture-gaps verdict is not proof of complete recording. The session-scoped event ring is a synthetic transport building block, not a live Chrome attachment.
