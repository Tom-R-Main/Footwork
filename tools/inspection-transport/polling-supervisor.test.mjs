import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { createCapture, METHODS } from '../browser-inspection/capture.mjs';
import { createEventRing } from './event-ring.mjs';
import { createPollingSupervisor } from './polling-supervisor.mjs';

const ORIGIN = 'https://example.test';
function fixture() {
  const state = { started: true, stopping: false, stopped: false, originPaused: false,
    polling: { active: false, everStarted: true, pauseReason: 'origin-check-unavailable' } };
  const calls = { start: 0 };
  const capture = { status: () => ({ ...state, polling: { ...state.polling } }),
    startPolling: async () => { calls.start++; state.polling.active = true; state.polling.pauseReason = null; } };
  return { state, calls, capture };
}

test('transient URL failure resumes once only after exact-origin recovery', async () => {
  const f = fixture();
  let available = false;
  const tab = { url: async () => { if (!available) throw new Error('PRIVATE_URL'); return `${ORIGIN}/app`; } };
  const supervisor = createPollingSupervisor({ capture: f.capture, tab, allowedOrigin: ORIGIN, retryMs: 10000 });
  try {
    const first = await supervisor.start();
    assert.equal(first.originUnavailable, 1); assert.equal(f.calls.start, 0);
    available = true;
    await Promise.all([supervisor.recoverOnce(), supervisor.recoverOnce()]);
    assert.equal(f.calls.start, 1);
    assert.equal(supervisor.status().resumed, 1);
    assert(!JSON.stringify(supervisor.status()).includes('PRIVATE_URL'));
  } finally { await supervisor.stop(); }
  assert.equal(f.state.polling.active, true, 'the recorder owner controls its shutdown');
});

test('foreign origin and sealed run never resume', async () => {
  const f = fixture();
  let url = 'https://other.test/private';
  const supervisor = createPollingSupervisor({ capture: f.capture, tab: { url: async () => url }, allowedOrigin: ORIGIN, retryMs: 10000 });
  try {
    const first = await supervisor.start();
    assert.equal(first.foreignOrigin, 1); assert.equal(f.calls.start, 0);
    url = `${ORIGIN}/app`; f.state.stopped = true;
    await supervisor.recoverOnce();
    assert.equal(f.calls.start, 0);
  } finally { await supervisor.stop(); }
});

test('stop during in-flight origin check cannot restart polling', async () => {
  const f = fixture();
  let release;
  const tab = { url: () => new Promise(resolve => { release = resolve; }) };
  const supervisor = createPollingSupervisor({ capture: f.capture, tab, allowedOrigin: ORIGIN, retryMs: 10000 });
  const starting = supervisor.start();
  await Promise.resolve();
  const stopping = supervisor.stop();
  release(`${ORIGIN}/app`);
  await Promise.all([starting, stopping]);
  assert.equal(f.calls.start, 0);
});

test('never-started and differently paused capture cannot be started', async () => {
  const f = fixture();
  const supervisor = createPollingSupervisor({ capture: f.capture,
    tab: { url: async () => `${ORIGIN}/app` }, allowedOrigin: ORIGIN, retryMs: 10000 });
  try {
    f.state.polling.everStarted = false;
    await supervisor.start();
    assert.equal(f.calls.start, 0);
    f.state.polling.everStarted = true;
    f.state.polling.pauseReason = 'poll-failed';
    await supervisor.recoverOnce();
    assert.equal(f.calls.start, 0);
  } finally { await supervisor.stop(); }
});

test('state change while URL is checked prevents a stale recovery attempt', async () => {
  const f = fixture();
  let release;
  const supervisor = createPollingSupervisor({ capture: f.capture,
    tab: { url: () => new Promise(resolve => { release = resolve; }) }, allowedOrigin: ORIGIN, retryMs: 10000 });
  const starting = supervisor.start();
  await Promise.resolve();
  f.state.originPaused = true;
  release(`${ORIGIN}/app`);
  try { await starting; assert.equal(f.calls.start, 0); }
  finally { await supervisor.stop(); }
});

test('actual recorder pauses on transient origin loss and resumes through its own fence', async () => {
  const root = await mkdtemp(join(tmpdir(), 'footwork-supervisor-'));
  let urlChecks = 0;
  const tab = { url: async () => {
    urlChecks++;
    if (urlChecks === 5) throw new Error('temporary browser disconnect');
    return `${ORIGIN}/app`;
  } };
  const ring = createEventRing({ sessionId: 'selected', methods: METHODS });
  const capture = createCapture({ tab, cdp: { readEvents: ring.readEvents, send: async () => ({}) },
    projectRoot: root, allowedOrigin: ORIGIN, runId: 'recovery-fixture', domainsToEnable: [] });
  let supervisor;
  try {
    await capture.start();
    await capture.startPolling({ intervalMs: 100 });
    const deadline = Date.now() + 2000;
    while (capture.status().polling.pauseReason !== 'origin-check-unavailable' && Date.now() < deadline) {
      await new Promise(resolve => setTimeout(resolve, 20));
    }
    assert.equal(capture.status().polling.pauseReason, 'origin-check-unavailable');
    supervisor = createPollingSupervisor({ capture, tab, allowedOrigin: ORIGIN, intervalMs: 100, retryMs: 10000 });
    await supervisor.start();
    assert.equal(capture.status().polling.active, true);
    assert.equal(supervisor.status().resumed, 1);
    await supervisor.stop();
    await capture.stop();
    const actions = await readFile(join(root, 'output', 'browser-inspection', 'recovery-fixture', 'actions.jsonl'), 'utf8');
    assert.equal(actions.match(/"type":"polling_started"/g)?.length, 2);
    assert(!actions.includes(`${ORIGIN}/app`));
  } finally {
    if (supervisor?.status().active) await supervisor.stop();
    if (capture.status().started && !capture.status().stopped) await capture.stop();
    await rm(root, { recursive: true, force: true });
  }
});
