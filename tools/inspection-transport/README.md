# Candidate push transport for browser inspection

`event-ring.mjs` is an offline-tested building block for a future long-lived CDP transport. It accepts pushed events **only from one explicitly selected CDP session** and provides the current recorder's paginated `readEvents` shape. It assigns monotonic local cursors, bounds event count and per-event bytes, reports eviction/oversize loss as `truncated`, and makes disconnect terminal after buffered events are drained. This module does not attach to Chrome, launch a browser, enable a CDP domain, navigate or write evidence.

```js
const ring = createEventRing({
  sessionId: selectedSessionId,
  methods: ['Network.requestWillBeSent', 'Network.responseReceived'],
});
// A separately reviewed CDP adapter calls ring.ingest({method, params, source})
// only for messages from its selected target/session.
const batch = await ring.readEvents({ afterSequence: previousCursor, limit: 1000 });
```

The buffer stores raw event params only in bounded process memory. A future adapter must pass them through `browser-inspection/redaction.mjs` before disk, preserve source/target identity, and record disconnect, session replacement and truncation as gaps in the sealed run. It must also prove target selection, worker attachment, domain ownership, a live origin fence, and uninterrupted process lifetime. No cross-tool-call or worker coverage is claimed here. Do not run a second controller on the shared Symbolic tab while the original audit owns it.

Offline test: `node --test tools/inspection-transport/event-ring.test.mjs`.

## Stream cadence sidecar

`stream-probe.mjs` adapts the useful part of the separate in-page recon kit for Footwork: **first-chunk time, per-chunk byte counts and cadence**, with no chunk previews or response values. `buildStreamProbeSource({allowedOrigin})` returns a self-contained script for the existing permitted tab's page-evaluation API. It installs `window.__footworkStreamProbe`; the operator can call `stop()`, then `drain(1000)` and `stats()` within one actively awaited browser invocation. Full page reloads need a fresh installation. The probe touches same-origin `fetch` responses with SSE, NDJSON or text-stream content types; it does not see streams started before installation, worker fetches, XHR, or WebSocket frames.

The Node-side `writeStreamArtifact({runDirectory,label,records,probeStatus})` strips unknown fields, writes a private `artifacts/<label>.stream.jsonl` file with `0600` permissions and syncs it. Call it **before** `capture.stop()` so the recorder hashes the artifact in its manifest. Include `probeStatus` so dropped in-page records and any still-active observation are visible. It refuses to modify a sealed run. The probe returns the page's original Response and clones only the selected stream, but cloning can still perturb buffering or timing; calibrate against a synthetic page and use it only for a bounded workflow. A cap or stop cancels the observer branch. A live Symbolic run has not used this sidecar yet.

Offline test: `node --test tools/inspection-transport/stream-probe.test.mjs`.

## Realtime protocol envelopes

`protocol-envelope.mjs` is a capture-time, pure parser for CDP `Network.webSocketFrameSent` and `Network.webSocketFrameReceived` events. It recognizes Phoenix JSON array/object envelopes, basic Socket.IO EVENT packets and standard GraphQL WebSocket message types. It returns only direction, CDP monotonic timestamp/sequence, frame byte count, protocol, recognition status, an **explicitly allowed** application event name, and an explicitly allowed Phoenix topic family. Dynamic topic suffixes, payloads, message IDs, socket URLs and unlisted names never enter its result. Binary, malformed and oversized frames remain unnamed.

```js
const metadata = inspectProtocolEnvelope(rawCdpEvent, {
  allowedEvents: ['chat_stream_started', 'chat_stream_delta', 'chat_stream_finished'],
  allowedTopicFamilies: ['chat'],
});
// Pass `metadata`, not `rawCdpEvent.params.response.payloadData`, to a private journal.
```

This module does **not** attach to a browser or modify the original recorder. It must run while raw CDP frames are transiently available in memory, before the original redaction step; previously sealed metadata-only packets cannot be enriched. The original browser driver owns any integration and must calibrate event loss, parser recognition, target identity and artifact sealing. Static Symbolic frontend code suggests Phoenix Channels on `/ws`, but the live audit has not yet verified specific channel event names in frames. The fetch stream sidecar above is generic and is unlikely to observe Symbolic's generation cadence if that code path uses WebSockets.

Offline test: `node --test tools/inspection-transport/protocol-envelope.test.mjs`.

## GraphQL operation envelopes

`graphql-envelope.mjs` takes a transient CDP `Network.requestWillBeSent` event and an exact HTTPS origin/path fence. For a JSON GraphQL POST it keeps only explicitly allowed operation names, query/mutation/subscription kind, operation/batch counts and byte counts. It discards URL query parameters, query text, variables, extensions and unknown operation names. Missing post data, malformed JSON, oversized bodies and a truncated batch are explicit. The operation allowlist should come from a reviewed delivered-client catalog or fixture.

```js
const metadata = inspectGraphqlEnvelope(rawCdpEvent, {
  allowedOrigin: 'https://studio.example.test',
  allowedOperations: ['GuidedFactCheckPrepare', 'GuidedFactCheckSubmit'],
});
```

Like the WebSocket parser, this is **not** connected to the current recorder and cannot enrich previously sealed packets. It identifies a request the client made, not successful server execution or persistence. A future integration should associate its fixed-schema output with the original request sequence, preserve capture gaps, and test against a private fixture before use on an account workflow.

Offline test: `node --test tools/inspection-transport/graphql-envelope.test.mjs`.
