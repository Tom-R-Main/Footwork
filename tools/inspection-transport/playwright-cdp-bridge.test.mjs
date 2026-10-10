import test from 'node:test';
import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import { mkdtemp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { createPlaywrightCdpBridge, writeColdEntryArtifact, writeEnvelopeArtifact } from './playwright-cdp-bridge.mjs';

const ORIGIN = 'https://example.test';
function mockPage(url = `${ORIGIN}/app`) {
  const page = new EventEmitter();
  const session = new EventEmitter();
  session.send = async method => method === 'Page.getFrameTree' ? { frameTree: { frame: { id: 'main-frame' } } } : {};
  session.detach = async () => {};
  const context = new EventEmitter();
  context.newCDPSession = async () => session;
  context.serviceWorkers = () => [];
  page.context = () => context;
  let currentUrl = url;
  page.url = () => currentUrl;
  page.setUrl = value => { currentUrl = value; };
  page.frames = () => [{}];
  page.workers = () => [];
  page.locator = () => ({ ariaSnapshot: async () => '- heading "Demo"' });
  page.screenshot = async () => Buffer.from('pixels');
  return { page, session, context };
}

test('real-session bridge accepts one target and records only bounded operation/frame metadata', async () => {
  const { page, session } = mockPage();
  const bridge = await createPlaywrightCdpBridge({ page, allowedOrigin: ORIGIN, graphqlPath: '/graphql', allowedOperations: ['DemoQuery'], allowedEvents: ['safe_event'] });
  const start = await bridge.cdp.readEvents({ methods: ['Network.requestWillBeSent'] });
  session.emit('Network.requestWillBeSent', { timestamp: 1, request: { url: `${ORIGIN}/graphql?private=SECRET_URL`, method: 'POST', postData: JSON.stringify({ operationName: 'DemoQuery', query: 'query DemoQuery { viewer }', variables: { secret: 'SECRET_VARIABLE' } }) } });
  session.emit('Network.webSocketFrameReceived', { timestamp: 2, response: { opcode: 1, payloadData: JSON.stringify([null, null, 'room:SECRET_TOPIC', 'safe_event', { private: 'SECRET_FRAME' }]) } });
  const events = await bridge.cdp.readEvents({ afterSequence: start.cursor, methods: ['Network.requestWillBeSent', 'Network.webSocketFrameReceived'] });
  assert.equal(events.events.length, 2);
  const metadata = bridge.metadata();
  assert.equal(metadata.records.length, 2);
  assert.equal(metadata.records[0].operations[0].name, 'DemoQuery');
  assert.equal(metadata.records[1].eventName, 'safe_event');
  assert.doesNotMatch(JSON.stringify(metadata.records), /SECRET_URL|SECRET_VARIABLE|SECRET_TOPIC|SECRET_FRAME/);
  await bridge.close();
  assert.equal(bridge.metadata().ring.disconnected, true);
});

test('bridge fences origin and artifact writer refuses sealed runs', async () => {
  const { page } = mockPage('https://other.test/app');
  await assert.rejects(createPlaywrightCdpBridge({ page, allowedOrigin: ORIGIN }), /allowed HTTPS origin/);
  const same = mockPage();
  const bridge = await createPlaywrightCdpBridge({ page: same.page, allowedOrigin: ORIGIN });
  const runDirectory = await mkdtemp(path.join(os.tmpdir(), 'footwork-bridge-'));
  try {
    await mkdir(path.join(runDirectory, 'artifacts'));
    const result = await writeEnvelopeArtifact({ runDirectory, bridge });
    assert.equal(result.count, 0);
    const saved = JSON.parse(await readFile(result.path, 'utf8'));
    assert.equal(saved.coverage.pageTargetOnly, true);
    await writeFile(path.join(runDirectory, 'manifest.json'), '{}');
    await assert.rejects(writeEnvelopeArtifact({ runDirectory, bridge, label: 'after-seal' }), /sealed/);
  } finally { await bridge.close(); await rm(runDirectory, { recursive: true, force: true }); }
});

test('cold entry writes sanitized first-document evidence only after origin verification', async () => {
  const { page, session, context } = mockPage('about:blank');
  const bridge = await createPlaywrightCdpBridge({ page, allowedOrigin: ORIGIN, preNavigation: true });
  const runDirectory = await mkdtemp(path.join(os.tmpdir(), 'footwork-cold-entry-'));
  try {
    await mkdir(path.join(runDirectory, 'artifacts'));
    await assert.rejects(writeColdEntryArtifact({ runDirectory, bridge }), /Verified cold entry unavailable/);
    session.emit('Network.requestWillBeSent', { requestId: 'doc', frameId: 'main-frame', type: 'Document', timestamp: 1,
      request: { method: 'GET', url: `${ORIGIN}/entry?private=SECRET_QUERY` } });
    session.emit('Network.responseReceived', { requestId: 'doc', timestamp: 2, type: 'Document', response: { url: `${ORIGIN}/entry?private=SECRET_QUERY`, status: 200, mimeType: 'text/html' } });
    session.emit('Network.requestWillBeSent', { requestId: 'external', timestamp: 3, type: 'Image',
      request: { method: 'GET', url: 'https://other.test/SECRET_EXTERNAL' } });
    page.emit('frameattached'); page.emit('worker'); context.emit('serviceworker');
    page.setUrl(`${ORIGIN}/entry`);
    assert.deepEqual(await bridge.verifyColdEntry(), { verified: true, mainDocumentRequests: 1, eventCount: 3 });
    const result = await writeColdEntryArtifact({ runDirectory, bridge });
    const saved = await readFile(result.path, 'utf8');
    assert.equal(result.eventCount, 2);
    assert.equal(JSON.parse(saved).coverage.observedTargets.dedicatedWorker, 1);
    assert.equal(JSON.parse(saved).coverage.workerAndOutOfProcessFrameTraffic, 'unattached');
    assert.equal(JSON.parse(saved).coverage.excludedEvents, 1);
    assert(!saved.includes('SECRET_QUERY'));
    assert(!saved.includes('SECRET_EXTERNAL'));
    await writeFile(path.join(runDirectory, 'manifest.json'), '{}');
    await assert.rejects(writeColdEntryArtifact({ runDirectory, bridge, label: 'late' }), /sealed/);
  } finally { await bridge.close(); await rm(runDirectory, { recursive: true, force: true }); }
});

test('cold entry refuses a foreign main document or truncated buffer', async () => {
  const foreign = mockPage('about:blank');
  const bridge = await createPlaywrightCdpBridge({ page: foreign.page, allowedOrigin: ORIGIN, preNavigation: true });
  try {
    foreign.session.emit('Network.requestWillBeSent', { requestId: 'doc', frameId: 'main-frame', type: 'Document',
      request: { method: 'GET', url: 'https://other.test/private' } });
    foreign.page.setUrl(`${ORIGIN}/entry`);
    await assert.rejects(bridge.verifyColdEntry(), /did not stay on the allowed origin/);
  } finally { await bridge.close(); }
  const truncated = mockPage('about:blank');
  const shortBridge = await createPlaywrightCdpBridge({ page: truncated.page, allowedOrigin: ORIGIN, preNavigation: true, maxEvents: 1 });
  try {
    truncated.session.emit('Network.requestWillBeSent', { requestId: 'doc', frameId: 'main-frame', type: 'Document',
      request: { method: 'GET', url: `${ORIGIN}/entry` } });
    truncated.session.emit('Network.responseReceived', { requestId: 'doc', response: { url: `${ORIGIN}/entry`, status: 200 } });
    truncated.page.setUrl(`${ORIGIN}/entry`);
    await assert.rejects(shortBridge.verifyColdEntry(), /buffer is incomplete/);
  } finally { await shortBridge.close(); }
});
