import { open, mkdir, realpath, readdir, readFile } from 'node:fs/promises';
import path from 'node:path';
import { createHash, randomUUID } from 'node:crypto';
import { safeText, safeUrl, eventMetadata, sourceIdentity, jsonShape, fixtureValues } from './redaction.mjs';

export const METHODS = Object.freeze([
  'Network.requestWillBeSent', 'Network.responseReceived', 'Network.loadingFinished', 'Network.loadingFailed',
  'Network.dataReceived', 'Network.requestServedFromCache', 'Network.responseReceivedExtraInfo', 'Network.eventSourceMessageReceived',
  'Network.webSocketCreated', 'Network.webSocketClosed', 'Network.webSocketFrameReceived', 'Network.webSocketFrameSent',
  'Runtime.consoleAPICalled', 'Runtime.exceptionThrown',
]);
const JOURNALS = ['events.jsonl', 'actions.jsonl', 'gaps.jsonl', 'bodies.jsonl'];
const iso = () => new Date().toISOString();
const sourceKey = (source, id) => JSON.stringify([source?.sessionId, source?.targetId, source?.tabId, source?.extensionId, id]);
const textual = mime => /^(?:application\/(?:[\w.+-]*json|javascript|xml)|text\/)/i.test(mime || '');
const jsonMime = mime => /^(?:application|text)\/[\w.+-]*json(?:;|$)/i.test(mime || '');
const inside = (root, candidate) => candidate === root || candidate.startsWith(`${root}${path.sep}`);
const safeId = value => typeof value === 'string' && /^[\w-]{1,100}$/.test(value);
const originOf = value => { try { return new URL(value).origin; } catch { return ''; } };
const websocketOrigin = value => { try { const url = new URL(value); return url.protocol === 'wss:' ? `https://${url.host}` : ''; } catch { return ''; } };

