import { createHash } from 'node:crypto';
import { readFile, realpath, stat } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { readJournal, verifyManifest } from '../browser-inspection/summarize.mjs';

const JOURNALS = ['events.jsonl', 'actions.jsonl', 'gaps.jsonl', 'bodies.jsonl'];
const MAX_JOURNAL_BYTES = 128 * 1024 * 1024;
const METHODS = [
  'Network.requestWillBeSent', 'Network.responseReceived', 'Network.loadingFinished', 'Network.loadingFailed',
  'Network.dataReceived', 'Network.requestServedFromCache', 'Network.responseReceivedExtraInfo',
  'Network.eventSourceMessageReceived', 'Network.webSocketCreated', 'Network.webSocketClosed',
  'Network.webSocketFrameReceived', 'Network.webSocketFrameSent', 'Runtime.consoleAPICalled',
  'Runtime.exceptionThrown',
];
const GAP_REASONS = new Set([
  'event-buffer-truncated', 'baseline-buffer-truncated', 'missing-response-metadata',
  'body-unavailable-or-evicted', 'read-events-failed', 'invalid-event-batch',
  'cursor-regression', 'invalid-or-unrequested-event', 'cursor-stalled', 'drain-page-limit',
  'origin-changed', 'origin-check-unavailable', 'polling-paused-drain-failure',
  'polling-paused-exception', 'post-action-drain-failed', 'post-action-snapshot-failed',
  'final-step-drain-failed', 'dom-snapshot-unavailable', 'screenshot-unavailable',
  'domain-enable-unsupported', 'domain-disable-failed',
]);
const BODY_STATUSES = new Set([
  'captured', 'omitted-content-policy', 'omitted-scope-or-mime', 'omitted-byte-cap',
  'unavailable', 'stream-fixture',
]);
const HTTP_METHODS = new Set(['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD']);
const hash = value => createHash('sha256').update(value).digest('hex').slice(0, 20);
const count = (map, key) => map.set(key, (map.get(key) ?? 0) + 1);
const sortedCounts = map => Object.fromEntries([...map].sort(([a], [b]) => a.localeCompare(b)));
const methodClass = value => HTTP_METHODS.has(value) ? value : 'OTHER';
const originClass = (value, allowedOrigin) => {
  if (!allowedOrigin) return 'unknown';
  try {
    const parsed = new URL(value);
    if (!['https:', 'http:'].includes(parsed.protocol)) return 'unknown';
    return parsed.origin === allowedOrigin ? 'same-origin' : 'external-origin';
  } catch { return 'unknown'; }
};
const sourceKey = (source = {}) => JSON.stringify([source.extensionId ?? null, source.tabId ?? null, source.sessionId ?? null, source.targetId ?? null]);
const requestKey = (source, requestId) => JSON.stringify([sourceKey(source), requestId ?? null]);
const finiteCursor = value => Number.isSafeInteger(value) && value >= 0;

