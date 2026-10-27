import { randomUUID } from 'node:crypto';
import { open, readFile } from 'node:fs/promises';
import path from 'node:path';
import { createEventRing } from './event-ring.mjs';
import { inspectGraphqlEnvelope } from './graphql-envelope.mjs';
import { inspectProtocolEnvelope } from './protocol-envelope.mjs';
import { METHODS } from '../browser-inspection/capture.mjs';
import { eventMetadata } from '../browser-inspection/redaction.mjs';

/**
 * Attach a disposable Playwright page to Footwork's existing pull-style recorder.
 * The page/context is supplied by the caller; this module never launches or navigates.
 * Only the page target is covered (not workers, service workers or OOPIFs).
 */
export async function createPlaywrightCdpBridge({ page, allowedOrigin, preNavigation = false, allowedOperations = [], graphqlPath = '/api/graphql', allowedEvents = [], allowedTopicFamilies = [], maxEnvelopeRecords = 10000, maxEvents = 10000, maxEventBytes = 1048576 } = {}) {
  if (!page?.context || typeof page.url !== 'function') throw new Error('An existing Playwright page is required');
  if (!Number.isSafeInteger(maxEnvelopeRecords) || maxEnvelopeRecords < 1 || maxEnvelopeRecords > 100000) throw new Error('Invalid envelope cap');
  const declared = new URL(allowedOrigin);
  if (declared.protocol !== 'https:' || declared.origin !== allowedOrigin) throw new Error('An exact allowed HTTPS origin is required');
  const current = new URL(page.url());
  if (preNavigation ? page.url() !== 'about:blank' : current.origin !== allowedOrigin || current.protocol !== 'https:') {
    throw new Error(preNavigation ? 'Pre-navigation page must be blank' : 'Page must already be on the allowed HTTPS origin');
  }
  const session = await page.context().newCDPSession(page);
  const sessionId = `playwright-${randomUUID()}`; // logical identity for this one attached session
  const ring = createEventRing({ sessionId, methods: METHODS, maxEvents, maxEventBytes });
  const envelopeRecords = [];
  let envelopeDropped = 0, parserFailures = 0, closed = false, pageClosed = false, coldEntrySequence = null, coldMainFrameId = null;
  const observedTargets = { frameAttached: 0, dedicatedWorker: 0, serviceWorker: 0 };
  const context = page.context();
  const listeners = [];
  const addEnvelope = record => {
    envelopeRecords.push(record);
    if (envelopeRecords.length > maxEnvelopeRecords) { envelopeRecords.shift(); envelopeDropped++; }
  };
  for (const method of METHODS) {
    const listener = params => {
      if (closed) return;
      const result = ring.ingest({ method, params, source: { sessionId } });
      if (!result.accepted) return;
      const event = { method, params, sequence: result.sequence };
      try {
        if (method === 'Network.requestWillBeSent') {
          const metadata = inspectGraphqlEnvelope(event, { allowedOrigin, graphqlPath, allowedOperations });
          if (metadata.status !== 'not-target') addEnvelope(metadata);
        } else if (method === 'Network.webSocketFrameSent' || method === 'Network.webSocketFrameReceived') {
          addEnvelope(inspectProtocolEnvelope(event, { allowedEvents, allowedTopicFamilies }));
        }
      } catch { parserFailures++; }
    };
    session.on(method, listener);
    listeners.push([method, listener]);
  }
  const onPageClosed = () => { pageClosed = true; ring.disconnect(); };
  page.on('close', onPageClosed);
  page.on('crash', onPageClosed);
  const onFrameAttached = () => { observedTargets.frameAttached++; };
  const onWorker = () => { observedTargets.dedicatedWorker++; };
  const onServiceWorker = () => { observedTargets.serviceWorker++; };
  page.on('frameattached', onFrameAttached);
  page.on('worker', onWorker);
  context.on?.('serviceworker', onServiceWorker);
  if (preNavigation) {
    // No disk writer exists yet. Raw events remain bounded in process memory until verification.
    try {
      await session.send('Network.enable', { maxTotalBufferSize: 4194304, maxResourceBufferSize: 1048576, maxPostDataSize: 262144 });
      await session.send('Runtime.enable');
      await session.send('Page.enable');
    } catch (error) {
      for (const [method, listener] of listeners) session.off(method, listener);
      page.off('close', onPageClosed); page.off('crash', onPageClosed);
      page.off('frameattached', onFrameAttached); page.off('worker', onWorker);
      context.off?.('serviceworker', onServiceWorker);
      await session.detach().catch(() => {});
      throw error;
    }
  }
  const tab = {
    url: async () => page.url(),
    playwright: { domSnapshot: async () => page.locator('body').ariaSnapshot() },
    screenshot: options => page.screenshot(options),
  };
  const cdp = {
    send: (method, params = {}) => session.send(method, params),
    readEvents: options => ring.readEvents(options),
  };
  return {
    tab, cdp, target: { sessionId },
    async verifyColdEntry() {
      if (!preNavigation || closed || pageClosed || coldEntrySequence !== null) throw new Error('Cold entry is unavailable or already verified');
      if (new URL(page.url()).origin !== allowedOrigin) throw new Error('Cold entry ended outside the allowed origin');
      const tree = await session.send('Page.getFrameTree');
      const mainFrameId = tree?.frameTree?.frame?.id;
      if (typeof mainFrameId !== 'string' || !mainFrameId) throw new Error('Main frame identity unavailable');
      const status = ring.status();
      if (status.lostThrough || status.droppedEvicted || status.droppedOversize) throw new Error('Cold entry event buffer is incomplete');
      const events = await collectColdEvents(ring, status.sequence);
      const documents = events.filter(event => event.method === 'Network.requestWillBeSent' && event.params?.type === 'Document' && event.params?.frameId === mainFrameId);
      if (!documents.length || documents.some(event => { try { return new URL(event.params.request?.url).origin !== allowedOrigin; } catch { return true; } })) {
        throw new Error('Main document request did not stay on the allowed origin');
      }
      coldMainFrameId = mainFrameId;
      coldEntrySequence = status.sequence;
      return { verified: true, mainDocumentRequests: documents.length, eventCount: events.length };
    },
    async coldEntry() {
      if (!preNavigation || closed || pageClosed || coldEntrySequence === null || new URL(page.url()).origin !== allowedOrigin) throw new Error('Verified cold entry unavailable');
      const status = ring.status();
      if (status.lostThrough || status.droppedEvicted || status.droppedOversize) throw new Error('Cold entry event buffer became incomplete');
      const events = await collectColdEvents(ring, coldEntrySequence);
      const allowedRequestIds = new Set(events.filter(event => event.method === 'Network.requestWillBeSent' && sameOrigin(event.params?.request?.url, allowedOrigin) &&
        (!event.params?.redirectResponse || sameOrigin(event.params.redirectResponse.url, allowedOrigin))).map(event => event.params.requestId));
      const fenced = events.filter(event => event.method.startsWith('Network.') && allowedRequestIds.has(event.params?.requestId));
      return { events: fenced.map(eventMetadata), mainFrameIdentityVerified: Boolean(coldMainFrameId),
        coverage: { pageTargetOnly: true, coldInitialNavigation: true, eventCount: fenced.length,
          excludedEvents: events.length - fenced.length,
          domainsEnabledByBridge: ['Network', 'Runtime', 'Page'],
          observedTargets: { ...observedTargets }, currentTargets: {
            frames: typeof page.frames === 'function' ? page.frames().length : null,
            dedicatedWorkers: typeof page.workers === 'function' ? page.workers().length : null,
            serviceWorkers: typeof context.serviceWorkers === 'function' ? context.serviceWorkers().length : null,
          }, workerAndOutOfProcessFrameTraffic: 'unattached' } };
    },
    metadata() { return { records: [...envelopeRecords], envelopeDropped, parserFailures, ring: ring.status(),
      targetCoverage: { pageTargetOnly: true, observedTargets: { ...observedTargets }, currentTargets: {
        frames: typeof page.frames === 'function' ? page.frames().length : null,
        dedicatedWorkers: typeof page.workers === 'function' ? page.workers().length : null,
        serviceWorkers: typeof context.serviceWorkers === 'function' ? context.serviceWorkers().length : null,
      }, workerAndOutOfProcessFrameTraffic: 'unattached' } }; },
    async close() {
      if (closed) return;
      closed = true;
      ring.disconnect();
      for (const [method, listener] of listeners) session.off(method, listener);
      page.off('close', onPageClosed);
      page.off('crash', onPageClosed);
      page.off('frameattached', onFrameAttached);
      page.off('worker', onWorker);
      context.off?.('serviceworker', onServiceWorker);
      if (preNavigation) {
        try { await session.send('Network.disable'); } catch { /* Disposable session cleanup. */ }
        try { await session.send('Runtime.disable'); } catch { /* Disposable session cleanup. */ }
        try { await session.send('Page.disable'); } catch { /* Disposable session cleanup. */ }
      }
      await session.detach();
    },
  };
}

