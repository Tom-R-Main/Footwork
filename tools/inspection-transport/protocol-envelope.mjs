/** Capture-time WebSocket envelope inspection. Raw frames are never returned. */
const FRAME_METHODS = new Map([
  ['Network.webSocketFrameSent', 'sent'],
  ['Network.webSocketFrameReceived', 'received'],
]);
const CONTROL = new Set(['phx_join', 'phx_reply', 'phx_leave', 'phx_error', 'phx_close', 'heartbeat']);
const GRAPHQL_TYPES = new Set(['connection_init', 'connection_ack', 'ping', 'pong', 'subscribe', 'next', 'error', 'complete', 'start', 'stop', 'data', 'ka']);
const NAME = /^[A-Za-z][A-Za-z0-9_.-]{0,63}$/;
const FAMILY = /^[A-Za-z][A-Za-z0-9_-]{0,31}$/;

function admittedName(value, names) {
  return typeof value === 'string' && NAME.test(value) && names.has(value) ? value : null;
}

function phoenixEnvelope(value) {
  if (Array.isArray(value) && value.length === 5 && typeof value[2] === 'string' && typeof value[3] === 'string') {
    return { topic: value[2], event: value[3] };
  }
  if (value && !Array.isArray(value) && typeof value === 'object' &&
      typeof value.topic === 'string' && typeof value.event === 'string' && Object.hasOwn(value, 'payload')) {
    return { topic: value.topic, event: value.event };
  }
  return null;
}

/**
 * Accepts a raw CDP frame event in process memory. The returned record has a fixed schema,
 * no payload, no socket URL, no topic suffix, and no operation/connection identifier.
 * Unknown names are counted but never emitted. The caller must pass this only before
 * the existing recorder's redaction step; sealed metadata-only packets cannot be enriched.
 */
export function inspectProtocolEnvelope(event, { allowedEvents = [], allowedTopicFamilies = [], maxPayloadBytes = 1048576 } = {}) {
  const direction = FRAME_METHODS.get(event?.method);
  if (!direction) throw new Error('Expected a CDP WebSocket frame event');
  if (!Number.isSafeInteger(maxPayloadBytes) || maxPayloadBytes < 1024 || maxPayloadBytes > 4194304) throw new Error('Invalid frame cap');
  const frame = event.params?.response;
  const raw = typeof frame?.payloadData === 'string' ? frame.payloadData : '';
  const payloadBytes = frame?.opcode === 2 ? Buffer.byteLength(raw, 'base64') : Buffer.byteLength(raw);
  const timestamp = Number.isFinite(event.params?.timestamp) && event.params.timestamp >= 0 ? event.params.timestamp : null;
  const sequence = Number.isSafeInteger(event.sequence) && event.sequence >= 0 ? event.sequence : null;
  const base = { schemaVersion: 1, kind: 'websocket-envelope', direction, timestamp, sequence, payloadBytes };
  if (frame?.opcode !== 1) return { ...base, protocol: 'unknown', status: frame?.opcode === 2 ? 'binary' : 'unsupported-opcode' };
  if (payloadBytes > maxPayloadBytes) return { ...base, protocol: 'unknown', status: 'oversized' };
  let parsed;
  try {
    if (raw.startsWith('42')) {
      // Socket.IO EVENT packet. Namespace and packet IDs are intentionally unsupported.
      parsed = JSON.parse(raw.slice(2));
      if (Array.isArray(parsed) && typeof parsed[0] === 'string') {
        const eventName = admittedName(parsed[0], new Set(allowedEvents));
        return { ...base, protocol: 'socket.io', status: eventName ? 'recognized' : 'unlisted-event', ...(eventName ? { eventName } : {}) };
      }
      return { ...base, protocol: 'socket.io', status: 'malformed' };
    }
    parsed = JSON.parse(raw);
  } catch {
    return { ...base, protocol: 'unknown', status: 'malformed' };
  }
  const phoenix = phoenixEnvelope(parsed);
  if (phoenix) {
    const allowed = new Set([...CONTROL, ...allowedEvents]);
    const eventName = admittedName(phoenix.event, allowed);
    const prefix = phoenix.topic.split(':', 1)[0];
    const topicFamily = FAMILY.test(prefix) && new Set(allowedTopicFamilies).has(prefix) ? prefix : null;
    return { ...base, protocol: 'phoenix', status: eventName ? 'recognized' : 'unlisted-event',
      ...(eventName ? { eventName } : {}), ...(topicFamily ? { topicFamily } : {}) };
  }
  if (parsed && !Array.isArray(parsed) && typeof parsed === 'object' && typeof parsed.type === 'string' && GRAPHQL_TYPES.has(parsed.type)) {
    return { ...base, protocol: 'graphql-ws', status: 'recognized', eventName: parsed.type };
  }
  return { ...base, protocol: 'unknown', status: 'unrecognized' };
}

/** Aggregate only already-sanitized records; it never needs raw frames. */
export function summarizeProtocolEnvelopes(records) {
  const groups = new Map();
  for (const row of records) {
    if (row?.kind !== 'websocket-envelope' || !FRAME_METHODS.has(row.direction === 'sent' ? 'Network.webSocketFrameSent' : row.direction === 'received' ? 'Network.webSocketFrameReceived' : '')) throw new Error('Invalid envelope record');
    const key = JSON.stringify([row.protocol, row.direction, row.eventName || '[unlisted]']);
    if (!groups.has(key)) groups.set(key, { protocol: row.protocol, direction: row.direction, eventName: row.eventName || null, count: 0, bytes: 0, firstTimestamp: null, lastTimestamp: null });
    const group = groups.get(key);
    group.count++;
    group.bytes += row.payloadBytes;
    if (row.timestamp !== null) {
      group.firstTimestamp = group.firstTimestamp === null ? row.timestamp : Math.min(group.firstTimestamp, row.timestamp);
      group.lastTimestamp = group.lastTimestamp === null ? row.timestamp : Math.max(group.lastTimestamp, row.timestamp);
    }
  }
  return [...groups.values()].sort((a, b) => b.count - a.count || String(a.eventName).localeCompare(String(b.eventName)));
}
