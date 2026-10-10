import test from 'node:test';
import assert from 'node:assert/strict';
import { runInNewContext } from 'node:vm';
import { mkdtemp, mkdir, readFile, writeFile, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { createCapture } from '../browser-inspection/capture.mjs';
import { installStreamProbe, buildStreamProbeSource, writeStreamArtifact } from './stream-probe.mjs';

const encoder = new TextEncoder();
const waitFor = async predicate => {
  for (let i = 0; i < 100; i++) { if (predicate()) return; await new Promise(resolve => setTimeout(resolve, 5)); }
  throw new Error('Timed out waiting for stream observation');
};
function response(chunks, { type = 'text/event-stream', onCancel } = {}) {
  const body = new ReadableStream({
    start(controller) { for (const chunk of chunks) controller.enqueue(encoder.encode(chunk)); controller.close(); },
    cancel() { onCancel?.(); },
  });
  return new Response(body, { headers: { 'content-type': type } });
}

test('metadata-only clone leaves application response bytes intact', async () => {
  const original = 'data: SECRET_FIRST\n\ndata: SECRET_SECOND\n\n';
  const host = { location: { href: 'https://fixture.test/home' }, performance,
    fetch: async () => response(['data: SECRET_FIRST\n\n', 'data: SECRET_SECOND\n\n']) };
  const records = [];
  const probe = installStreamProbe(host, { allowedOrigin: 'https://fixture.test', emit: row => records.push(row) });
  const appResponse = await host.fetch('/stream');
  assert.equal(await appResponse.text(), original);
  await waitFor(() => records.length === 1);
  assert.equal(records[0].coverage, 'observed');
  assert.equal(records[0].contentTypeFamily, 'sse');
  assert.equal(records[0].chunkCount, 2);
  assert.equal(records[0].observedBytes, encoder.encode(original).byteLength);
  assert.equal(records[0].chunkTimesMs.length, 2);
  assert(!JSON.stringify(records).includes('SECRET'));
  await probe.stop();
});

test('cross-origin and ordinary JSON are not cloned or recorded', async () => {
  let clones = 0;
  const foreign = { url: 'https://other.test/stream', status: 200, headers: new Headers({ 'content-type': 'text/event-stream' }), clone() { clones++; throw new Error('Should not clone'); } };
  const host = { location: { href: 'https://fixture.test/home' }, performance,
    fetch: async input => String(input).includes('foreign') ? foreign : new Response('{"ok":true}', { headers: { 'content-type': 'application/json' } }) };
  const records = [];
  const probe = installStreamProbe(host, { allowedOrigin: 'https://fixture.test', emit: row => records.push(row) });
  await host.fetch('https://other.test/foreign');
  await host.fetch('/json');
  assert.equal(clones, 0);
  assert.deepEqual(records, []);
  await probe.stop();
});

test('caps stream observation and reports only bounded cadence', async () => {
  const host = { location: { href: 'https://fixture.test/home' }, performance,
    fetch: async () => response(['S1', 'S2', 'S3', 'S4'], { type: 'application/x-ndjson' }) };
  const records = [];
  const probe = installStreamProbe(host, { allowedOrigin: 'https://fixture.test', maxChunks: 2, emit: row => records.push(row) });
  const appResponse = await host.fetch('/stream');
  assert.equal(await appResponse.text(), 'S1S2S3S4');
  await waitFor(() => records.length === 1);
  assert.equal(records[0].coverage, 'capped');
  assert.equal(records[0].chunkCount, 2);
  assert.equal(records[0].chunkSizesBytes.length, 2);
  assert(!JSON.stringify(records).includes('S1'));
  await probe.stop();
});

test('fetch failure is unchanged and uninstall restores the original fetch', async () => {
  const error = new Error('SECRET_FAILURE');
  const original = async () => { throw error; };
  const host = { location: { href: 'https://fixture.test/home' }, performance, fetch: original };
  const records = [];
  const probe = installStreamProbe(host, { allowedOrigin: 'https://fixture.test', emit: row => records.push(row) });
  await assert.rejects(host.fetch('/stream'), caught => caught === error);
  assert.deepEqual(records, []);
  await probe.stop();
  assert.equal(host.fetch, original);
});

test('stop cancels a pending clone without waiting for the page to consume it', async () => {
  const host = { location: { href: 'https://fixture.test/home' }, performance,
    fetch: async () => new Response(new ReadableStream({ start(controller) { controller.enqueue(encoder.encode('data: SECRET\n\n')); } }), { headers: { 'content-type': 'text/event-stream' } }) };
  const records = [];
  const probe = installStreamProbe(host, { allowedOrigin: 'https://fixture.test', stopTimeoutMs: 100, emit: row => records.push(row) });
  await host.fetch('/hanging'); // The application deliberately never consumes the response.
  await waitFor(() => probe.status().active === 1);
  await probe.stop();
  assert.equal(probe.status().stopped, true);
  assert.equal(probe.status().active, 0);
  assert.equal(records[0].coverage, 'stopped');
  assert(!JSON.stringify(records).includes('SECRET'));
});

test('injectable source is idempotent and retains only bounded metadata records', async () => {
  const host = { location: { href: 'https://fixture.test/home' }, performance,
    fetch: async () => response(['data: SECRET\n\n']) };
  const context = { window: host, URL, Date, Reflect, Number, String, Set, Promise, Math, JSON, setTimeout, clearTimeout };
  const source = buildStreamProbeSource({ allowedOrigin: 'https://fixture.test', maxRecords: 1 });
  assert.equal(runInNewContext(source, context).installed, true);
  assert.equal(runInNewContext(source, context).alreadyInstalled, true);
  await (await host.fetch('/stream')).text();
  await waitFor(() => host.__footworkStreamProbe.stats().buffered === 1);
  const records = host.__footworkStreamProbe.drain();
  assert.equal(records.length, 1);
  assert(!JSON.stringify(records).includes('SECRET'));
  await host.__footworkStreamProbe.stop();
  assert.equal(runInNewContext(source, context).installed, true);
  await host.__footworkStreamProbe.stop();
});

test('artifact writer strips unknown payload fields and refuses a sealed run', async () => {
  const root = await mkdtemp(join(tmpdir(), 'stream-artifact-'));
  try {
    await mkdir(join(root, 'artifacts'));
    const record = { kind: 'fetch-stream-summary', requestOrdinal: 1, coverage: 'observed', contentTypeFamily: 'sse',
      chunkCount: 1, observedBytes: 8, chunkTimesMs: [4], chunkSizesBytes: [8], rawContent: 'SECRET_VALUE', url: 'https://fixture.test/SECRET_PATH' };
    const receipt = await writeStreamArtifact({ runDirectory: root, label: 'fixture', records: [record],
      probeStatus: { buffered: 0, dropped: 2, active: 0, intercepted: 3, stopped: true, privateValue: 'SECRET_STATUS' } });
    assert.equal(receipt.records, 1);
    assert.equal(receipt.statusIncluded, true);
    const saved = await readFile(join(root, receipt.path), 'utf8');
    assert(!saved.includes('SECRET'));
    const rows = saved.trim().split('\n').map(JSON.parse);
    assert.equal(rows[0].contentTypeFamily, 'sse');
    assert.equal(rows[1].kind, 'stream-probe-status');
    assert.equal(rows[1].dropped, 2);
    await writeFile(join(root, 'manifest.json'), '{}');
    await assert.rejects(writeStreamArtifact({ runDirectory: root, label: 'late', records: [record] }), /run is sealed/);
  } finally { await rm(root, { recursive: true, force: true }); }
});

test('stream metadata written before recorder stop is covered by the sealed manifest', async () => {
  const root = await mkdtemp(join(tmpdir(), 'stream-seal-'));
  try {
    const capture = createCapture({
      tab: { url: async () => 'https://fixture.test/home' },
      cdp: { send: async () => ({}), readEvents: async () => ({ cursor: 0, events: [], hasMore: false, truncated: false }) },
      projectRoot: root, allowedOrigin: 'https://fixture.test', outputName: 'inspection', runId: 'fixture', domainsToEnable: [],
    });
    await capture.start();
    const receipt = await writeStreamArtifact({ runDirectory: capture.status().directory, label: 'stream',
      records: [{ kind: 'fetch-stream-summary', coverage: 'observed', contentTypeFamily: 'sse', chunkCount: 1, observedBytes: 4 }] });
    await capture.stop();
    const manifest = JSON.parse(await readFile(join(capture.status().directory, 'manifest.json'), 'utf8'));
    assert(manifest.files.some(file => file.path === receipt.path && file.sha256 === receipt.sha256));
  } finally { await rm(root, { recursive: true, force: true }); }
});
