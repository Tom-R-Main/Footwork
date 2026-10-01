import { randomUUID } from 'node:crypto';
import { open, readFile } from 'node:fs/promises';
import path from 'node:path';
import { createEventRing } from './event-ring.mjs';
import { inspectGraphqlEnvelope } from './graphql-envelope.mjs';
import { inspectProtocolEnvelope } from './protocol-envelope.mjs';
import { METHODS } from '../browser-inspection/capture.mjs';

/**
 * Attach a disposable Playwright page to Footwork's existing pull-style recorder.
 * The page/context is supplied by the caller; this module never launches or navigates.
 * Only the page target is covered (not workers, service workers or OOPIFs).
 */
export async function createPlaywrightCdpBridge({ page, allowedOrigin, allowedOperations = [], graphqlPath = '/api/graphql', allowedEvents = [], allowedTopicFamilies = [], maxEnvelopeRecords = 10000, maxEvents = 10000, maxEventBytes = 1048576 } = {}) {
  if (!page?.context || typeof page.url !== 'function') throw new Error('An existing Playwright page is required');
  if (!Number.isSafeInteger(maxEnvelopeRecords) || maxEnvelopeRecords < 1 || maxEnvelopeRecords > 100000) throw new Error('Invalid envelope cap');
  const current = new URL(page.url());
  if (current.origin !== allowedOrigin || current.protocol !== 'https:') throw new Error('Page must already be on the allowed HTTPS origin');
  const session = await page.context().newCDPSession(page);
  const sessionId = `playwright-${randomUUID()}`; // logical identity for this one attached session
  const ring = createEventRing({ sessionId, methods: METHODS, maxEvents, maxEventBytes });
  const envelopeRecords = [];
  let envelopeDropped = 0, parserFailures = 0, closed = false;
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
  const onPageClosed = () => { if (!closed) { closed = true; ring.disconnect(); } };
  page.on('close', onPageClosed);
  page.on('crash', onPageClosed);
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
    metadata() { return { records: [...envelopeRecords], envelopeDropped, parserFailures, ring: ring.status() }; },
    async close() {
      if (closed) return;
      closed = true;
      ring.disconnect();
      for (const [method, listener] of listeners) session.off(method, listener);
      page.off('close', onPageClosed);
      page.off('crash', onPageClosed);
      await session.detach();
    },
  };
}

/** Save only metadata records before capture.stop() seals its artifact manifest. */
export async function writeEnvelopeArtifact({ runDirectory, bridge, label = 'protocol-envelopes' } = {}) {
  if (!/^[\w-]{1,80}$/.test(label) || !runDirectory || !bridge?.metadata) throw new Error('Run directory, bridge and safe label required');
  try { await readFile(path.join(runDirectory, 'manifest.json')); throw new Error('Run is already sealed'); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  const { records, envelopeDropped, parserFailures, ring } = bridge.metadata();
  const filename = path.join(runDirectory, 'artifacts', `${label}.json`);
  const handle = await open(filename, 'wx', 0o600);
  try {
    const report = { schemaVersion: 1, kind: 'protocol-envelopes', records, coverage: {
      envelopeDropped, parserFailures, ringLostThrough: ring.lostThrough,
      ringDroppedEvicted: ring.droppedEvicted, ringDroppedOversize: ring.droppedOversize,
      pageTargetOnly: true,
    } };
    await handle.writeFile(`${JSON.stringify(report)}\n`);
    await handle.sync();
    return { path: filename, count: records.length, coverage: report.coverage };
  } finally { await handle.close(); }
}
