import { createHash } from 'node:crypto';
import { open, realpath, lstat } from 'node:fs/promises';
import { join, relative, isAbsolute } from 'node:path';

/**
 * Page-local, metadata-only stream observer. No response content is retained.
 * `installStreamProbe` is self-contained so its source can be injected into a page.
 */
export function installStreamProbe(host, { allowedOrigin, emit, maxChunks = 200, maxBytes = 1048576, maxActive = 8, stopTimeoutMs = 2000 } = {}) {
  let origin;
  try { origin = new URL(allowedOrigin); } catch { throw new Error('Explicit HTTPS allowedOrigin required'); }
  if (origin.protocol !== 'https:' || origin.origin !== allowedOrigin) throw new Error('allowedOrigin must be an exact HTTPS origin');
  if (typeof host?.fetch !== 'function' || typeof emit !== 'function') throw new Error('Fetch host and metadata sink required');
  if (![maxChunks, maxBytes, maxActive, stopTimeoutMs].every(Number.isSafeInteger) || maxChunks < 1 || maxChunks > 1000 || maxBytes < 1024 || maxBytes > 4194304 || maxActive < 1 || maxActive > 32 || stopTimeoutMs < 10 || stopTimeoutMs > 10000) throw new Error('Invalid stream observation limits');
  const originalFetch = host.fetch;
  const active = new Set();
  let ordinal = 0, stopped = false;
  const now = () => typeof host.performance?.now === 'function' ? host.performance.now() : Date.now();
  const sameOrigin = value => { try { return new URL(value, host.location?.href || allowedOrigin).origin === allowedOrigin; } catch { return false; } };
  const contentTypeFamily = value => {
    const type = String(value || '').split(';', 1)[0].trim().toLowerCase();
    if (type === 'text/event-stream') return 'sse';
    if (/^(?:application\/)?(?:x-)?ndjson$/.test(type) || type === 'application/jsonl') return 'ndjson';
    if (type === 'text/plain' || /stream/i.test(type)) return 'text-stream';
    return null;
  };
  const send = record => { try { emit(record); } catch { /* Instrumentation never changes app fetch behavior. */ } };

  async function observe(response, detail) {
    let clone;
    try { clone = response.clone(); } catch {
      send({ ...detail, kind: 'fetch-stream-summary', coverage: 'clone-unavailable' });
      return;
    }
    if (!clone.body) { send({ ...detail, kind: 'fetch-stream-summary', coverage: 'body-unavailable' }); return; }
    const item = { reader: null, task: null };
    active.add(item);
    item.task = (async () => {
      const timesMs = [], sizesBytes = [];
      let chunkCount = 0, bytes = 0, firstChunkMs = null, coverage = 'observed';
      try {
        item.reader = clone.body.getReader();
        for (;;) {
          const { done, value } = await item.reader.read();
          if (done) { if (stopped) coverage = 'stopped'; break; }
          const size = value?.byteLength ?? 0;
          chunkCount++;
          bytes += size;
          const elapsed = Math.max(0, Math.round(now() - detail.startedAtMonotonicMs));
          if (firstChunkMs === null) firstChunkMs = elapsed;
          timesMs.push(elapsed);
          sizesBytes.push(size);
          if (stopped || chunkCount >= maxChunks || bytes >= maxBytes) {
            coverage = stopped ? 'stopped' : 'capped';
            // A tee branch's cancel promise can wait for the application's branch.
            // Request cancellation without blocking the observation summary.
            void item.reader.cancel().catch(() => {});
            break;
          }
        }
      } catch { coverage = stopped ? 'stopped' : 'read-error'; }
      finally {
        active.delete(item);
        send({ ...detail, kind: 'fetch-stream-summary', coverage, firstChunkMs,
          totalMs: Math.max(0, Math.round(now() - detail.startedAtMonotonicMs)), chunkCount, observedBytes: bytes,
          chunkTimesMs: timesMs, chunkSizesBytes: sizesBytes });
      }
    })();
  }

  async function wrappedFetch(input, init) {
    const startedAtMonotonicMs = now();
    const startedAtEpochMs = Date.now();
    const requestUrl = typeof input === 'string' ? input : input?.url ?? String(input);
    const response = await Reflect.apply(originalFetch, this, [input, init]);
    if (stopped || !sameOrigin(requestUrl) || (response.url && !sameOrigin(response.url))) return response;
    const family = contentTypeFamily(response.headers?.get?.('content-type'));
    if (!family) return response;
    const detail = { requestOrdinal: ++ordinal, startedAtEpochMs, startedAtMonotonicMs,
      responseMs: Math.max(0, Math.round(now() - startedAtMonotonicMs)), status: Number.isInteger(response.status) ? response.status : null,
      contentTypeFamily: family };
    if (active.size >= maxActive) send({ ...detail, kind: 'fetch-stream-summary', coverage: 'active-cap' });
    else void observe(response, detail);
    return response;
  }
  host.fetch = wrappedFetch;
  return {
    async stop() {
      if (stopped) return;
      stopped = true;
      if (host.fetch === wrappedFetch) host.fetch = originalFetch;
      const pending = [...active];
      for (const item of pending) if (item.reader) void item.reader.cancel().catch(() => {});
      let timeout;
      await Promise.race([
        Promise.allSettled(pending.map(item => item.task)),
        new Promise(resolve => { timeout = setTimeout(resolve, stopTimeoutMs); }),
      ]);
      clearTimeout(timeout);
    },
    status() { return { active: active.size, intercepted: ordinal, stopped }; },
  };
}