/** Inject an already selected plugin tab + its CDP bridge. Never connects, navigates or reads auth storage. */
export function createCapture({ tab, cdp, projectRoot, allowedOrigin, outputName = 'browser-inspection', runId = `run-${randomUUID()}`, target, maxBodyBytes = 262144, maxDrainPages = 100, eventTimeoutMs = 500, networkBufferBytes = 4194304, resourceBufferBytes = Math.min(1048576, maxBodyBytes, networkBufferBytes), fixtureBodyValues = false, deliveredSourceText = false, privateDom = false, privateScreenshots = false, domainsToEnable = ['Network'], ownDomainLifecycle = false } = {}) {
  let declared;
  try { declared = new URL(allowedOrigin); } catch { throw new Error('An explicit HTTPS allowedOrigin is required'); }
  if (declared.protocol !== 'https:' || declared.origin !== allowedOrigin) throw new Error('allowedOrigin must be an exact HTTPS origin without path, query or credentials');
  if (!/^[\w-]{1,80}$/.test(outputName)) throw new Error('A safe outputName is required');
  if (!tab?.url || !cdp?.send || !cdp?.readEvents) throw new Error('Existing browser tab and CDP bridge required');
  if (!path.isAbsolute(projectRoot || '') || !safeId(runId)) throw new Error('Absolute project root and safe runId required');
  if (!Number.isInteger(maxBodyBytes) || maxBodyBytes < 1 || maxBodyBytes > 1048576) throw new Error('maxBodyBytes must be 1..1048576');
  if (!Number.isInteger(maxDrainPages) || maxDrainPages < 1 || maxDrainPages > 1000) throw new Error('maxDrainPages must be 1..1000');
  if (!Number.isInteger(eventTimeoutMs) || eventTimeoutMs < 50 || eventTimeoutMs > 1000) throw new Error('eventTimeoutMs must be 50..1000');
  if (!Number.isInteger(networkBufferBytes) || networkBufferBytes < 1 || networkBufferBytes > 4194304) throw new Error('networkBufferBytes must be 1..4194304');
  if (!Number.isInteger(resourceBufferBytes) || resourceBufferBytes < 1 || resourceBufferBytes > Math.min(1048576, networkBufferBytes)) throw new Error('resourceBufferBytes must be 1..min(1048576,networkBufferBytes)');
  if (!Array.isArray(domainsToEnable) || domainsToEnable.some(d => !['Network', 'Runtime'].includes(d))) throw new Error('Only Network and Runtime domains may be enabled');
  if (privateScreenshots && !privateDom) throw new Error('Screenshots require privateDom for credential-screen preflight');
  let directory, cursor, started = false, stopped = false, stopping = false, busy = false, stepNumber = 0;
  let tail = Promise.resolve(), activeStep, stopPromise, startPromise, originPaused = false, originCheckUnavailable = false, timer;
  const enabled = new Set(), unsupported = [], responses = new Map(), sockets = new Map(), writers = new Map();
  const stepIds = new Set(), artifactLabels = new Set(), cleanupFailures = [];
  const counts = { events: 0, actions: 0, bodies: 0, gaps: 0 };
  const polling = { active: false, everStarted: false, intervalMs: null, ticks: 0, pauseReason: null };
  const sendOptions = { ...(target ? { target } : {}), timeoutMs: eventTimeoutMs };
  const enqueue = task => { const result = tail.then(task); tail = result.catch(() => {}); return result; };
  const assertRunning = () => { if (!started || stopped) throw new Error('Capture is not running'); };
  const assertAccepting = () => { assertRunning(); if (stopping) throw new Error('Capture is stopping'); };
  const cancelTimer = () => { if (timer !== undefined) clearTimeout(timer); timer = undefined; polling.active = false; };
  const journal = async (name, type, data) => {
    const row = { schemaVersion: 1, type, recordedAt: iso(), runId, ...data };
    const writer = writers.get(name);
    if (!writer) throw new Error('Journal writer is closed');
    // One serialized queue owns each handle. Sync before resolving the operation or sealing hashes.
    const buffer = Buffer.from(`${JSON.stringify(row)}\n`);
    let offset = 0;
    while (offset < buffer.length) {
      const { bytesWritten } = await writer.write(buffer, offset, buffer.length - offset);
      if (!bytesWritten) throw new Error('Journal writer made no progress');
      offset += bytesWritten;
    }
    await writer.sync();
    counts[name.split('.')[0]]++;
  };
  const gap = (reason, extra = {}) => journal('gaps.jsonl', 'gap', { reason, cursor, ...extra });
  async function scope() {
    if (originPaused) throw Object.assign(new Error('Capture paused after leaving allowedOrigin; start a new scoped run'), { captureReason: 'origin-changed' });
    let url;
    try { url = await tab.url(); } catch {
      if (!originCheckUnavailable && writers.has('gaps.jsonl')) await gap('origin-check-unavailable');
      originCheckUnavailable = true;
      throw Object.assign(new Error('Current tab origin unavailable'), { captureReason: 'origin-check-unavailable' });
    }
    originCheckUnavailable = false;
    if (originOf(url) !== allowedOrigin) {
      originPaused = true;
      cancelTimer();
      polling.pauseReason = 'origin-changed';
      responses.clear(); sockets.clear();
      if (writers.has('gaps.jsonl')) await gap('origin-changed', { url: safeUrl(url) });
      throw Object.assign(new Error('Capture requires the current tab to remain at the declared allowedOrigin'), { captureReason: 'origin-changed' });
    }
    return url;
  }
  async function durableFile(file, bytes) {
    const writer = await open(path.join(directory, file), 'wx', 0o600);
    try { await writer.writeFile(bytes); await writer.sync(); } finally { await writer.close(); }
  }

  async function body(event) {
    const p = event.params || {}, key = sourceKey(event.source, p.requestId), response = responses.get(key);
    responses.delete(key);
    if (!response) return gap('missing-response-metadata', { requestId: safeText(p.requestId, 120), source: sourceIdentity(event.source) });
    const sourceText = deliveredSourceText && /^(?:text|application)\/(?:x-)?javascript(?:;|$)/i.test(response.mimeType || '') && /\.m?js$/i.test((() => { try { return new URL(response.url).pathname; } catch { return ''; } })());
    const base = { requestId: safeText(p.requestId, 120), source: sourceIdentity(event.source), url: safeUrl(response.url), mimeType: safeText(response.mimeType, 120), captureMode: sourceText ? 'delivered-source' : fixtureBodyValues ? 'fixture-values' : 'shape' };
    if (originOf(response.url) !== allowedOrigin || !textual(response.mimeType) || /text\/event-stream/i.test(response.mimeType)) return journal('bodies.jsonl', 'body', { ...base, status: 'omitted-scope-or-mime' });
    // Asset text discarded by policy needs no body bridge call. Encoded bytes are an observed
    // loadingFinished measurement, not a decoded-content byte count or a recovered source artifact.
    if (!jsonMime(response.mimeType) && !fixtureBodyValues && !sourceText) return journal('bodies.jsonl', 'body', { ...base, status: 'omitted-content-policy', ...(typeof p.encodedDataLength === 'number' ? { encodedBytes: p.encodedDataLength } : {}) });
    if (p.encodedDataLength > maxBodyBytes) return journal('bodies.jsonl', 'body', { ...base, status: 'omitted-byte-cap', encodedBytes: p.encodedDataLength });
    try {
      await scope();
      const eventTarget = event.source?.sessionId ? { sessionId: event.source.sessionId } : event.source?.targetId ? { targetId: event.source.targetId } : target;
      const raw = await cdp.send('Network.getResponseBody', { requestId: p.requestId }, { ...sendOptions, ...(eventTarget ? { target: eventTarget } : {}) });
      await scope(); // Drop a late body if the tab crossed origin while the bridge was awaiting it.
      if (typeof raw?.body !== 'string') throw new Error('No body');
      const buffer = Buffer.from(raw.body, raw.base64Encoded ? 'base64' : 'utf8');
      if (buffer.length > maxBodyBytes) return journal('bodies.jsonl', 'body', { ...base, status: 'omitted-byte-cap', bytes: buffer.length });
      let parsed;
      try { parsed = JSON.parse(buffer.toString('utf8')); } catch { /* Values stay in memory unless fixture opt-in is explicit. */ }
      const source = buffer.toString('utf8');
      const sourceRedacted = sourceText ? safeText(source, maxBodyBytes) : undefined;
      const content = sourceText ? { text: sourceRedacted, redactionApplied: true, sourceAltered: sourceRedacted !== source, truncated: source.length > maxBodyBytes } : parsed !== undefined ? { shape: jsonShape(parsed), ...(fixtureBodyValues ? { values: fixtureValues(parsed) } : {}) } : { shape: { type: 'text', bytes: buffer.length }, ...(fixtureBodyValues ? { text: safeText(source, maxBodyBytes) } : {}) };
      await journal('bodies.jsonl', 'body', { ...base, status: 'captured', bytes: buffer.length, ...content });
    } catch {
      if (originPaused) return;
      await journal('bodies.jsonl', 'body', { ...base, status: 'unavailable' });
      await gap('body-unavailable-or-evicted', { requestId: base.requestId, source: base.source });
    }
  }

  async function drainCore() {
    assertRunning();
    if (originPaused) return { cursor, drained: false, paused: true, reason: 'origin-changed' };
    for (let page = 0; page < maxDrainPages; page++) {
      try { await scope(); } catch (error) { return { cursor, drained: false, paused: originPaused, reason: error.captureReason || 'origin-check-failed' }; }
      let batch;
      try { batch = await cdp.readEvents({ afterSequence: cursor, limit: 1000, methods: [...METHODS], ...(target ? { target } : {}), timeoutMs: eventTimeoutMs }); }
      catch { await gap('read-events-failed'); return { cursor, drained: false, reason: 'read-events-failed' }; }
      // Do not serialize any newly returned data after a cross-origin transition.
      try { await scope(); } catch (error) { return { cursor, drained: false, paused: originPaused, reason: error.captureReason || 'origin-check-failed' }; }
      if (!Number.isInteger(batch?.cursor) || !Array.isArray(batch.events)) { await gap('invalid-event-batch'); return { cursor, drained: false }; }
      if (batch.truncated) await gap('event-buffer-truncated', { nextCursor: batch.cursor });
      const previousCursor = cursor;
      if (batch.cursor < previousCursor) { await gap('cursor-regression', { nextCursor: batch.cursor }); return { cursor, drained: false }; }
      for (const event of batch.events) {
        try { await scope(); } catch (error) { return { cursor, drained: false, paused: originPaused, reason: error.captureReason || 'origin-check-failed' }; }
        if (!METHODS.includes(event.method) || !Number.isInteger(event.sequence) || event.sequence > batch.cursor) { await gap('invalid-or-unrequested-event'); continue; }
        if (event.sequence <= cursor) continue;
        await journal('events.jsonl', 'event', { event: eventMetadata(event) });
        cursor = event.sequence; // Avoid duplication if a later operation in this batch fails.
        const p = event.params || {}, key = sourceKey(event.source, p.requestId);
        if (event.method === 'Network.requestWillBeSent') responses.delete(key); // Reused redirect IDs remain journal entries.
        if (event.method === 'Network.responseReceived') responses.set(key, { url: p.response?.url, mimeType: p.response?.mimeType });
        if (event.method === 'Network.loadingFinished') await body(event);
        if (event.method === 'Network.loadingFailed') responses.delete(key);
        if (event.method === 'Network.webSocketCreated') sockets.set(key, { origin: websocketOrigin(p.url), url: p.url });
        if (event.method === 'Network.webSocketClosed') sockets.delete(key);
        if (fixtureBodyValues && ['Network.eventSourceMessageReceived', 'Network.webSocketFrameReceived', 'Network.webSocketFrameSent'].includes(event.method)) {
          const isSse = event.method === 'Network.eventSourceMessageReceived';
          const response = isSse ? responses.get(key) : sockets.get(key);
          const origin = isSse ? originOf(response?.url) : response?.origin;
          if (origin === allowedOrigin && (isSse || p.response?.opcode === 1)) {
            try { await scope(); } catch (error) { return { cursor, drained: false, paused: originPaused, reason: error.captureReason || 'origin-check-failed' }; }
            const raw = isSse ? p.data || '' : p.response?.payloadData || '';
            const bytes = Buffer.byteLength(raw);
            let parsed; try { parsed = JSON.parse(raw); } catch { /* Plain synthetic text. */ }
            await journal('bodies.jsonl', 'body', { requestId: safeText(p.requestId, 120), source: sourceIdentity(event.source), captureMode: 'fixture-values', streamType: isSse ? 'sse' : 'websocket', bytes, status: bytes <= maxBodyBytes ? 'stream-fixture' : 'omitted-byte-cap', ...(bytes <= maxBodyBytes ? parsed !== undefined ? { values: fixtureValues(parsed) } : { text: safeText(raw, maxBodyBytes) } : {}) });
          }
        }
      }
      cursor = Math.max(cursor, batch.cursor);
      if (!batch.hasMore) return { cursor, drained: true };
      if (cursor === previousCursor) { await gap('cursor-stalled'); return { cursor, drained: false }; }
    }
    await gap('drain-page-limit');
    return { cursor, drained: false };
  }

  async function snapshotCore(label) {
    const result = { capturedAt: iso() };
    try { result.url = safeUrl(await scope()); } catch { return { ...result, status: originPaused ? 'outside-origin' : 'origin-unavailable' }; }
    if (privateDom) {
      let dom;
      try { dom = await tab.playwright.domSnapshot(); }
      catch { result.domStatus = 'unavailable'; await gap('dom-snapshot-unavailable'); }
      try { await scope(); } catch { return { ...result, status: 'outside-origin' }; }
      if (typeof dom === 'string') {
        const credentialScreen = /password|access.?token|api.?key|secret|authorization|\bBearer\b/i.test(dom);
        const filename = `artifacts/${label}.dom.txt`;
        await durableFile(filename, safeText(dom, 1000000));
        result.dom = filename;
        if (privateScreenshots && !credentialScreen) {
          try {
            await scope();
            const pixels = await tab.screenshot({ fullPage: false });
            await scope();
            const file = `artifacts/${label}.png`;
            await durableFile(file, pixels); result.screenshot = file;
          } catch { result.screenshotStatus = originPaused ? 'outside-origin' : 'unavailable'; if (!originPaused) await gap('screenshot-unavailable'); }
        } else if (privateScreenshots) result.screenshotStatus = 'omitted-credential-screen';
      }
    } else result.domStatus = 'private-artifacts-disabled';
    return result;
  }

  async function closeWriters() {
    for (const writer of writers.values()) {
      try { await writer.sync(); } catch { cleanupFailures.push('journal-sync-failed'); }
      try { await writer.close(); } catch { cleanupFailures.push('journal-close-failed'); }
    }
    writers.clear();
  }
  async function disableOwnedDomains() {
    for (const domain of [...enabled].reverse()) {
      try { await cdp.send(`${domain}.disable`, {}, sendOptions); enabled.delete(domain); }
      catch { cleanupFailures.push(`${domain}-disable-failed`); if (writers.has('gaps.jsonl')) { try { await gap('domain-disable-failed', { method: `${domain}.disable` }); } catch { cleanupFailures.push('cleanup-gap-write-failed'); } } }
    }
  }
  function start() {
    if (startPromise || started || stopped) return Promise.reject(new Error('Capture already started or stopped'));
    startPromise = enqueue(async () => {
      try {
        await scope();
        if (domainsToEnable.length && !ownDomainLifecycle) throw new Error('Explicit ownDomainLifecycle required; existing domain state cannot be inferred');
        const root = await realpath(projectRoot);
        let parent = root;
        for (const segment of ['output', outputName]) { const next = path.join(parent, segment); await mkdir(next, { mode: 0o700 }).catch(error => { if (error.code !== 'EEXIST') throw error; }); parent = await realpath(next); if (!inside(root, parent)) throw new Error('Output symlink escapes project'); }
        directory = path.join(parent, runId);
        await mkdir(directory, { mode: 0o700 });
        await mkdir(path.join(directory, 'artifacts'), { mode: 0o700 });
        for (const file of JOURNALS) { const writer = await open(path.join(directory, file), 'wx', 0o600); writers.set(file, writer); await writer.sync(); }
        // Baseline drops historical buffered events, then every action starts at an explicit cursor.
        for (let page = 0; page < maxDrainPages; page++) {
          await scope();
          const batch = await cdp.readEvents({ ...(cursor !== undefined ? { afterSequence: cursor } : {}), limit: 1000, methods: [...METHODS], ...(target ? { target } : {}), timeoutMs: eventTimeoutMs });
          await scope();
          if (!Number.isInteger(batch?.cursor)) throw new Error('Initial event cursor unavailable');
          if (batch.truncated) await gap('baseline-buffer-truncated', { nextCursor: batch.cursor });
          if (cursor !== undefined && batch.cursor <= cursor && batch.hasMore) throw new Error('Baseline cursor stalled');
          cursor = batch.cursor;
          if (!batch.hasMore) break;
          if (page === maxDrainPages - 1) throw new Error('Baseline drain exceeded page limit');
        }
        started = true;
        for (const domain of [...new Set(domainsToEnable)]) {
          try { await cdp.send(`${domain}.enable`, domain === 'Network' ? { maxTotalBufferSize: networkBufferBytes, maxResourceBufferSize: resourceBufferBytes, maxPostDataSize: maxBodyBytes } : {}, sendOptions); enabled.add(domain); }
          catch { unsupported.push(`${domain}.enable`); await gap('domain-enable-unsupported', { method: `${domain}.enable` }); }
        }
        await journal('actions.jsonl', 'capture_started', { cursor, origin: allowedOrigin, fixtureBodyValues, deliveredSourceText, privateDom, privateScreenshots, enabledDomains: [...enabled], eventTimeoutMs, networkBufferBytes, resourceBufferBytes });
        return status();
      } catch (error) {
        cancelTimer();
        await disableOwnedDomains();
        await closeWriters();
        stopped = true;
        // Our validation errors are static. Never surface bridge messages with browser payloads.
        if (error instanceof Error && /^(Capture |Explicit |Output |Baseline |Initial |EEXIST:)/.test(error.message)) throw error;
        throw new Error('Capture initialization failed; writers closed and owned domains released');
      }
    });
    return startPromise;
  }
  function drain() { assertAccepting(); return enqueue(drainCore); }
  function schedulePoll() {
    if (!polling.active || stopping || stopped || originPaused) return;
    timer = setTimeout(() => {
      timer = undefined;
      if (!polling.active || stopping || stopped || originPaused) return;
      enqueue(async () => {
        if (!polling.active || stopping || stopped || originPaused) return;
        polling.ticks++;
        try {
          const result = await drainCore();
          if (!result.drained) {
            cancelTimer(); polling.pauseReason = result.paused ? 'origin-changed' : result.reason || 'drain-failed';
            if (!result.paused) await gap('polling-paused-drain-failure', { cause: result.reason || 'drain-failed' });
          }
        } catch {
          cancelTimer(); polling.pauseReason = 'poll-failed';
          try { await gap('polling-paused-exception'); } catch { cleanupFailures.push('poll-gap-write-failed'); }
        }
      }).then(schedulePoll, () => { cancelTimer(); polling.pauseReason = 'queue-failed'; });
    }, polling.intervalMs);
  }
  function startPolling({ intervalMs = 1000 } = {}) {
    assertAccepting();
    if (!Number.isInteger(intervalMs) || intervalMs < 100 || intervalMs > 10000) throw new Error('intervalMs must be 100..10000');
    return enqueue(async () => {
      await scope();
      if (polling.active) throw new Error('Polling is already active');
      polling.active = true; polling.everStarted = true; polling.intervalMs = intervalMs; polling.pauseReason = null;
      try { await journal('actions.jsonl', 'polling_started', { cursor, intervalMs }); schedulePoll(); return status(); }
      catch { cancelTimer(); throw new Error('Polling could not start; journal write failed'); }
    });
  }
  function stopPolling() {
    assertAccepting();
    cancelTimer(); // Cancel now, then wait for queued/in-flight drain and journal work.
    return enqueue(async () => { cancelTimer(); await journal('actions.jsonl', 'polling_stopped', { cursor, ticks: polling.ticks }); return status(); });
  }
  function mark({ stepId, workflowId, note } = {}) {
    assertAccepting();
    if (!safeId(stepId) || !safeId(workflowId)) throw new Error('Safe stepId/workflowId required');
    return enqueue(async () => { await scope(); await drainCore(); await journal('actions.jsonl', 'mark', { stepId, workflowId, note: safeText(note), cursor }); return status(); });
  }
  function snapshotNow({ label, stepId, workflowId } = {}) {
    assertAccepting();
    if (!safeId(label) || (stepId !== undefined && !safeId(stepId)) || (workflowId !== undefined && !safeId(workflowId))) throw new Error('Safe snapshot label and optional IDs required');
    return enqueue(async () => {
      await scope();
      if (artifactLabels.has(label)) throw new Error('Snapshot labels must be unique');
      artifactLabels.add(label);
      await drainCore(); const cursorBefore = cursor;
      const snapshot = await snapshotCore(label);
      await drainCore();
      await journal('actions.jsonl', 'snapshot', { label, stepId, workflowId, cursorBefore, cursorAfter: cursor, snapshot });
      return snapshot;
    });
  }

  function step({ workflowId, stepId, intent, action, visibleEffect, acknowledgement = 'not-evaluated' }) {
    assertAccepting();
    if (busy) return Promise.reject(new Error('Concurrent UI actions are not supported'));
    if (typeof action !== 'function') return Promise.reject(new Error('One action callback required'));
    const id = stepId || `step-${++stepNumber}`;
    if (!safeId(id) || !safeId(workflowId)) return Promise.reject(new Error('Safe stepId/workflowId required'));
    if (stepIds.has(id)) return Promise.reject(new Error('Step IDs must be unique; use a new step ID for an independently reviewed action'));
    if (artifactLabels.has(`${id}-before`) || artifactLabels.has(`${id}-after`)) return Promise.reject(new Error('Step artifact labels already used'));
    busy = true; stepIds.add(id); artifactLabels.add(`${id}-before`); artifactLabels.add(`${id}-after`);
    const work = (async () => {
      let result, failed = false, before, after, cursorBefore;
      try {
        await enqueue(async () => {
          await scope(); await drainCore(); before = await snapshotCore(`${id}-before`); await drainCore(); cursorBefore = cursor;
          await journal('actions.jsonl', 'step_begin', { stepId: id, workflowId, intent: safeText(intent), cursorBefore, before });
        });
        // Do not hold the evidence queue during UI/generation waits: background drains can continue.
        try { result = await action(); } catch { failed = true; }
        await enqueue(async () => {
          try { await drainCore(); } catch { await gap('post-action-drain-failed'); }
          try { after = await snapshotCore(`${id}-after`); } catch { after = { status: 'unavailable' }; await gap('post-action-snapshot-failed'); }
          try { await drainCore(); } catch { await gap('final-step-drain-failed'); }
          await journal('actions.jsonl', 'step_end', { stepId: id, workflowId, cursorBefore, cursorAfter: cursor, before, after, status: failed ? 'failed' : 'completed', visibleEffect: safeText(visibleEffect), acknowledgement: ['observed', 'not-observed', 'not-evaluated'].includes(acknowledgement) ? acknowledgement : 'not-evaluated', visibleEffectVerified: false });
        });
        if (failed) throw new Error(`Action failed in ${id}; failure recorded and events drained`);
        return result;
      } finally { busy = false; }
    })();
    activeStep = work;
    work.then(() => { if (activeStep === work) activeStep = undefined; }, () => { if (activeStep === work) activeStep = undefined; });
    return work;
  }

  async function manifest() {
    const files = [];
    for (const file of JOURNALS.concat((await readdir(path.join(directory, 'artifacts'))).map(name => `artifacts/${name}`))) {
      const bytes = await readFile(path.join(directory, file));
      files.push({ path: file, bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') });
    }
    const data = { schemaVersion: 1, runId, finalizedAt: iso(), files, cursor, counts, unsupported, cleanupFailures, recording: { mode: polling.everStarted ? 'polling' : 'bounded-drain', methods: METHODS, fixtureBodyValues, deliveredSourceText, privateDom, privateScreenshots, polling: { ...polling }, eventTimeoutMs, networkBufferBytes, resourceBufferBytes, journalDurability: 'FileHandle.write+sync before acknowledgement' }, limitations: ['Polling requires a persistent Node/browser runtime; tool-session disconnection can interrupt collection.', 'No unattended-across-turn or disconnect-survival guarantee.', 'CDP retention can evict events and response bodies before a drain.', 'HTTP acknowledgement and visible state are distinct; timing alone does not prove causality.', 'Cross-origin bodies, auth state, storage, headers and raw console values are omitted.', 'Private images require operator preinspection; text redaction is best effort.', 'Fetch streaming response chunk contents are not implemented; dataReceived records byte metadata only.'] };
    await durableFile('manifest.json', `${JSON.stringify(data, null, 2)}\n`);
    return data;
  }
  function stop() {
    if (stopPromise) return stopPromise;
    assertRunning();
    stopping = true; cancelTimer();
    stopPromise = (async () => {
      if (activeStep) { try { await activeStep; } catch { /* Step failure already journaled; stop still closes its writers. */ } }
      return enqueue(async () => {
        let failure;
        try {
          await drainCore();
          await disableOwnedDomains();
          await drainCore();
          await journal('actions.jsonl', 'capture_stopped', { cursor, originPaused });
        } catch { failure = true; cleanupFailures.push('stop-drain-or-write-failed'); }
        finally {
          cancelTimer();
          await disableOwnedDomains();
          await closeWriters();
          stopped = true;
        }
        try { await manifest(); } catch { cleanupFailures.push('manifest-write-failed'); throw new Error('Capture stopped and writers closed; manifest could not be sealed'); }
        if (failure) throw new Error('Capture stopped and sealed with cleanup failures; inspect safe manifest status');
        return status();
      });
    })();
    return stopPromise;
  }
  function status() { return { runId, directory, started, stopped, stopping, originPaused, cursor, counts: { ...counts }, unsupported: [...unsupported], cleanupFailures: [...cleanupFailures], enabledDomains: [...enabled], mode: polling.everStarted ? 'polling' : 'bounded-drain', polling: { ...polling }, writerCount: writers.size }; }
  return { start, startPolling, stopPolling, step, mark, snapshotNow, drain, stop, status };
}