async function collectColdEvents(ring, throughSequence) {
  const events = [];
  let cursor = 0;
  while (cursor < throughSequence) {
    const batch = await ring.readEvents({ afterSequence: cursor, limit: 1000, methods: METHODS });
    if (batch.truncated || batch.cursor <= cursor) throw new Error('Cold entry events are incomplete');
    events.push(...batch.events);
    cursor = batch.cursor;
  }
  return events.filter(event => event.sequence <= throughSequence);
}

function sameOrigin(value, allowedOrigin) {
  try { return new URL(value).origin === allowedOrigin; } catch { return false; }
}

/** Persist only sanitized, verified pre-navigation metadata before capture.stop() seals it. */
export async function writeColdEntryArtifact({ runDirectory, bridge, label = 'cold-entry' } = {}) {
  if (!/^[\w-]{1,80}$/.test(label) || !runDirectory || !bridge?.coldEntry) throw new Error('Run directory, bridge and safe label required');
  try { await readFile(path.join(runDirectory, 'manifest.json')); throw new Error('Run is already sealed'); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  const entry = await bridge.coldEntry();
  const filename = path.join(runDirectory, 'artifacts', `${label}.json`);
  const handle = await open(filename, 'wx', 0o600);
  try {
    const report = { schemaVersion: 1, kind: 'cold-entry', mainFrameIdentityVerified: entry.mainFrameIdentityVerified,
      events: entry.events, coverage: entry.coverage };
    await handle.writeFile(`${JSON.stringify(report)}\n`);
    await handle.sync();
    return { path: filename, eventCount: entry.events.length, coverage: entry.coverage };
  } finally { await handle.close(); }
}

/** Save only metadata records before capture.stop() seals its artifact manifest. */
export async function writeEnvelopeArtifact({ runDirectory, bridge, label = 'protocol-envelopes' } = {}) {
  if (!/^[\w-]{1,80}$/.test(label) || !runDirectory || !bridge?.metadata) throw new Error('Run directory, bridge and safe label required');
  try { await readFile(path.join(runDirectory, 'manifest.json')); throw new Error('Run is already sealed'); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  const { records, envelopeDropped, parserFailures, ring, targetCoverage } = bridge.metadata();
  const filename = path.join(runDirectory, 'artifacts', `${label}.json`);
  const handle = await open(filename, 'wx', 0o600);
  try {
    const report = { schemaVersion: 1, kind: 'protocol-envelopes', records, coverage: {
      envelopeDropped, parserFailures, ringLostThrough: ring.lostThrough,
      ringDroppedEvicted: ring.droppedEvicted, ringDroppedOversize: ring.droppedOversize,
      pageTargetOnly: true, targetCoverage,
    } };
    await handle.writeFile(`${JSON.stringify(report)}\n`);
    await handle.sync();
    return { path: filename, count: records.length, coverage: report.coverage };
  } finally { await handle.close(); }
}
