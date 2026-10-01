// Keep raw browser data in memory only. Journal serializers use positive allowlists.
export const SECRET_KEY = /authorization|cookie|password|passwd|secret|token|credential|api.?key|signature|session|jwt|signed|policy|x-amz|x-goog/i;

export function safeText(value, max = 2000) {
  if (typeof value !== 'string') return undefined;
  return value
    .replace(/-----BEGIN [^-]*-----[\s\S]*?-----END [^-]*-----/g, '[REDACTED_PEM]')
    .replace(/https?:\/\/[^\s<>"']+/gi, url => safeUrl(url))
    .replace(/\b(?:Bearer|Basic)\s+[\w.+/=-]+/gi, '[REDACTED]')
    .replace(/\beyJ[\w-]+\.[\w-]+\.[\w-]+\b/g, '[REDACTED]')
    .replace(/\b(?:sk|pk|ghp|github_pat)[_-][\w-]{10,}\b/g, '[REDACTED]')
    .replace(/((?:["']?)(?:password|passwd|secret|token|access[_-]?token|refresh[_-]?token|api[_-]?key|authorization|cookie|signature|credential)(?:["']?)\s*[:=]\s*)(?:"[^"\n]*"|'[^'\n]*'|[^\s,;\n]+)/gi, '$1[REDACTED]')
    .replace(/[\w.+-]+@[\w.-]+\.[a-z]{2,}/gi, '[EMAIL]')
    .replace(/\b[\w-]{48,}\b/g, '[OPAQUE]')
    .slice(0, max);
}

export function safeUrl(value) {
  try {
    const url = new URL(value);
    // No credentials, hash or query values, even when their parameter names look harmless.
    const pathname = url.pathname.split('/').map(segment => {
      let decoded;
      try { decoded = decodeURIComponent(segment); } catch { return '[INVALID]'; }
      return /@|eyJ|[\w-]{48,}/.test(decoded) ? '[OPAQUE]' : segment;
    }).join('/');
    const keys = [...new Set([...url.searchParams.keys()].map(key => SECRET_KEY.test(key) ? '[SECRET]' : key.replace(/[^\w.-]/g, '_').slice(0, 60)))];
    return `${url.protocol}//${url.host}${pathname}${keys.length ? `?${keys.map(k => `${k}=[OMITTED]`).join('&')}` : ''}`;
  } catch { return '[INVALID_URL]'; }
}

export function sourceIdentity(source = {}) {
  return Object.fromEntries(['sessionId', 'targetId', 'tabId', 'extensionId'].filter(k => typeof source[k] === 'string' || (k === 'tabId' && Number.isInteger(source[k]))).map(k => [k, typeof source[k] === 'number' ? source[k] : safeText(source[k], 100)]));
}

export function jsonShape(value, depth = 0) {
  if (depth > 8) return 'depth-limit';
  if (value === null) return 'null';
  if (Array.isArray(value)) return { type: 'array', length: value.length, sample: value.slice(0, 5).map(v => jsonShape(v, depth + 1)) };
  if (typeof value === 'object') {
    // Dynamic map keys can themselves contain private data. Suppress non-schema-looking keys.
    return { type: 'object', fields: Object.fromEntries(Object.keys(value).slice(0, 100).map((key, i) => [SECRET_KEY.test(key) ? `[sensitive-field-${i}]` : /^[a-zA-Z_][a-zA-Z0-9_]{0,60}$/.test(key) ? key : `[dynamic-key-${i}]`, SECRET_KEY.test(key) ? 'omitted' : jsonShape(value[key], depth + 1)])), truncated: Object.keys(value).length > 100 };
  }
  return typeof value;
}

export function fixtureValues(value, depth = 0) {
  if (depth > 8) return '[DEPTH_LIMIT]';
  if (typeof value === 'string') return safeText(value);
  if (Array.isArray(value)) return value.slice(0, 100).map(v => fixtureValues(v, depth + 1));
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).slice(0, 100).map(([key, v], i) => [SECRET_KEY.test(key) ? `[sensitive-field-${i}]` : /^[a-zA-Z_][a-zA-Z0-9_]{0,60}$/.test(key) ? key : `[dynamic-key-${i}]`, SECRET_KEY.test(key) ? '[REDACTED]' : fixtureValues(v, depth + 1)]));
  return value;
}

const NUMERIC = ['timestamp', 'wallTime', 'status', 'encodedDataLength', 'dataLength', 'loaderId'];
export function eventMetadata(event) {
  const p = event.params || {};
  const result = {};
  for (const key of ['requestId', 'frameId', 'loaderId', 'type']) if (typeof p[key] === 'string') result[key] = safeText(p[key], 120);
  for (const key of NUMERIC) if (typeof p[key] === 'number' && Number.isFinite(p[key])) result[key] = p[key];
  if (typeof p.canceled === 'boolean') result.canceled = p.canceled;
  if (p.request) result.request = { url: safeUrl(p.request.url), method: /^[A-Z]{1,12}$/.test(p.request.method) ? p.request.method : '[UNKNOWN]', hasPostData: Boolean(p.request.hasPostData), headerCount: Object.keys(p.request.headers || {}).length };
  if (typeof p.request?.postData === 'string') {
    const bytes = Buffer.byteLength(p.request.postData);
    let shape = { type: 'text', bytes };
    if (bytes <= 262144) { try { shape = jsonShape(JSON.parse(p.request.postData)); } catch { /* Values stay in memory. */ } }
    result.requestBody = { bytes, shape, ...(bytes > 262144 ? { status: 'shape-byte-cap' } : {}) };
  } else if (p.request?.hasPostData) result.requestBody = { status: 'post-data-not-in-event' };
  if (p.initiator) result.initiator = { ...(typeof p.initiator.url === 'string' ? { url: safeUrl(p.initiator.url) } : {}), ...(typeof p.initiator.lineNumber === 'number' ? { lineNumber: p.initiator.lineNumber } : {}), ...(typeof p.initiator.columnNumber === 'number' ? { columnNumber: p.initiator.columnNumber } : {}) };
  if (event.method === 'Network.responseReceivedExtraInfo' && typeof p.statusCode === 'number') result.statusCode = p.statusCode;
  // CDP also calls a WebSocketFrame `response`; it has no HTTP URL, MIME or cache fields.
  const redirect = event.method === 'Network.requestWillBeSent' ? p.redirectResponse : undefined;
  const response = event.method === 'Network.responseReceived' ? p.response : redirect;
  if (response) result[redirect ? 'redirectResponse' : 'response'] = { url: safeUrl(response.url), status: typeof response.status === 'number' ? response.status : undefined, mimeType: safeText(response.mimeType, 120), protocol: safeText(response.protocol, 30), fromDiskCache: Boolean(response.fromDiskCache), fromServiceWorker: Boolean(response.fromServiceWorker), timing: Object.fromEntries(Object.entries(response.timing || {}).filter(([k, v]) => /^[a-zA-Z]{1,40}$/.test(k) && typeof v === 'number')) };
  if (p.url) result.url = safeUrl(p.url);
  if (event.method === 'Network.webSocketFrameReceived' || event.method === 'Network.webSocketFrameSent') result.frame = { opcode: p.response?.opcode, mask: p.response?.mask, payloadBytes: Buffer.byteLength(p.response?.payloadData || '') };
  if (event.method === 'Network.eventSourceMessageReceived') result.stream = { eventName: /^[\w.-]{1,60}$/.test(p.eventName || '') ? p.eventName : '[OMITTED]', payloadBytes: Buffer.byteLength(p.data || '') };
  if (event.method === 'Runtime.consoleAPICalled') result.console = { type: safeText(p.type, 30), argumentTypes: (p.args || []).map(arg => ({ type: safeText(arg.type, 30), subtype: safeText(arg.subtype, 30) })) };
  if (event.method === 'Runtime.exceptionThrown') result.exception = { exceptionId: p.exceptionDetails?.exceptionId, lineNumber: p.exceptionDetails?.lineNumber, columnNumber: p.exceptionDetails?.columnNumber, text: '[OMITTED]' };
  // Error text, stack traces, initiator URLs, headers, bodies, console values are intentionally omitted.
  return { method: event.method, sequence: event.sequence, source: sourceIdentity(event.source), params: result };
}
