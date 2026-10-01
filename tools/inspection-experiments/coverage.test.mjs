import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { createHash } from 'node:crypto';
import { auditCoverage, auditSealedRun } from './coverage.mjs';

const event = (method, sequence, params = {}, source = { tabId: 1 }) => ({ event: { method, sequence, params, source } });
const empty = () => ({ events: [], actions: [], gaps: [], bodies: [] });
async function sealed(root, journals) {
  const dir = join(root, 'packet');
  await mkdir(dir);
  const files = [];
  for (const [kind, rows] of Object.entries(journals)) {
    const path = `${kind}.jsonl`;
    const content = rows.map(row => JSON.stringify(row)).join('\n') + (rows.length ? '\n' : '');
    await writeFile(join(dir, path), content);
    files.push({ path, bytes: Buffer.byteLength(content), sha256: createHash('sha256').update(content).digest('hex') });
  }
  await writeFile(join(dir, 'manifest.json'), JSON.stringify({ files, recording: { mode: 'polling', methods: ['Network.requestWillBeSent'], polling: { ticks: 2 } } }));
  return dir;
}

test('redirect reuse, source identity and optional extra info remain distinct', () => {
  const rows = empty();
  rows.events.push(
    event('Network.requestWillBeSentExtraInfo', 1, { requestId: 'r', headers: { Cookie: 'SECRET' } }),
    event('Network.requestWillBeSent', 2, { requestId: 'r', request: { url: 'https://example.test/SECRET' } }),
    event('Network.requestWillBeSent', 3, { requestId: 'r', redirectResponse: { status: 302 }, request: { url: 'https://example.test/next' } }),
    event('Network.responseReceived', 4, { requestId: 'r', response: { status: 200 } }),
    event('Network.loadingFinished', 5, { requestId: 'r' }),
    event('Network.requestWillBeSent', 6, { requestId: 'r', request: { url: 'https://example.test/worker' } }, { tabId: 1, sessionId: 'worker' }),
  );
  const report = auditCoverage(rows, { recording: { methods: ['Network.requestWillBeSent', 'Network.responseReceivedExtraInfo'] } });
  assert.equal(report.networkLifecycle.requestHops, 3);
  assert.equal(report.networkLifecycle.redirects, 1);
  assert.equal(report.networkLifecycle.terminalWithoutResponse, 0);
  assert.equal(report.capture.sourceIdentities, 2);
  assert.equal(report.protocols['Network.responseReceivedExtraInfo'].observed, 0);
  assert.equal(report.assessment, 'no-reported-capture-gaps');
  assert(!JSON.stringify(report).includes('SECRET'));
});

test('orphan events, missing response and explicit gaps limit a step without claiming product failure', () => {
  const rows = empty();
  rows.events.push(
    event('Network.responseReceived', 1, { requestId: 'orphan' }),
    event('Network.loadingFinished', 2, { requestId: 'orphan' }),
    event('Network.requestWillBeSent', 3, { requestId: 'x' }),
    event('Network.loadingFinished', 4, { requestId: 'x' }),
    event('Network.dataReceived', 5, { requestId: 'unseen' }),
  );
  rows.actions.push({ type: 'step_begin', workflowId: 'test', stepId: '1', cursorBefore: 2 }, { type: 'step_end', workflowId: 'test', stepId: '1', cursorAfter: 5, status: 'completed' });
  rows.gaps.push({ reason: 'event-buffer-truncated', cursor: 3 }, { reason: 'SECRET', cursor: null });
  rows.bodies.push({ status: 'omitted-content-policy', values: 'SECRET' });
  const report = auditCoverage(rows);
  assert.equal(report.networkLifecycle.orphanResponses, 1);
  assert.equal(report.networkLifecycle.orphanTerminals, 1);
  assert.equal(report.networkLifecycle.orphanDataEvents, 1);
  assert.equal(report.networkLifecycle.terminalWithoutResponse, 1);
  assert.equal(report.capture.gapReasons.other, 1);
  assert.equal(report.steps[0].coverage, 'limited');
  assert.equal(report.steps[0].status, 'action-callback-completed');
  assert.equal(report.bodyPolicy.statuses['omitted-content-policy'], 1);
  assert(!JSON.stringify(report).includes('SECRET'));
});

test('protocol absence is unobserved, not unsupported', () => {
  const report = auditCoverage(empty(), { recording: { methods: ['Network.eventSourceMessageReceived', 'Network.webSocketFrameReceived'] } });
  assert.deepEqual(report.protocols['Network.eventSourceMessageReceived'], { subscribed: true, observed: 0 });
  assert.deepEqual(report.protocols['Network.webSocketFrameReceived'], { subscribed: true, observed: 0 });
  assert.equal(report.assessment, 'no-reported-capture-gaps');
});

test('sealed packet is verified before coverage and tampering is rejected', async () => {
  const root = await mkdtemp(join(tmpdir(), 'coverage-'));
  try {
    const rows = empty();
    rows.gaps.push({ reason: 'read-events-failed', cursor: 4 });
    const dir = await sealed(root, rows);
    const report = await auditSealedRun(dir);
    assert.equal(report.manifestIntegrity, 'hashes-verified');
    assert.equal(report.capture.reportedGaps, 1);
    assert.equal(report.capture.pollingTicks, 2);
    await writeFile(join(dir, 'gaps.jsonl'), 'tampered\n');
    await assert.rejects(auditSealedRun(dir), /Refusing unverified run/);
  } finally { await rm(root, { recursive: true, force: true }); }
});
