import { readFile, writeFile, realpath, lstat } from 'node:fs/promises';
import { resolve, dirname, relative, isAbsolute } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';

const outputRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../output/browser-inspection');
const journals = ['events.jsonl', 'actions.jsonl', 'gaps.jsonl', 'bodies.jsonl'];

export function contained(base, path) {
  const rel = relative(base, path);
  return rel !== '' && !rel.startsWith('../') && rel !== '..' && !isAbsolute(rel);
}

export async function readJournal(path) {
  let text;
  try { text = await readFile(path, 'utf8'); }
  catch (error) { if (error.code === 'ENOENT') return { rows: [], absent: true }; throw error; }
  const rows = text.split('\n').filter(line => line.trim()).map((line, index) => {
    try { return JSON.parse(line); }
    catch { throw new Error(`Invalid JSONL at ${path}:${index + 1}`); }
  });
  return { rows, absent: false };
}

function sourceKey(source = {}) {
  return [source.extensionId ?? '', source.tabId ?? '', source.sessionId ?? '', source.targetId ?? ''].join(':');
}

function cleanEndpoint(value) {
  try {
    const url = new URL(value);
    return `${url.origin}${url.pathname}`;
  } catch { return '[unavailable]'; }
}

export function analyze({ events = [], actions = [], gaps = [], bodies = [] }) {
  const requests = [];
  const active = new Map();
  for (const row of events) {
    const e = row.event ?? row;
    const p = e.params ?? {};
    const key = `${sourceKey(e.source)}:${p.requestId ?? ''}`;
    if (e.method === 'Network.requestWillBeSent') {
      const previous = active.get(key);
      if (previous && p.redirectResponse) {
        previous.status = p.redirectResponse.status;
        previous.redirect = true;
        previous.finishedSequence = e.sequence;
      }
      const request = {
        key, requestId: p.requestId, source: e.source,
        method: p.request?.method ?? '?', endpoint: cleanEndpoint(p.request?.url),
        startedSequence: e.sequence, wallTime: p.wallTime, timestamp: p.timestamp,
        hop: requests.filter(r => r.key === key).length,
        status: null, finishedSequence: null, failed: false, redirect: false,
      };
      requests.push(request);
      active.set(key, request);
    } else {
      const request = active.get(key);
      if (!request) continue;
      if (e.method === 'Network.responseReceived') {
        request.status = p.response?.status ?? null;
        request.mimeType = p.response?.mimeType;
      }
      if (e.method === 'Network.loadingFinished' || e.method === 'Network.loadingFailed') {
        request.finishedSequence = e.sequence;
        request.failed = e.method === 'Network.loadingFailed';
        request.elapsedMs = Number.isFinite(p.timestamp) && Number.isFinite(request.timestamp)
          ? Math.round((p.timestamp - request.timestamp) * 1000) : null;
      }
    }
  }
  const steps = actions.filter(a => a.type === 'step_begin').map(begin => {
    const end = actions.find(a => a.type === 'step_end' && a.stepId === begin.stepId);
    const start = begin.cursorBefore;
    const finish = end?.cursorAfter;
    return {
      stepId: begin.stepId, workflowId: begin.workflowId, intent: begin.intent,
      status: end?.status ?? 'incomplete', acknowledgement: end?.acknowledgement ?? 'not-evaluated',
      visibleEffect: end?.visibleEffect ?? null,
      // Association by capture interval, deliberately not a causal attribution.
      associatedRequests: requests.filter(r => Number.isFinite(start) && Number.isFinite(finish)
        && r.startedSequence > start && r.startedSequence <= finish).map(r => ({ key: r.key, hop: r.hop })),
    };
  });
  const endpoints = new Map();
  for (const request of requests) {
    const key = `${request.method} ${request.endpoint}`;
    const entry = endpoints.get(key) ?? { endpoint: key, requests: 0, statuses: [], failures: 0, unfinished: 0 };
    entry.requests++;
    if (request.status !== null && !entry.statuses.includes(request.status)) entry.statuses.push(request.status);
    if (request.failed) entry.failures++;
    if (request.finishedSequence === null) entry.unfinished++;
    endpoints.set(key, entry);
  }
  return { requests, steps, endpoints: [...endpoints.values()], gaps, bodyCount: bodies.length,
    bodyModes: [...new Set(bodies.map(b => b.captureMode))] };
}