export function auditCoverage({ events = [], actions = [], gaps = [], bodies = [] }, manifest = {}) {
  const observedMethods = new Map(), gapReasons = new Map(), bodyStatuses = new Map();
  const active = new Map(), requests = [];
  let redirects = 0, orphanResponses = 0, orphanTerminals = 0, orphanDataEvents = 0, implicitReuses = 0;
  let outOfOrderSequences = 0, previousSequence = -1;
  const sources = new Set();
  const allowedOrigin = actions.find(row => row.type === 'capture_started')?.origin;
  for (const row of events) {
    const event = row.event ?? row;
    if (!METHODS.includes(event.method)) continue;
    count(observedMethods, event.method);
    sources.add(sourceKey(event.source));
    if (finiteCursor(event.sequence)) {
      if (event.sequence <= previousSequence) outOfOrderSequences++;
      previousSequence = Math.max(previousSequence, event.sequence);
    }
    const params = event.params ?? {};
    const key = requestKey(event.source, params.requestId);
    if (event.method === 'Network.requestWillBeSent') {
      const prior = active.get(key);
      if (prior && params.redirectResponse) {
        prior.redirect = true;
        prior.terminal = true;
        redirects++;
      } else if (prior && !prior.terminal) {
        prior.implicitReuse = true;
        implicitReuses++;
      }
      const request = { key, start: event.sequence, method: methodClass(params.request?.method), origin: originClass(params.request?.url, allowedOrigin), response: false, terminal: false, failed: false, redirect: false, implicitReuse: false, cache: false };
      requests.push(request);
      active.set(key, request);
    } else if (event.method === 'Network.responseReceived') {
      const request = active.get(key);
      if (request) request.response = true;
      else orphanResponses++;
    } else if (event.method === 'Network.loadingFinished' || event.method === 'Network.loadingFailed') {
      const request = active.get(key);
      if (request) {
        request.terminal = true;
        request.failed = event.method === 'Network.loadingFailed';
      } else orphanTerminals++;
    } else if (event.method === 'Network.dataReceived') {
      if (!active.has(key)) orphanDataEvents++;
    } else if (event.method === 'Network.requestServedFromCache') {
      const request = active.get(key);
      if (request) request.cache = true;
    }
    // ExtraInfo events are deliberately not required: CDP says they may be absent
    // and may arrive before or after the request event.
  }
  for (const row of gaps) count(gapReasons, GAP_REASONS.has(row.reason) ? row.reason : 'other');
  for (const row of bodies) count(bodyStatuses, BODY_STATUSES.has(row.status) ? row.status : 'other');
  const gapCursors = gaps.filter(g => finiteCursor(g.cursor)).map(g => g.cursor);
  const unscopedGaps = gaps.length - gapCursors.length;
  const ends = new Map();
  for (const row of actions) if (row.type === 'step_end') ends.set(JSON.stringify([row.workflowId ?? '', row.stepId ?? '']), row);
  const steps = actions.filter(row => row.type === 'step_begin').map(begin => {
    const id = JSON.stringify([begin.workflowId ?? '', begin.stepId ?? '']);
    const end = ends.get(id);
    const startCursor = begin.cursorBefore, endCursor = end?.cursorAfter;
    const intervalKnown = finiteCursor(startCursor) && finiteCursor(endCursor) && endCursor >= startCursor;
    const gapsInInterval = intervalKnown ? gapCursors.filter(cursor => cursor >= startCursor && cursor <= endCursor).length : null;
    const started = intervalKnown ? requests.filter(request => finiteCursor(request.start) && request.start >= startCursor && request.start <= endCursor) : [];
    const byMethod = new Map(), byOrigin = new Map(), postsByOrigin = new Map();
    for (const request of started) {
      count(byMethod, request.method);
      count(byOrigin, request.origin);
      if (request.method === 'POST') count(postsByOrigin, request.origin);
    }
    return { stepFingerprint: hash(id), intervalKnown, reportedGapsInInterval: gapsInInterval,
      status: end?.status === 'completed' ? 'action-callback-completed' : end?.status === 'failed' ? 'action-callback-failed' : 'incomplete',
      coverage: !intervalKnown || unscopedGaps || gapsInInterval ? 'limited' : 'no-reported-interval-gaps',
      traffic: { requestsStarted: intervalKnown ? started.length : null, byMethod: sortedCounts(byMethod), byOrigin: sortedCounts(byOrigin), postsByOrigin: sortedCounts(postsByOrigin) } };
  });
  const byMethod = Object.fromEntries(METHODS.map(method => [method, {
    subscribed: Array.isArray(manifest.recording?.methods) && manifest.recording.methods.includes(method),
    observed: observedMethods.get(method) ?? 0,
  }]));
  return {
    schemaVersion: 1,
    assessment: gaps.length || outOfOrderSequences || orphanResponses || orphanTerminals ? 'limited' : 'no-reported-capture-gaps',
    capture: { eventRows: events.length, sourceIdentities: sources.size, reportedGaps: gaps.length, gapReasons: sortedCounts(gapReasons), unscopedGaps, outOfOrderSequences,
      declaredMode: manifest.recording?.mode === 'polling' ? 'polling' : 'bounded-or-unknown',
      pollingTicks: Number.isSafeInteger(manifest.recording?.polling?.ticks) ? manifest.recording.polling.ticks : null,
      unsupportedFeatures: Array.isArray(manifest.unsupported) ? manifest.unsupported.length : 0,
      cleanupFailures: Array.isArray(manifest.cleanupFailures) ? manifest.cleanupFailures.length : 0 },
    networkLifecycle: { requestHops: requests.length, redirects, responsesObserved: requests.filter(r => r.response).length,
      terminalEventsObserved: requests.filter(r => r.terminal).length, failedLoads: requests.filter(r => r.failed).length,
      terminalWithoutResponse: requests.filter(r => r.terminal && !r.response && !r.redirect).length,
      unclosedAtCaptureEnd: requests.filter(r => !r.terminal).length,
      implicitRequestIdReuses: implicitReuses, orphanResponses, orphanTerminals, orphanDataEvents,
      servedFromCache: requests.filter(r => r.cache).length },
    bodyPolicy: { records: bodies.length, statuses: sortedCounts(bodyStatuses) },
    protocols: byMethod,
    steps,
    limitations: [
      'No reported gap is not proof of complete capture; recording may start after page load or miss worker targets.',
      'A request without a terminal event may be a long-lived stream or may be outside the recorded interval.',
      'Orphan and missing-response events indicate incomplete local lifecycle evidence, not necessarily product failure.',
      'ExtraInfo events are optional and unordered by CDP; their absence is not counted as lost traffic.',
      'Response body records reflect capture policy and availability, not all bytes delivered to the browser.',
      'Action callback completion does not prove a visible, persisted, or correct product effect.',
      'Step traffic is coincident with an action interval, not proof that the action caused a request.',
    ],
  };
}

export async function auditSealedRun(directory) {
  const root = await realpath(directory);
  const manifestText = await readFile(resolve(root, 'manifest.json'), 'utf8');
  const manifest = JSON.parse(manifestText);
  const integrity = await verifyManifest(root, manifest);
  if (!integrity.verified) throw new Error(`Refusing unverified run: ${integrity.errors.join('; ')}`);
  for (const name of JOURNALS) if ((await stat(resolve(root, name))).size > MAX_JOURNAL_BYTES) throw new Error(`Journal exceeds offline analysis cap: ${name}`);
  const loaded = await Promise.all(JOURNALS.map(name => readJournal(resolve(root, name))));
  if (loaded.some(item => item.absent)) throw new Error('A required journal is missing');
  const journals = Object.fromEntries(JOURNALS.map((name, index) => [name.slice(0, -6), loaded[index].rows]));
  return { packetFingerprint: hash(manifestText), manifestIntegrity: 'hashes-verified', ...auditCoverage(journals, manifest) };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    if (process.argv.length !== 3) throw new Error('Usage: node coverage.mjs <sealed-run-directory>');
    process.stdout.write(`${JSON.stringify(await auditSealedRun(process.argv[2]), null, 2)}\n`);
  } catch (error) { console.error(error.message); process.exitCode = 1; }
}
