import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { randomUUID, createHash } from 'node:crypto';
import path from 'node:path';
import { createCapture } from './capture.mjs';
const ORIGIN = 'https://studio.symbolic.ai';
import { safeText, safeUrl, jsonShape, fixtureValues, eventMetadata } from './redaction.mjs';

const projectRoot = path.resolve(import.meta.dirname, '../..');
const event = (sequence, method, params, source = { sessionId: 'test-session' }) => ({ sequence, method, params, source });
async function mockRun(options = {}) {
  let url = `${options.allowedOrigin || ORIGIN}/monumental-stories`, sequence = 0;
  const queue = [], calls = [];
  const tab = { url: async () => url, playwright: { domSnapshot: async () => '- button "Fixture"' }, screenshot: async () => Buffer.from('mock screenshot') };
  const cdp = {
    send: async (method, params, sendOptions) => { calls.push({ method, params, options: sendOptions }); if (options.failEnable && method.endsWith('.enable')) throw new Error('secret unsafe'); if (method === 'Network.getResponseBody') { if (options.evicted) throw new Error('Bearer never-print-this'); return { body: JSON.stringify({ title: 'PRIVATE_STORY', token: 'PRIVATE_TOKEN', rows: [{ count: 4 }] }) }; } return {}; },
    readEvents: async () => queue.shift() || { cursor: sequence, events: [], hasMore: false, truncated: false },
  };
  const capture = createCapture({ tab, cdp, projectRoot, allowedOrigin: ORIGIN, runId: `test-${randomUUID()}`, ownDomainLifecycle: true, ...options });
  await capture.start();
  return { capture, calls, tab, cdp, setUrl: next => { url = next; }, enqueue: (events, extra = {}) => { sequence = Math.max(sequence, ...events.map(e => e.sequence)); queue.push({ cursor: sequence, events, hasMore: false, truncated: false, ...extra }); }, rows: async file => (await readFile(path.join(capture.status().directory, file), 'utf8')).trim().split('\n').filter(Boolean).map(JSON.parse) };
}

test('redaction omits signed query values, credentials, JWT, PEM and dynamic JSON keys', () => {
  const input = 'https://u:pass@studio.symbolic.ai/api?X-Amz-Signature=SECRETSIG&query=PRIVATE_QUERY#access_token=SECRET';
  const output = safeUrl(input);
  assert.ok(!/SECRETSIG|PRIVATE_QUERY|pass|access_token/.test(output));
  const text = safeText('Bearer MYTOKEN secret="secretvalue" token=shortvalue -----BEGIN PRIVATE KEY-----\nxyz\n-----END PRIVATE KEY----- eyJabc.abc.def someone@example.com');
  assert.ok(!/MYTOKEN|secretvalue|shortvalue|xyz|eyJabc|someone@/.test(text));
  const shape = JSON.stringify(jsonShape({ email: 'PRIVATE_EMAIL', 'PRIVATE_EMAIL@example.com': 'body', accessToken: 'PRIVATE_TOKEN' }));
  assert.ok(!/PRIVATE/.test(shape));
  assert.ok(!JSON.stringify(fixtureValues({ authorization: 'abc', content: 'Bearer DEF', pem: '-----BEGIN KEY-----abc-----END KEY-----' })).includes('abc'));
  assert.equal(safeUrl('data:text/plain,PRIVATE_DATA_URL_SENTINEL'), '[NON_NETWORK_URL]');
  assert.equal(safeUrl('blob:https://example.test/PRIVATE_BLOB_SENTINEL'), '[NON_NETWORK_URL]');
  const mixedToken = `0.032512336477671266:1790881533:${'Ab3_Cd4-Ef5.Gh6'.repeat(5)}`;
  assert.equal(safeUrl(`https://example.test/cdn-cgi/challenge-platform/${mixedToken}`), 'https://example.test/cdn-cgi/challenge-platform/[OPAQUE]');
  assert.equal(safeUrl('https://example.test/projects/alpha-1/assets/app.js'), 'https://example.test/projects/alpha-1/assets/app.js');
  const event = eventMetadata({ method: 'Network.requestWillBeSent', params: { request: { url: 'data:text/plain,PRIVATE_DATA_URL_SENTINEL', method: 'GET' } } });
  assert.doesNotMatch(JSON.stringify(event), /PRIVATE_DATA_URL_SENTINEL/);
});