export async function verifyManifest(runDirectory, manifest) {
  const root = await realpath(runDirectory);
  const errors = [];
  const files = Array.isArray(manifest.files) ? manifest.files : [];
  if (!files.length) errors.push('Manifest has no file hashes');
  for (const file of files) {
    const path = resolve(root, file.path);
    if (!contained(root, path)) { errors.push('Manifest path escapes run directory'); continue; }
    try {
      const actualPath = await realpath(path);
      if (!contained(root, actualPath) || (await lstat(path)).isSymbolicLink()) {
        errors.push(`Unsafe artifact path: ${file.path}`); continue;
      }
      const bytes = await readFile(path);
      if (createHash('sha256').update(bytes).digest('hex') !== file.sha256) errors.push(`Hash mismatch: ${file.path}`);
      if (file.bytes !== undefined && bytes.byteLength !== file.bytes) errors.push(`Size mismatch: ${file.path}`);
    } catch (error) { errors.push(`Unreadable artifact: ${file.path} (${error.code ?? 'error'})`); }
  }
  for (const journal of journals) if (!files.some(file => file.path === journal)) errors.push(`Journal not hashed: ${journal}`);
  return { checkedFiles: files.length, errors, verified: errors.length === 0 };
}

const md = value => String(value ?? '').replace(/[|\r\n]/g, ' ').replace(/</g, '&lt;').replace(/>/g, '&gt;');

export function render(result, integrity, manifest = {}) {
  const lines = ['# Symbolic capture digest', '',
    `Run: ${md(manifest.runId ?? 'unknown')}. Integrity: ${integrity.verified ? 'verified' : 'FAILED or unavailable'}.`, '',
    'This digest associates requests with observation intervals. It does not infer causal attribution, successful persistence, or workflow completion from HTTP status alone.', '',
    `Events reconstructed: ${result.requests.length} request hops. Bodies: ${result.bodyCount}. Gaps: ${result.gaps.length}.`, '',
    '## Steps', '', '| Step | Workflow | Status | Requests in interval | Effect assessment |',
    '| --- | --- | --- | --- | --- |'];
  for (const s of result.steps) lines.push(`| ${md(s.stepId)} | ${md(s.workflowId)} | ${md(s.status)} | ${s.associatedRequests.length} | ${md(s.acknowledgement)} |`);
  if (!result.steps.length) lines.push('| No driven steps recorded | | | | |');
  lines.push('', '## Observed endpoints', '', '| Method and endpoint | Hops | Statuses | Failures | Unfinished |', '| --- | --- | --- | --- | --- |');
  for (const e of result.endpoints) lines.push(`| ${md(e.endpoint)} | ${e.requests} | ${e.statuses.join(', ')} | ${e.failures} | ${e.unfinished} |`);
  lines.push('', '## Evidence limitations', '');
  for (const error of integrity.errors) lines.push(`- ${md(error)}`);
  for (const gap of result.gaps) lines.push(`- ${md(gap.reason)} (cursor ${md(gap.cursor)})`);
  if (manifest.unsupported) lines.push(`- Unsupported capture features: ${md(JSON.stringify(manifest.unsupported))}`);
  lines.push('- Body shapes omit original values by default. Screenshots and DOM artifacts require separate privacy review.',
    '- No absence or implementation claim should be drawn from a recording that starts after initial page load.',
    '- Consult the workflow observation and hypothesis records for interpretation.', '');
  return lines.join('\n');
}

export async function summarize(runDirectory, { outputDirectory = outputRoot } = {}) {
  const directory = await realpath(runDirectory);
  const root = await realpath(outputDirectory);
  if (!contained(root, directory)) throw new Error('Run directory must be inside the declared inspection output directory');
  const manifest = JSON.parse(await readFile(resolve(directory, 'manifest.json'), 'utf8'));
  const integrity = await verifyManifest(directory, manifest);
  const loaded = await Promise.all(journals.map(j => readJournal(resolve(directory, j))));
  loaded.forEach((j, i) => { if (j.absent) integrity.errors.push(`Missing journal: ${journals[i]}`); });
  integrity.verified = integrity.errors.length === 0;
  const result = analyze(Object.fromEntries(['events','actions','gaps','bodies'].map((key, i) => [key, loaded[i].rows])));
  // Generated digests are derivative and deliberately not members of the sealed capture manifest.
  for (const name of ['digest.json', 'digest.md']) {
    try { if ((await lstat(resolve(directory, name))).isSymbolicLink()) throw new Error('Digest output cannot be a symlink'); }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
  await writeFile(resolve(directory, 'digest.json'), JSON.stringify({ integrity, ...result }, null, 2));
  await writeFile(resolve(directory, 'digest.md'), render(result, integrity, manifest));
  return { requestHops: result.requests.length, steps: result.steps.length, gaps: result.gaps.length, integrity };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    if (!process.argv[2]) throw new Error('Usage: node summarize.mjs <output/browser-inspection/run-directory>');
    const result = await summarize(process.argv[2]);
    console.log(JSON.stringify(result));
    if (!result.integrity.verified) process.exitCode = 1;
  } catch (error) { console.error(error.message); process.exitCode = 1; }
}
