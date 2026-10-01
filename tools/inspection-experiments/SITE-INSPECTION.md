# Evidence-led inspection of an unfamiliar web app

Use the same chain for Symbolic or another site: **interface action → browser state → network/realtime event → persisted readback**. Every claim should carry a source, time interval, account role, and one of `observed`, `code-supported`, `inferred`, or `unknown`. A delivered client bundle shows what the client can attempt; it does not show what the server permits or what this account can use.

## Capture before navigation

1. Freeze a run identity: site origin, browser target, account role, viewport, locale, date, build asset IDs, cache/service-worker state, and the baseline URL. Keep credentials and session material out of the record.
2. Start one scoped recorder with network, WebSocket, EventSource, console error and page lifecycle metadata. Keep a monotonic event cursor, explicit gaps/drops, and source target/session IDs. A second controller can alter the observed page or compete for CDP domain ownership, so coordinate one browser lane.
3. Capture a visible-state baseline: URL, screenshot, accessibility/DOM structure, enabled/disabled controls, loading and empty states, navigation labels, modal contents, and focus. Record text selectively, since documents and workspace content are private.
4. Pre-register the next action and expected result. Mark the beginning and end of the action interval; capture an immediate state and a settled state after visible readiness conditions. An HTTP acknowledgement alone is not a completed workflow.
5. Seal the raw private packet with a manifest/hash before deriving a report. Reports should link back to packet IDs and gaps, never silently convert missing events to absence claims.

## Extract five linked maps

| Map | Browser evidence | Useful questions | Limit |
| --- | --- | --- | --- |
| Route and state | URL, rendered controls, DOM/accessibility tree, screenshot before/after | What screens exist, what actions become available, what loading/error/empty states appear? | Hidden or role-gated screens remain unknown. |
| Client capability | Delivered JS/CSS, route strings, GraphQL documents, feature flags, translations, source maps when available | Which operations and schemas can the client ask for? What branches and validations exist? | Presence in code is not activation or server behavior. |
| Request graph | Method, URL shape, initiator, request/response shape, redirect, status, timing, cache/worker source | Which action correlates with which API call? What is paginated, cached, uploaded or retried? | Background calls and async updates confound causal attribution. |
| Realtime graph | WebSocket/SSE frame direction, event name allowlist, topic family, cadence, bytes, disconnect/reconnect | Where do progress, collaboration and generation updates arrive? | Encrypted/binary/custom protocols may stay opaque; frame contents are intentionally omitted. |
| Persistence and permission | Reload, reopen, alternate role, invalid input, cancel, retry, version/history | Did the result persist? Which controls are authorized? Does cancel roll back or just stop the UI? | One account cannot establish all permission boundaries. |

For each workflow, maintain a transition record: `precondition → action → immediate UI → request/realtime sequence → settled UI → reload/readback`. Include negative and recovery branches: validation failures, duplicate submit, cancel mid-flight, tab reload, lost socket, empty results, permission denial and stale data. A synthetic fixture with known facts or deliberate errors lets output quality be scored independently of transport success.

## Controlled inference

- Pair a no-action baseline with the action trial. Repeat after cache warmup and after a fresh page load. Compare sealed packets with `compare.mjs`; report background traffic and capture gaps from `coverage.mjs`.
- Change one input at a time: file type/size, prompt, skill, source trust, role, project context, or browser connectivity. Preserve the exact fixture and account state; note when another actor or tab can change shared state.
- Infer backend boundaries only when multiple signals converge. Example: a `Prepare → Submit` GraphQL pair plus a later named WebSocket completion event and a saved result suggests an asynchronous task. It does not reveal worker code, model provider, database schema, queue implementation, or billing semantics without additional evidence.
- Distinguish *requested*, *accepted*, *completed*, and *persisted*. Count latency from the right boundary: click-to-request, request-to-first-frame, first-to-last-frame, UI settle, and reload/readback.
- Give every finding a falsifier: a second role, a cold-cache run, an error injection, a different fixture, or a direct readback that could overturn the current explanation.

## Capture choices from local reference repos

- Chrome DevTools Protocol exposes complete WebSocket messages as `Network.webSocketFrameSent/Received` with opcode, payload, request ID and monotonic timestamp (`devtools-protocol/types/protocol.d.ts`). `protocol-envelope.mjs` parses them transiently and retains only structural fields.
- Playwright's HAR tracer records WebSocket frame events (`playwright/packages/playwright-core/src/server/har/harTracer.ts`); its trace can add screenshots/DOM snapshots for a **separately controlled** test browser. Importing a full HAR into a shareable report risks leaking headers, URLs and bodies.
- Chrome DevTools MCP offers request and page inspection tools (`chrome-devtools-mcp/src/tools/network.ts`, `screenshot.ts`, `performance.ts`) for interactive spot checks, not by itself a guaranteed continuous capture.
- HTTP Toolkit and mitmproxy can inspect HTTPS and WebSockets through a proxy. They are useful when browser CDP misses a transport, but proxy trust configuration can change behavior and capture sensitive traffic outside the target tab. Use a narrowly scoped, private run only when the added evidence justifies that intrusion.

## Current Symbolic boundary

The separate static read of publicly delivered Symbolic bundles reports Phoenix Channels on `/ws`, GraphQL guided-task operations, and `chat_stream_*` events. That is **code-supported**, not verified live frame traffic. Existing sealed browser packets have WebSocket timestamps and byte counts but discard raw frames, so they cannot reveal past event names. The original audit driver can opt into the envelope parser for a future bounded run. Until then, the fetch-stream probe remains a general HTTP-stream tool and should not be used as evidence that Symbolic emitted no generation stream.
