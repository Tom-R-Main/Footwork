/**
 * In-memory, session-scoped CDP push-to-pull adapter for a future persistent transport.
 * No browser connection is made here. Raw event params live only in this bounded ring;
 * the capture journal must still apply its positive-allowlist serializer before disk.
 */
export function createEventRing({ sessionId, methods, maxEvents = 10000, maxEventBytes = 1048576 } = {}) {
  if (typeof sessionId !== 'string' || !sessionId || !Array.isArray(methods) || !methods.length || methods.some(method => !/^(?:Network|Runtime)\.[A-Za-z]+$/.test(method))) {
    throw new Error('An explicit CDP session and Network/Runtime method allowlist are required');
  }
  if (!Number.isSafeInteger(maxEvents) || maxEvents < 1 || maxEvents > 100000) throw new Error('maxEvents must be 1..100000');
  if (!Number.isSafeInteger(maxEventBytes) || maxEventBytes < 1024 || maxEventBytes > 4194304) throw new Error('maxEventBytes must be 1024..4194304');
  const allowed = new Set(methods);
  const ring = [];
  let sequence = 0, lostThrough = 0, droppedEvicted = 0, droppedOversize = 0, ignoredForeign = 0, ignoredMethod = 0, disconnected = false;

  function ingest({ method, params = {}, source = {} } = {}) {
    if (disconnected) throw new Error('Transport disconnected');
    if (source.sessionId !== sessionId) { ignoredForeign++; return { accepted: false, reason: 'foreign-session' }; }
    if (!allowed.has(method)) { ignoredMethod++; return { accepted: false, reason: 'method-not-selected' }; }
    const candidate = { method, params, source: { ...source, sessionId }, sequence: sequence + 1 };
    let serialized;
    try { serialized = JSON.stringify(candidate); } catch { throw new Error('CDP event cannot be serialized'); }
    if (typeof serialized !== 'string') throw new Error('CDP event cannot be serialized');
    sequence++;
    if (Buffer.byteLength(serialized) > maxEventBytes) {
      lostThrough = sequence;
      droppedOversize++;
      return { accepted: false, reason: 'event-byte-cap', sequence };
    }
    // Store a parsed copy so later mutation of the incoming transport object cannot alter evidence.
    ring.push(JSON.parse(serialized));
    while (ring.length > maxEvents) {
      const removed = ring.shift();
      lostThrough = Math.max(lostThrough, removed.sequence);
      droppedEvicted++;
    }
    return { accepted: true, sequence };
  }

  async function readEvents({ afterSequence, limit = 1000, methods: selected, target } = {}) {
    if (target && target.sessionId !== sessionId) throw new Error('Target session does not match this transport');
    if (!Number.isSafeInteger(limit) || limit < 1 || limit > 1000) throw new Error('limit must be 1..1000');
    if (selected !== undefined && (!Array.isArray(selected) || selected.some(method => !allowed.has(method)))) throw new Error('Requested method was not subscribed');
    if (afterSequence === undefined) {
      if (disconnected) throw new Error('Transport disconnected');
      return { cursor: sequence, events: [], hasMore: false, truncated: false };
    }
    if (!Number.isSafeInteger(afterSequence) || afterSequence < 0 || afterSequence > sequence) throw new Error('Invalid event cursor');
    if (disconnected && afterSequence >= sequence) throw new Error('Transport disconnected');
    const wanted = selected ? new Set(selected) : allowed;
    const events = [];
    let cursor = afterSequence;
    for (const event of ring) {
      if (event.sequence <= afterSequence) continue;
      cursor = event.sequence;
      if (wanted.has(event.method)) events.push(event);
      if (events.length >= limit) break;
    }
    if (events.length < limit) cursor = sequence; // Consume filtered and dropped positions too.
    return { cursor, events, hasMore: cursor < sequence, truncated: afterSequence < lostThrough };
  }

  function disconnect() { disconnected = true; }
  function status() {
    return { sessionSelected: true, sequence, bufferedEvents: ring.length, lostThrough,
      droppedEvicted, droppedOversize, ignoredForeign, ignoredMethod, disconnected };
  }
  return { ingest, readEvents, disconnect, status };
}
