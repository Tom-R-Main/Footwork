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