test('start asserts fresh exact Symbolic origin, no navigation, and explicit domain ownership', async () => {
  const calls = [];
  const cdp = { send: async (...args) => calls.push(args), readEvents: async () => ({ cursor: 10, events: [], hasMore: false }) };
  const outside = createCapture({ tab: { url: async () => 'https://symbolic.ai' }, cdp, projectRoot, allowedOrigin: ORIGIN });
  await assert.rejects(outside.start(), /current tab/);
  const unowned = createCapture({ tab: { url: async () => ORIGIN }, cdp, projectRoot, allowedOrigin: ORIGIN });
  await assert.rejects(unowned.start(), /ownDomainLifecycle/);
  assert.equal(calls.length, 0);
});

test('pagination, redirect reuse, immediate bodies, default private suppression and sealed hashes', async () => {
  const run = await mockRun();
  run.enqueue([
    event(1, 'Network.requestWillBeSent', { requestId: 'repeat', request: { url: `${ORIGIN}/old?token=SECRET`, method: 'GET', headers: { Cookie: 'SECRET_COOKIE' } } }),
    event(2, 'Network.requestWillBeSent', { requestId: 'repeat', request: { url: `${ORIGIN}/api/fixture`, method: 'GET' }, redirectResponse: { url: `${ORIGIN}/old`, status: 302, headers: { Authorization: 'SECRET_AUTH' } } }),
    event(3, 'Network.responseReceived', { requestId: 'repeat', response: { url: `${ORIGIN}/api/fixture`, status: 200, mimeType: 'application/json' } }),
  ], { hasMore: true });
  run.enqueue([event(4, 'Network.loadingFinished', { requestId: 'repeat', encodedDataLength: 100 })]);
  const result = await run.capture.drain();
  assert.equal(result.cursor, 4);
  assert.equal(run.calls.filter(c => c.method === 'Network.getResponseBody').length, 1);
  const events = await run.rows('events.jsonl');
  assert.equal(events.length, 4);
  assert.equal(events.filter(r => r.event.method === 'Network.requestWillBeSent').length, 2);
  const bodies = await run.rows('bodies.jsonl');
  assert.equal(bodies[0].captureMode, 'shape');
  assert.equal(bodies[0].status, 'captured');
  await run.capture.stop();
  const manifest = JSON.parse(await readFile(path.join(run.capture.status().directory, 'manifest.json'), 'utf8'));
  for (const file of manifest.files) { const bytes = await readFile(path.join(run.capture.status().directory, file.path)); assert.equal(file.sha256, createHash('sha256').update(bytes).digest('hex')); assert.equal(file.bytes, bytes.length); assert.ok(!['SECRET_COOKIE', 'SECRET_AUTH', 'token=SECRET'].some(value => bytes.toString().includes(value))); assert.ok(!bytes.toString().includes('PRIVATE_STORY')); }
});

test('failure drains once, records safe failed result and never retries UI action', async () => {
  const run = await mockRun({ evicted: true });
  let attempts = 0;
  await assert.rejects(run.capture.step({ workflowId: 'fixture', intent: 'Test token=secret', action: async () => { attempts++; run.enqueue([event(1, 'Network.responseReceived', { requestId: 'r', response: { url: `${ORIGIN}/api`, mimeType: 'application/json' } }), event(2, 'Network.loadingFinished', { requestId: 'r', encodedDataLength: 100 })]); throw new Error('COOKIE_SECRET'); } }), /Action failed/);
  assert.equal(attempts, 1);
  const actions = await run.rows('actions.jsonl');
  assert.equal(actions.find(r => r.type === 'step_end').status, 'failed');
  assert.equal(actions.find(r => r.type === 'step_end').cursorAfter, 2);
  assert.ok(!JSON.stringify(actions).includes('COOKIE_SECRET'));
  assert.ok((await run.rows('gaps.jsonl')).some(r => r.reason === 'body-unavailable-or-evicted'));
  await run.capture.stop();
});

