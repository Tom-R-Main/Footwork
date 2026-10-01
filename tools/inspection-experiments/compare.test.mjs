import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { createHash } from 'node:crypto';
import { profile, compareProfiles, compareRuns } from './compare.mjs';

const event = (method, sequence, params, source = { tabId: 1 }) => ({ event: { method, sequence, params, source } });
const empty = () => ({ events: [], actions: [], gaps: [], bodies: [] });
function step(journals, id, before, after) {
  journals.actions.push({ type: 'step_begin', workflowId: 'analyze', stepId: id, cursorBefore: before });
  journals.actions.push({ type: 'step_end', workflowId: 'analyze', stepId: id, cursorAfter: after, status: 'completed', acknowledgement: 'observed' });
}
function request(journals, { id, sequence, url, method = 'POST', shape = { type: 'object', fields: { draft: 'string' } }, status = 200, source = { tabId: 1 } }) {
  journals.events.push(event('Network.requestWillBeSent', sequence, { requestId: id, request: { method, url }, requestBody: { shape } }, source));
  journals.events.push(event('Network.responseReceived', sequence + 1, { requestId: id, response: { status } }, source));
  journals.events.push(event('Network.loadingFinished', sequence + 2, { requestId: id }, source));
}
async function sealed(root, name, journals) {
  const dir = join(root, name);
  await mkdir(dir);
  const files = [];
  for (const [kind, rows] of Object.entries(journals)) {
    const path = `${kind}.jsonl`;
    const content = rows.map(row => JSON.stringify(row)).join('\n') + (rows.length ? '\n' : '');
    await writeFile(join(dir, path), content);
    files.push({ path, bytes: Buffer.byteLength(content), sha256: createHash('sha256').update(content).digest('hex') });
  }
  await writeFile(join(dir, 'manifest.json'), JSON.stringify({ files }));
  return dir;
}

test('paired intervals preserve count changes, redirect hops and opaque endpoint identities', () => {
  const a = empty(), b = empty();
  step(a, 'upload', 0, 10); step(b, 'upload', 0, 12);
  request(a, { id: 'r', sequence: 1, url: 'https://example.test/private/123?secret=CONTROL' });
  request(b, { id: 'r', sequence: 1, url: 'https://example.test/private/123?secret=VARIANT' });
  request(b, { id: 'r2', sequence: 5, url: 'https://example.test/private/123?secret=VARIANT' });
  const report = compareProfiles(profile(a), profile(b));
  assert.equal(report.steps[0].comparison, 'paired-intervals');
  assert.equal(report.steps[0].endpoints.length, 1);
  assert.equal(report.steps[0].endpoints[0].control.hops, 1);
  assert.equal(report.steps[0].endpoints[0].variant.hops, 2);
  assert.equal(report.steps[0].endpoints[0].change, 'changed-observed-profile');
  assert(!JSON.stringify(report).includes('/private/123'));
  assert(!JSON.stringify(report).includes('CONTROL'));
  assert(!JSON.stringify(report).includes('VARIANT'));
  const redirect = empty(); step(redirect, 'redirect', 0, 10);
  redirect.events.push(event('Network.requestWillBeSent', 1, { requestId: 'r', request: { method: 'GET', url: 'https://example.test/a' } }));
  redirect.events.push(event('Network.requestWillBeSent', 2, { requestId: 'r', redirectResponse: { status: 302 }, request: { method: 'GET', url: 'https://example.test/b' } }));
  assert.equal(profile(redirect).requestHops, 2);
});

test('missing steps and capture gaps limit conclusions', () => {
  const a = empty(), b = empty();
  step(a, 'present', 0, 3);
  request(a, { id: 'r', sequence: 1, url: 'https://example.test/api' });
  b.gaps.push({ reason: 'event-buffer-truncated', cursor: 1 });
  const report = compareProfiles(profile(a), profile(b));
  assert.equal(report.steps[0].comparison, 'incomparable-missing-step');
  assert.equal(report.steps[0].quality, 'limited');
  assert.deepEqual(report.steps[0].endpoints, []);
  step(b, 'present', 0, 3);
  const limited = compareProfiles(profile(a), profile(b));
  assert.equal(limited.steps[0].comparison, 'paired-intervals');
  assert.equal(limited.steps[0].quality, 'limited');
});

test('new endpoint and changed request structure are reported without request values', () => {
  const a = empty(), b = empty();
  step(a, 'submit', 0, 5); step(b, 'submit', 0, 10);
  request(a, { id: 'old', sequence: 1, url: 'https://example.test/api/check', shape: { type: 'object', fields: { text: 'string' } } });
  request(b, { id: 'new', sequence: 1, url: 'https://example.test/api/check', shape: { type: 'object', fields: { text: 'string', mode: 'string' } } });
  request(b, { id: 'other', sequence: 5, url: 'https://example.test/api/review', shape: { type: 'object', fields: { text: 'string' } } });
  const endpoints = compareProfiles(profile(a), profile(b)).steps[0].endpoints;
  assert.equal(endpoints.length, 2);
  assert(endpoints.some(item => item.change === 'added-in-variant'));
  assert(endpoints.some(item => item.control && item.variant && JSON.stringify(item.control.requestShapes) !== JSON.stringify(item.variant.requestShapes)));
  assert(!JSON.stringify(endpoints).includes('/api/check'));
});

test('response shapes compare by run without exposing values or claiming step attribution', () => {
  const a = empty(), b = empty();
  a.bodies.push({ url: 'https://example.test/result?key=TOPSECRET', status: 'captured', shape: { type: 'object', fields: { answer: 'string' } }, values: { answer: 'TOPSECRET' } });
  b.bodies.push({ url: 'https://example.test/result?key=OTHERSECRET', status: 'captured', shape: { type: 'object', fields: { answer: 'number' } }, values: { answer: 'OTHERSECRET' } });
  const report = compareProfiles(profile(a), profile(b));
  assert.equal(report.responses[0].change, 'changed-observed-profile');
  assert(!JSON.stringify(report).includes('TOPSECRET'));
  assert(!JSON.stringify(report).includes('OTHERSECRET'));
});

test('sealed-run loader rejects tampering and accepts two distinct packets', async () => {
  const root = await mkdtemp(join(tmpdir(), 'inspection-experiment-'));
  try {
    const a = empty(), b = empty(); step(a, 'open', 0, 1); step(b, 'open', 0, 1);
    const control = await sealed(root, 'control', a), variant = await sealed(root, 'variant', b);
    assert.equal((await compareRuns(control, variant)).steps.length, 1);
    await assert.rejects(compareRuns(control, control), /different sealed runs/);
    await writeFile(join(variant, 'events.jsonl'), 'tampered\n');
    await assert.rejects(compareRuns(control, variant), /Refusing unverified run/);
  } finally { await rm(root, { recursive: true, force: true }); }
});
