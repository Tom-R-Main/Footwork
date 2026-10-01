/** Extract GraphQL operation identity transiently from CDP requestWillBeSent. */
const OPERATION = /^[A-Za-z_][A-Za-z0-9_]{0,79}$/;

function queryKind(query) {
  if (typeof query !== 'string') return 'unknown';
  // Ignore leading GraphQL comments; never retain the query text.
  const prefix = query.slice(0, 4096).replace(/^(?:\s|#[^\n]*(?:\n|$))*/, '');
  return /^(query|mutation|subscription)\b/.exec(prefix)?.[1] || 'unknown';
}

/**
 * No URL, query, variables, extensions, body text, headers or unknown operation names
 * are returned. The allowed operation list should come from a reviewed public client
 * catalog or a task-specific fixture, not from untrusted request data.
 */
export function inspectGraphqlEnvelope(event, { allowedOrigin, graphqlPath = '/api/graphql', allowedOperations = [], maxPostBytes = 1048576 } = {}) {
  let origin;
  try { origin = new URL(allowedOrigin); } catch { throw new Error('Exact HTTPS allowedOrigin required'); }
  if (origin.protocol !== 'https:' || origin.origin !== allowedOrigin) throw new Error('Exact HTTPS allowedOrigin required');
  if (!graphqlPath.startsWith('/') || graphqlPath.includes('?') || graphqlPath.includes('#')) throw new Error('Invalid GraphQL path');
  if (!Number.isSafeInteger(maxPostBytes) || maxPostBytes < 1024 || maxPostBytes > 4194304) throw new Error('Invalid post-data cap');
  if (event?.method !== 'Network.requestWillBeSent') throw new Error('Expected CDP requestWillBeSent');
  const request = event.params?.request || {};
  const base = { schemaVersion: 1, kind: 'graphql-envelope', status: 'not-target' };
  let url;
  try { url = new URL(request.url); } catch { return base; }
  if (url.origin !== allowedOrigin || url.pathname !== graphqlPath || request.method !== 'POST') return base;
  const timestamp = Number.isFinite(event.params?.timestamp) && event.params.timestamp >= 0 ? event.params.timestamp : null;
  const sequence = Number.isSafeInteger(event.sequence) && event.sequence >= 0 ? event.sequence : null;
  const target = { ...base, timestamp, sequence };
  if (typeof request.postData !== 'string') return { ...target, status: 'body-unavailable' };
  const postBytes = Buffer.byteLength(request.postData);
  if (postBytes > maxPostBytes) return { ...target, status: 'oversized', postBytes };
  let body;
  try { body = JSON.parse(request.postData); } catch { return { ...target, status: 'invalid-json', postBytes }; }
  const batch = Array.isArray(body) ? body : [body];
  const allowed = new Set(allowedOperations);
  const operations = batch.slice(0, 20).map(item => {
    const name = typeof item?.operationName === 'string' && OPERATION.test(item.operationName) && allowed.has(item.operationName) ? item.operationName : null;
    const variableCount = item?.variables && typeof item.variables === 'object' && !Array.isArray(item.variables) ? Object.keys(item.variables).length : 0;
    return { name, nameStatus: name ? 'allowed' : typeof item?.operationName === 'string' ? 'unlisted' : 'absent',
      queryKind: queryKind(item?.query), variableCount, queryBytes: typeof item?.query === 'string' ? Buffer.byteLength(item.query) : 0 };
  });
  return { ...target, status: 'parsed', postBytes, batchCount: batch.length, batchTruncated: batch.length > 20, operations };
}