test('external, binary and oversized response bodies never requested', async () => {
  const run = await mockRun({ maxBodyBytes: 10 });
  run.enqueue([
    event(1, 'Network.responseReceived', { requestId: 'external', response: { url: 'https://external.example/api', mimeType: 'application/json' } }), event(2, 'Network.loadingFinished', { requestId: 'external', encodedDataLength: 1 }),
    event(3, 'Network.responseReceived', { requestId: 'binary', response: { url: `${ORIGIN}/image`, mimeType: 'image/png' } }), event(4, 'Network.loadingFinished', { requestId: 'binary', encodedDataLength: 1 }),
    event(5, 'Network.responseReceived', { requestId: 'large', response: { url: `${ORIGIN}/api`, mimeType: 'application/json' } }), event(6, 'Network.loadingFinished', { requestId: 'large', encodedDataLength: 100 }),
  ]);
  await run.capture.drain();
  assert.equal(run.calls.filter(c => c.method === 'Network.getResponseBody').length, 0);
  assert.equal((await run.rows('bodies.jsonl')).length, 3);
  await run.capture.stop();
});

test('truncation and unsupported domains are recorded; unowned domains are not disabled', async () => {
  const run = await mockRun({ failEnable: true });
  run.enqueue([event(7, 'Runtime.consoleAPICalled', { type: 'log', args: [{ type: 'string', value: 'PRIVATE_CONSOLE' }] })], { truncated: true });
  await run.capture.drain();
  await run.capture.stop();
  assert.ok((await run.rows('gaps.jsonl')).some(r => r.reason === 'event-buffer-truncated'));
  assert.equal(run.calls.filter(c => c.method.endsWith('.disable')).length, 0);
  assert.ok(!JSON.stringify(await run.rows('events.jsonl')).includes('PRIVATE_CONSOLE'));
});

test('safe output folder containment rejects an existing run id', async () => {
  const run = await mockRun();
  await run.capture.stop();
  const duplicate = createCapture({ tab: run.tab, cdp: run.cdp, projectRoot, allowedOrigin: ORIGIN, runId: run.capture.status().runId, domainsToEnable: [] });
  await assert.rejects(duplicate.start(), /EEXIST/);
});

test('fixture body opt-in preserves bounded synthetic values while deleting credential fields', async () => {
  const run = await mockRun({ fixtureBodyValues: true });
  run.enqueue([event(1, 'Network.responseReceived', { requestId: 'r', response: { url: `${ORIGIN}/api`, mimeType: 'application/json' } }), event(2, 'Network.loadingFinished', { requestId: 'r', encodedDataLength: 10 })]);
  await run.capture.drain();
  const serialized = JSON.stringify(await run.rows('bodies.jsonl'));
  assert.ok(serialized.includes('PRIVATE_STORY'));
  assert.ok(!serialized.includes('PRIVATE_TOKEN'));
  await run.capture.stop();
});

test('portable recorder accepts two declared origins and refuses an outside-origin action', async () => {
  for (const allowedOrigin of ['https://first.example.test', 'https://second.example.test']) {
    const run = await mockRun({ allowedOrigin });
    await run.capture.step({ workflowId: 'portable', intent: 'Observe synthetic site', action: async () => {} });
    run.setUrl('https://outside.example.test');
    let actions = 0;
    await assert.rejects(run.capture.step({ workflowId: 'portable', intent: 'Must refuse', action: async () => { actions++; } }), /allowedOrigin/);
    assert.equal(actions, 0);
    run.setUrl(allowedOrigin);
    await run.capture.stop();
  }
  assert.throws(() => createCapture({ allowedOrigin: 'http://example.test' }), /exact HTTPS/);
  assert.throws(() => createCapture({ allowedOrigin: 'https://example.test/path' }), /exact HTTPS/);
  assert.throws(() => createCapture({ allowedOrigin: 'https://example.test', outputName: '../escape' }), /outputName/);
});

