import test from 'node:test';
import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import { mkdtemp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { createPlaywrightCdpBridge, writeEnvelopeArtifact } from './playwright-cdp-bridge.mjs';

const ORIGIN = 'https://example.test';
function mockPage(url = `${ORIGIN}/app`) {
  const page = new EventEmitter();
  const session = new EventEmitter();
  session.send = async () => ({});
  session.detach = async () => {};
  page.context = () => ({ newCDPSession: async () => session });
  page.url = () => url;
  page.locator = () => ({ ariaSnapshot: async () => '- heading "Demo"' });
  page.screenshot = async () => Buffer.from('pixels');
  return { page, session };
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