/** Build a script for the existing permitted tab's evaluate operation; it makes no browser connection. */
export function buildStreamProbeSource({ allowedOrigin, maxChunks = 200, maxBytes = 1048576, maxActive = 8, stopTimeoutMs = 2000, maxRecords = 1000 } = {}) {
  if (!Number.isSafeInteger(maxRecords) || maxRecords < 1 || maxRecords > 10000) throw new Error('maxRecords must be 1..10000');
  const settings = JSON.stringify({ allowedOrigin, maxChunks, maxBytes, maxActive, stopTimeoutMs });
  return `(() => {
    if (window.__footworkStreamProbe) {
      const prior = window.__footworkStreamProbe.stats();
      if (!prior.stopped) return { alreadyInstalled: true, ...prior };
      if (prior.buffered) return { needsDrain: true, ...prior };
    }
    const install = ${installStreamProbe.toString()};
    const records = []; let dropped = 0;
    const probe = install(window, { ...${settings}, emit: record => {
      records.push(record);
      if (records.length > ${maxRecords}) { records.shift(); dropped++; }
    }});
    window.__footworkStreamProbe = {
      drain(n = 100) { if (!Number.isSafeInteger(n) || n < 1 || n > 1000) throw new Error('Invalid drain size'); return records.splice(0, n); },
      stats() { return { buffered: records.length, dropped, ...probe.status() }; },
      async stop() { await probe.stop(); return this.stats(); },
    };
    return { installed: true, ...window.__footworkStreamProbe.stats() };
  })()`;
}

const COVERAGE = new Set(['observed', 'capped', 'stopped', 'read-error', 'clone-unavailable', 'body-unavailable', 'active-cap']);
const FAMILY = new Set(['sse', 'ndjson', 'text-stream']);
const integer = (value, max) => Number.isSafeInteger(value) && value >= 0 && value <= max ? value : null;
export function sanitizeStreamRecord(row) {
  if (!row || row.kind !== 'fetch-stream-summary') throw new Error('Invalid stream record kind');
  const cappedArray = value => Array.isArray(value) ? value.slice(0, 1000).map(item => integer(item, 86400000)).filter(item => item !== null) : [];
  return {
    schemaVersion: 1, kind: 'fetch-stream-summary',
    requestOrdinal: integer(row.requestOrdinal, 1000000),
    startedAtEpochMs: integer(row.startedAtEpochMs, 10000000000000),
    startedAtMonotonicMs: integer(Math.round(row.startedAtMonotonicMs), 86400000),
    responseMs: integer(row.responseMs, 86400000),
    status: Number.isInteger(row.status) && row.status >= 100 && row.status <= 599 ? row.status : null,
    contentTypeFamily: FAMILY.has(row.contentTypeFamily) ? row.contentTypeFamily : 'unknown',
    coverage: COVERAGE.has(row.coverage) ? row.coverage : 'unknown',
    firstChunkMs: integer(row.firstChunkMs, 86400000), totalMs: integer(row.totalMs, 86400000),
    chunkCount: integer(row.chunkCount, 1000000), observedBytes: integer(row.observedBytes, 1000000000),
    chunkTimesMs: cappedArray(row.chunkTimesMs), chunkSizesBytes: cappedArray(row.chunkSizesBytes),
  };
}

function sanitizeProbeStatus(status) {
  if (!status || typeof status !== 'object') throw new Error('Probe status required');
  return { schemaVersion: 1, kind: 'stream-probe-status',
    buffered: integer(status.buffered, 10000), dropped: integer(status.dropped, 1000000000),
    active: integer(status.active, 32), intercepted: integer(status.intercepted, 1000000),
    stopped: status.stopped === true };
}

/** Write before capture.stop(), so the recorder's manifest includes this artifact. */
export async function writeStreamArtifact({ runDirectory, label, records, probeStatus } = {}) {
  if (!/^[\w-]{1,100}$/.test(label ?? '') || !Array.isArray(records) || records.length > 1000) throw new Error('Safe label and bounded stream records required');
  const root = await realpath(runDirectory);
  try { await lstat(join(root, 'manifest.json')); throw new Error('Cannot add an artifact after the run is sealed'); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  const artifacts = await realpath(join(root, 'artifacts'));
  const rel = relative(root, artifacts);
  if (!rel || rel.startsWith('..') || isAbsolute(rel)) throw new Error('Artifact directory escapes run');
  const rows = [...records.map(sanitizeStreamRecord), ...(probeStatus ? [sanitizeProbeStatus(probeStatus)] : [])];
  const content = `${rows.map(row => JSON.stringify(row)).join('\n')}${rows.length ? '\n' : ''}`;
  const bytes = Buffer.from(content);
  if (bytes.length > 8 * 1024 * 1024) throw new Error('Stream artifact exceeds byte cap');
  const name = `${label}.stream.jsonl`;
  const handle = await open(join(artifacts, name), 'wx', 0o600);
  try { await handle.writeFile(bytes); await handle.sync(); } finally { await handle.close(); }
  return { path: `artifacts/${name}`, records: records.length, statusIncluded: Boolean(probeStatus), bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') };
}