test('numeric tab identity and every source component distinguish reused request ids', async () => {
  const run = await mockRun();
  const a = { sessionId: 's', targetId: 't', tabId: 10, extensionId: 'ext-a' };
  const b = { sessionId: 's', targetId: 't', tabId: 11, extensionId: 'ext-b' };
  run.enqueue([
    event(1, 'Network.responseReceived', { requestId: 'same', response: { url: `${ORIGIN}/api`, mimeType: 'application/json' } }, a),
    event(2, 'Network.responseReceived', { requestId: 'same', response: { url: `${ORIGIN}/api`, mimeType: 'application/json' } }, b),
    event(3, 'Network.loadingFinished', { requestId: 'same', encodedDataLength: 10 }, a),
    event(4, 'Network.loadingFinished', { requestId: 'same', encodedDataLength: 10 }, b),
  ]);
  await run.capture.drain();
  assert.deepEqual((await run.rows('bodies.jsonl')).map(row => row.source), [a, b]);
  assert.equal(run.calls.filter(c => c.method === 'Network.getResponseBody').length, 2);
  await run.capture.stop();
});

test('request structures, direct initiator location and response status omit values, stacks and headers', async () => {
  const run = await mockRun();
  run.enqueue([
    event(1, 'Network.requestWillBeSent', { requestId: 'r', request: { url: `${ORIGIN}/api`, method: 'POST', hasPostData: true, postData: JSON.stringify({ draft: 'PRIVATE_DRAFT', authorization: 'PRIVATE_AUTH', options: { rewrite: true } }) }, initiator: { url: `${ORIGIN}/bundle.js?token=PRIVATE_QUERY`, lineNumber: 20, columnNumber: 4, stack: { callFrames: [{ functionName: 'PRIVATE_STACK' }] } } }),
    event(2, 'Network.responseReceivedExtraInfo', { requestId: 'r', statusCode: 403, headers: { Cookie: 'PRIVATE_COOKIE' }, blockedCookies: [{ cookieLine: 'PRIVATE_COOKIE' }] }),
  ]);
  await run.capture.drain();
  const rows = await run.rows('events.jsonl');
  assert.equal(rows[0].event.params.requestBody.shape.fields.draft, 'string');
  assert.equal(rows[0].event.params.initiator.lineNumber, 20);
  assert.equal(rows[1].event.params.statusCode, 403);
  assert.ok(!JSON.stringify(rows).includes('PRIVATE_'));
  await run.capture.stop();
});

test('fresh current-origin check prevents retrieval after the tab leaves the declared origin', async () => {
  const run = await mockRun();
  run.enqueue([event(1, 'Network.responseReceived', { requestId: 'r', response: { url: `${ORIGIN}/api`, mimeType: 'application/json' } }), event(2, 'Network.loadingFinished', { requestId: 'r', encodedDataLength: 10 })]);
  run.setUrl('https://outside.example.test');
  await run.capture.drain();
  assert.equal(run.calls.filter(c => c.method === 'Network.getResponseBody').length, 0);
  assert.equal((await run.rows('bodies.jsonl')).length, 0);
  assert.equal((await run.rows('events.jsonl')).length, 0);
  assert.equal(run.capture.status().originPaused, true);
  assert.ok((await run.rows('gaps.jsonl')).some(row => row.reason === 'origin-changed'));
  await run.capture.stop();
});

