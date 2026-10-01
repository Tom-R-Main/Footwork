import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { createCapture, METHODS as captureMethods } from '../browser-inspection/capture.mjs';
import { createEventRing } from './event-ring.mjs';

const methods = ['Network.requestWillBeSent', 'Network.responseReceived', 'Network.loadingFinished', 'Runtime.exceptionThrown'];
const source = { sessionId: 'selected', targetId: 'tab-one' };
const put = (ring, method, params = {}, src = source) => ring.ingest({ method, params, source: src });

test('session scope, pagination and filtered cursor progression', async () => {
  const ring = createEventRing({ sessionId: 'selected', methods, maxEvents: 6 });
  assert.equal(put(ring, 'Network.requestWillBeSent', {}, { sessionId: 'other' }).accepted, false);
  assert.equal(put(ring, 'Page.frameNavigated').accepted, false);
  assert.equal((await ring.readEvents()).cursor, 0);
  put(ring, 'Network.requestWillBeSent', { requestId: 'r' });
  put(ring, 'Runtime.exceptionThrown', { exceptionDetails: { text: 'private' } });
  put(ring, 'Network.responseReceived', { requestId: 'r' });
  put(ring, 'Network.loadingFinished', { requestId: 'r' });
  const first = await ring.readEvents({ afterSequence: 0, methods: ['Network.requestWillBeSent', 'Network.responseReceived'], limit: 1, target: { sessionId: 'selected' } });
  assert.equal(first.cursor, 1);
  assert.equal(first.events.length, 1);
  assert.equal(first.hasMore, true);
  const second = await ring.readEvents({ afterSequence: first.cursor, methods: ['Network.requestWillBeSent', 'Network.responseReceived'] });
  assert.equal(second.cursor, 4);
  assert.equal(second.events.length, 1);
  assert.equal(second.hasMore, false);
  assert.deepEqual(ring.status().ignoredForeign, 1);
  assert.deepEqual(ring.status().ignoredMethod, 1);
  await assert.rejects(ring.readEvents({ afterSequence: 4, target: { sessionId: 'other' } }), /does not match/);
});

test('eviction and byte cap stay visible as truncation, including when no events remain', async () => {
  const ring = createEventRing({ sessionId: 'selected', methods, maxEvents: 2, maxEventBytes: 1024 });
  put(ring, 'Network.requestWillBeSent', { requestId: 'a' });
  put(ring, 'Network.responseReceived', { requestId: 'a' });
  put(ring, 'Network.loadingFinished', { requestId: 'a' });
  const first = await ring.readEvents({ afterSequence: 0 });
  assert.equal(first.truncated, true);
  assert.deepEqual(first.events.map(e => e.sequence), [2, 3]);
  assert.equal(ring.status().droppedEvicted, 1);
  const oversized = put(ring, 'Runtime.exceptionThrown', { payload: 'S'.repeat(2000) });
  assert.equal(oversized.reason, 'event-byte-cap');
  const second = await ring.readEvents({ afterSequence: 3 });
  assert.equal(second.truncated, true);
  assert.equal(second.cursor, 4);
  assert.deepEqual(second.events, []);
  assert.equal(ring.status().droppedOversize, 1);
});

test('disconnect lets buffered events drain once and then refuses false empty success', async () => {
  const ring = createEventRing({ sessionId: 'selected', methods });
  put(ring, 'Network.requestWillBeSent', { requestId: 'r' });
  ring.disconnect();
  const final = await ring.readEvents({ afterSequence: 0 });
  assert.equal(final.events.length, 1);
  assert.equal(final.cursor, 1);
  await assert.rejects(ring.readEvents({ afterSequence: 1 }), /disconnected/);
  await assert.rejects(ring.readEvents(), /disconnected/);
  assert.throws(() => put(ring, 'Network.loadingFinished'), /disconnected/);
});

test('incoming event object mutation cannot change buffered evidence', async () => {
  const ring = createEventRing({ sessionId: 'selected', methods });
  const params = { requestId: 'r' };
  put(ring, 'Network.requestWillBeSent', params);
  params.requestId = 'mutated';
  const result = await ring.readEvents({ afterSequence: 0 });
  assert.equal(result.events[0].params.requestId, 'r');
});

test('ring supplies the recorder bridge and preserves a sealed failed-load trace', async () => {
  const root = await mkdtemp(join(tmpdir(), 'footwork-ring-'));
  try {
    const ring = createEventRing({ sessionId: 'selected', methods: captureMethods });
    const capture = createCapture({
      tab: { url: async () => 'https://fixture.test/home' },
      cdp: { readEvents: ring.readEvents, send: async () => ({}) },
      projectRoot: root, allowedOrigin: 'https://fixture.test', outputName: 'inspection',
      runId: 'ring-integration', target: { sessionId: 'selected' }, domainsToEnable: [],
    });
    await capture.start();
    put(ring, 'Network.requestWillBeSent', { requestId: 'r', request: { method: 'GET', url: 'https://fixture.test/api?secret=DO_NOT_LOG' } });
    put(ring, 'Network.loadingFailed', { requestId: 'r' });
    await capture.drain();
    await capture.stop();
    const dir = join(root, 'output', 'inspection', 'ring-integration');
    const events = await readFile(join(dir, 'events.jsonl'), 'utf8');
    const manifest = JSON.parse(await readFile(join(dir, 'manifest.json'), 'utf8'));
    assert.equal(manifest.counts.events, 2);
    assert.equal(manifest.counts.gaps, 0);
    assert(!events.includes('DO_NOT_LOG'));
  } finally { await rm(root, { recursive: true, force: true }); }
});