test('duplicate step ids are refused before a second UI action', async () => {
  const run = await mockRun();
  let attempts = 0;
  const descriptor = { workflowId: 'fixture', stepId: 'unique', intent: 'Single action', action: async () => { attempts++; } };
  await run.capture.step(descriptor);
  await assert.rejects(run.capture.step(descriptor), /unique/);
  assert.equal(attempts, 1);
  await run.capture.stop();
});

const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function eventually(predicate) {
  const deadline = Date.now() + 3000;
  while (!predicate()) { if (Date.now() >= deadline) throw new Error('Mock condition did not become true'); await delay(5); }
}

test('background polling continues through a UI wait and serializes marks, snapshots and steps', async () => {
  const run = await mockRun();
  const entered = deferred(), release = deferred();
  await run.capture.startPolling({ intervalMs: 100 });
  const step = run.capture.step({ stepId: 'generation', workflowId: 'fixture', intent: 'Wait for synthetic generation', action: async () => { entered.resolve(); await release.promise; } });
  await entered.promise;
  await Promise.all([
    run.capture.mark({ stepId: 'generation', workflowId: 'fixture', note: 'Still waiting token=PRIVATE_TOKEN' }),
    run.capture.snapshotNow({ label: 'waiting', stepId: 'generation', workflowId: 'fixture' }),
    run.capture.drain(),
  ]);
  run.enqueue([event(1, 'Network.dataReceived', { requestId: 'stream', dataLength: 42, encodedDataLength: 42 }), event(2, 'Network.dataReceived', { requestId: 'stream', dataLength: 15, encodedDataLength: 15 })]);
  await eventually(() => run.capture.status().counts.events === 2 && run.capture.status().polling.ticks > 0);
  release.resolve(); await step; await run.capture.stop();
  const rows = await run.rows('events.jsonl');
  assert.deepEqual(rows.map(row => row.event.sequence), [1, 2]);
  const actions = await run.rows('actions.jsonl');
  assert.ok(actions.some(row => row.type === 'mark'));
  assert.ok(actions.some(row => row.type === 'snapshot'));
  assert.ok(actions.some(row => row.type === 'step_end'));
  assert.ok(!JSON.stringify(actions).includes('PRIVATE_TOKEN'));
  assert.equal(run.capture.status().writerCount, 0);
});

test('stop cancels future polls and waits an in-flight drain before closing and hashing journals', async () => {
  const run = await mockRun();
  const entered = deferred(), release = deferred();
  const originalRead = run.cdp.readEvents;
  let reads = 0, block = true;
  run.cdp.readEvents = async options => { reads++; assert.ok(options.timeoutMs <= 1000); if (block) { block = false; entered.resolve(); await release.promise; } return originalRead(options); };
  run.enqueue([event(1, 'Network.dataReceived', { requestId: 'r', dataLength: 12 })]);
  await run.capture.startPolling({ intervalMs: 100 });
  await entered.promise;
  let finished = false;
  const stop = run.capture.stop().then(value => { finished = true; return value; });
  await delay(10); assert.equal(finished, false);
  release.resolve(); await stop;
  assert.equal(run.capture.status().writerCount, 0);
  const manifest = JSON.parse(await readFile(path.join(run.capture.status().directory, 'manifest.json'), 'utf8'));
  assert.equal(manifest.recording.mode, 'polling');
  assert.match(manifest.recording.journalDurability, /sync/);
  for (const file of manifest.files) assert.equal(file.sha256, createHash('sha256').update(await readFile(path.join(run.capture.status().directory, file.path))).digest('hex'));
  const readCount = reads;
  await delay(150); assert.equal(reads, readCount);
  await assert.rejects(async () => run.capture.drain(), /not running/);
});

test('stop is a barrier for a pending UI action and step completion', async () => {
  const run = await mockRun();
  const entered = deferred(), release = deferred();
  const step = run.capture.step({ workflowId: 'fixture', action: async () => { entered.resolve(); await release.promise; } });
  await entered.promise;
  let finished = false;
  const stop = run.capture.stop().then(() => { finished = true; });
  await delay(10); assert.equal(finished, false);
  release.resolve(); await Promise.all([step, stop]);
  const actions = await run.rows('actions.jsonl');
  assert.ok(actions.findIndex(row => row.type === 'step_end') < actions.findIndex(row => row.type === 'capture_stopped'));
  assert.equal(run.capture.status().writerCount, 0);
});

test('poll bridge failure pauses once and cannot create a tight retry loop or leak its error', async () => {
  const run = await mockRun();
  let reads = 0;
  run.cdp.readEvents = async () => { reads++; throw new Error('authorization=PRIVATE_BRIDGE_TOKEN'); };
  await run.capture.startPolling({ intervalMs: 100 });
  await eventually(() => run.capture.status().polling.pauseReason === 'read-events-failed');
  await delay(200); assert.equal(reads, 1);
  assert.equal(run.capture.status().polling.active, false);
  assert.equal((await run.rows('gaps.jsonl')).filter(row => row.reason === 'polling-paused-drain-failure').length, 1);
  assert.ok(!JSON.stringify(await run.rows('gaps.jsonl')).includes('PRIVATE_BRIDGE_TOKEN'));
  await run.capture.stop(); assert.equal(run.capture.status().writerCount, 0);
});

test('origin hop during a poll discards returned events, pauses and prevents all subsequent bridge reads', async () => {
  const run = await mockRun();
  const originalRead = run.cdp.readEvents;
  let reads = 0;
  run.cdp.readEvents = async options => { reads++; const result = await originalRead(options); run.setUrl('https://outside.example.test?token=PRIVATE_HOP'); return result; };
  run.enqueue([event(1, 'Network.responseReceived', { requestId: 'r', response: { url: `${ORIGIN}/api`, mimeType: 'application/json' } }), event(2, 'Network.loadingFinished', { requestId: 'r', encodedDataLength: 10 })]);
  await run.capture.startPolling({ intervalMs: 100 });
  await eventually(() => run.capture.status().originPaused);
  await delay(150); assert.equal(reads, 1);
  assert.equal((await run.rows('events.jsonl')).length, 0);
  assert.equal((await run.rows('bodies.jsonl')).length, 0);
  assert.equal(run.calls.filter(call => call.method === 'Network.getResponseBody').length, 0);
  await run.capture.stop(); assert.equal(reads, 1);
  assert.ok(!JSON.stringify(await run.rows('gaps.jsonl')).includes('PRIVATE_HOP'));
});

test('stopPolling flushes before acknowledgement and journal records are readable before sealing', async () => {
  const run = await mockRun({ privateDom: true });
  await run.capture.startPolling({ intervalMs: 100 });
  await run.capture.mark({ stepId: 'home', workflowId: 'fixture', note: 'Synthetic checkpoint' });
  const snapshot = await run.capture.snapshotNow({ label: 'home' });
  assert.equal(await readFile(path.join(run.capture.status().directory, snapshot.dom), 'utf8'), '- button "Fixture"');
  assert.ok((await run.rows('actions.jsonl')).some(row => row.type === 'mark'));
  assert.ok((await run.rows('actions.jsonl')).some(row => row.type === 'snapshot'));
  await run.capture.stopPolling();
  assert.equal(run.capture.status().polling.active, false);
  assert.ok((await run.rows('actions.jsonl')).some(row => row.type === 'polling_stopped'));
  await run.capture.stop();
});

test('disable failure still closes journal handles and reports safe cleanup status', async () => {
  const run = await mockRun();
  const originalSend = run.cdp.send;
  run.cdp.send = async (method, params, options) => { if (method.endsWith('.disable')) throw new Error('COOKIE=PRIVATE_CLEANUP'); return originalSend(method, params, options); };
  await run.capture.stop();
  assert.equal(run.capture.status().writerCount, 0);
  assert.ok(run.capture.status().cleanupFailures.includes('Network-disable-failed'));
  assert.ok(!JSON.stringify(await run.rows('gaps.jsonl')).includes('PRIVATE_CLEANUP'));
});

test('Network retention limits are bounded and fixture websocket values require same-origin creation', async () => {
  const run = await mockRun({ fixtureBodyValues: true, maxBodyBytes: 100 });
  const enable = run.calls.find(call => call.method === 'Network.enable');
  assert.equal(enable.params.maxTotalBufferSize, 4194304);
  assert.ok(enable.params.maxResourceBufferSize <= 1048576);
  assert.equal(enable.params.maxPostDataSize, 100);
  run.enqueue([
    event(1, 'Network.webSocketCreated', { requestId: 'same', url: 'wss://studio.symbolic.ai/stream?token=PRIVATE_QUERY' }),
    event(2, 'Network.webSocketFrameReceived', { requestId: 'same', response: { opcode: 1, payloadData: '{"text":"FIXTURE","token":"PRIVATE_TOKEN"}' } }),
    event(3, 'Network.webSocketCreated', { requestId: 'other', url: 'wss://outside.example.test/stream' }),
    event(4, 'Network.webSocketFrameReceived', { requestId: 'other', response: { opcode: 1, payloadData: 'PRIVATE_OTHER' } }),
  ]);
  await run.capture.drain();
  const bodies = await run.rows('bodies.jsonl');
  assert.equal(bodies.length, 1);
  assert.equal(bodies[0].streamType, 'websocket');
  assert.ok(JSON.stringify(bodies).includes('FIXTURE'));
  assert.ok(!JSON.stringify(bodies).includes('PRIVATE_'));
  await run.capture.stop();
});

test('delivered JS source opt-in keeps sanitized same-origin JS while HTML and cross-origin contents remain omitted', async () => {
  const run = await mockRun({ deliveredSourceText: true });
  const originalSend = run.cdp.send;
  run.cdp.send = async (method, params, options) => method === 'Network.getResponseBody' ? { body: params.requestId === 'js' ? 'const token="PRIVATE_SOURCE"; export const fixture=1;' : '<html>PRIVATE_HTML</html>' } : originalSend(method, params, options);
  run.enqueue([
    event(1, 'Network.responseReceived', { requestId: 'js', response: { url: `${ORIGIN}/bundle.js`, mimeType: 'application/javascript' } }), event(2, 'Network.loadingFinished', { requestId: 'js', encodedDataLength: 20 }),
    event(3, 'Network.responseReceived', { requestId: 'html', response: { url: `${ORIGIN}/home`, mimeType: 'text/html' } }), event(4, 'Network.loadingFinished', { requestId: 'html', encodedDataLength: 20 }),
    event(5, 'Network.responseReceived', { requestId: 'external', response: { url: 'https://outside.example.test/bundle.js', mimeType: 'application/javascript' } }), event(6, 'Network.loadingFinished', { requestId: 'external', encodedDataLength: 20 }),
  ]);
  await run.capture.drain();
  const bodies = await run.rows('bodies.jsonl');
  assert.equal(bodies[0].captureMode, 'delivered-source');
  assert.ok(bodies[0].text.includes('fixture=1'));
  assert.equal(bodies[0].sourceAltered, true);
  assert.equal(bodies[1].text, undefined);
  assert.equal(bodies[2].status, 'omitted-scope-or-mime');
  assert.ok(!JSON.stringify(bodies).includes('PRIVATE_'));
  await run.capture.stop();
});

test('missing browser invocation context is recorded distinctly from actual origin movement', async () => {
  const run = await mockRun();
  const originalUrl = run.tab.url;
  let available = false, reads = 0;
  run.tab.url = async () => { if (!available) throw new Error('PRIVATE_TRANSPORT_CONTEXT'); return originalUrl(); };
  const originalRead = run.cdp.readEvents;
  run.cdp.readEvents = async options => { reads++; return originalRead(options); };
  // Start within available context, then model context loss before the timer fires.
  available = true; await run.capture.startPolling({ intervalMs: 100 }); available = false;
  await eventually(() => run.capture.status().polling.pauseReason === 'origin-check-unavailable');
  assert.equal(reads, 0);
  assert.equal(run.capture.status().originPaused, false);
  const first = await run.capture.drain();
  assert.equal(first.reason, 'origin-check-unavailable');
  const gaps = await run.rows('gaps.jsonl');
  assert.equal(gaps.filter(row => row.reason === 'origin-check-unavailable').length, 1);
  assert.ok(gaps.some(row => row.reason === 'polling-paused-drain-failure' && row.cause === 'origin-check-unavailable'));
  assert.ok(!JSON.stringify(gaps).includes('PRIVATE_TRANSPORT_CONTEXT'));
  available = true;
  assert.equal((await run.capture.drain()).drained, true);
  await run.capture.stop();
});

test('WebSocket frame response metadata does not invent an HTTP response or cache fields', () => {
  for (const method of ['Network.webSocketFrameReceived', 'Network.webSocketFrameSent']) {
    const metadata = eventMetadata(event(1, method, { requestId: 'ws', response: { opcode: 1, mask: false, payloadData: 'PRIVATE_FRAME' } }));
    assert.equal(metadata.params.response, undefined);
    assert.equal(metadata.params.redirectResponse, undefined);
    assert.equal(metadata.params.frame.opcode, 1);
    assert.equal(metadata.params.frame.mask, false);
    assert.equal(metadata.params.frame.payloadBytes, Buffer.byteLength('PRIVATE_FRAME'));
    assert.ok(!JSON.stringify(metadata).includes('PRIVATE_FRAME'));
    assert.ok(!JSON.stringify(metadata).includes('INVALID_URL'));
    assert.ok(!JSON.stringify(metadata).includes('fromDiskCache'));
  }
  const http = eventMetadata(event(2, 'Network.responseReceived', { requestId: 'http', response: { url: `${ORIGIN}/api`, status: 200, mimeType: 'application/json' } }));
  assert.equal(http.params.response.status, 200);
  assert.equal(http.params.frame, undefined);
});

test('default JS and CSS content policy avoids body calls while retaining observed encoded sizes and JSON shapes', async () => {
  const run = await mockRun();
  run.enqueue([
    event(1, 'Network.responseReceived', { requestId: 'js', response: { url: `${ORIGIN}/bundle.js`, mimeType: 'application/javascript' } }), event(2, 'Network.loadingFinished', { requestId: 'js', encodedDataLength: 1234 }),
    event(3, 'Network.responseReceived', { requestId: 'css', response: { url: `${ORIGIN}/app.css`, mimeType: 'text/css' } }), event(4, 'Network.loadingFinished', { requestId: 'css', encodedDataLength: 5678 }),
    event(5, 'Network.responseReceived', { requestId: 'json', response: { url: `${ORIGIN}/api`, mimeType: 'application/graphql-response+json' } }), event(6, 'Network.loadingFinished', { requestId: 'json', encodedDataLength: 20 }),
  ]);
  await run.capture.drain();
  const bodyCalls = run.calls.filter(call => call.method === 'Network.getResponseBody');
  assert.deepEqual(bodyCalls.map(call => call.params.requestId), ['json']);
  const bodies = await run.rows('bodies.jsonl');
  assert.equal(bodies[0].status, 'omitted-content-policy');
  assert.equal(bodies[0].encodedBytes, 1234);
  assert.equal(bodies[0].bytes, undefined);
  assert.equal(bodies[1].status, 'omitted-content-policy');
  assert.equal(bodies[1].encodedBytes, 5678);
  assert.equal(bodies[1].bytes, undefined);
  assert.equal(bodies[2].status, 'captured');
  assert.equal(bodies[2].shape.fields.title, 'string');
  await run.capture.stop();
});
