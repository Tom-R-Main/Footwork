import { createHash } from 'node:crypto';
import { readFile, realpath, stat } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { analyze, readJournal, verifyManifest } from '../browser-inspection/summarize.mjs';

const JOURNALS = ['events.jsonl', 'actions.jsonl', 'gaps.jsonl', 'bodies.jsonl'];
const MAX_JOURNAL_BYTES = 128 * 1024 * 1024;
const fingerprint = value => createHash('sha256').update(value).digest('hex').slice(0, 20);

function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(key => [key, stable(value[key])]));
  return value;
}

function endpointId(method, endpoint) { return fingerprint(JSON.stringify([method, endpoint])); }
function urlId(url) {
  try { const parsed = new URL(url); return fingerprint(`${parsed.origin}${parsed.pathname}`); }
  catch { return fingerprint('[unavailable]'); }
}
function counts(items) {
  const result = new Map();
  for (const item of items) result.set(item, (result.get(item) ?? 0) + 1);
  return Object.fromEntries([...result].sort(([a], [b]) => a.localeCompare(b)));
}

export function profile(journals) {
  const digest = analyze(journals);
  const eventBySequence = new Map(journals.events.map(row => {
    const event = row.event ?? row;
    return [event.sequence, event];
  }));
  const requestByIdentity = new Map(digest.requests.map(request => [`${request.key}:${request.hop}`, request]));
  const seenSteps = new Set();
  const steps = digest.steps.map(step => {
    const identity = JSON.stringify([step.workflowId ?? '', step.stepId ?? '']);
    if (seenSteps.has(identity)) throw new Error('Repeated workflow and step identity in one run');
    seenSteps.add(identity);
    const requests = step.associatedRequests.map(ref => requestByIdentity.get(`${ref.key}:${ref.hop}`)).filter(Boolean);
    const byEndpoint = new Map();
    for (const request of requests) {
      const id = endpointId(request.method, request.endpoint);
      const entry = byEndpoint.get(id) ?? { endpointId: id, method: /^[A-Z]{1,12}$/.test(request.method) ? request.method : '?', hops: 0, statuses: [], failures: 0, unfinished: 0, requestShapes: [] };
      entry.hops++;
      if (Number.isInteger(request.status) && request.status >= 100 && request.status <= 599) entry.statuses.push(request.status);
      if (request.failed) entry.failures++;
      if (request.finishedSequence === null) entry.unfinished++;
      const shape = eventBySequence.get(request.startedSequence)?.params?.requestBody?.shape;
      if (shape !== undefined) entry.requestShapes.push(fingerprint(JSON.stringify(stable(shape))));
      byEndpoint.set(id, entry);
    }
    const endpoints = [...byEndpoint.values()].map(entry => ({ ...entry, statuses: counts(entry.statuses), requestShapes: counts(entry.requestShapes) })).sort((a, b) => a.endpointId.localeCompare(b.endpointId));
    return { identity, workflowId: step.workflowId ?? '', stepId: step.stepId ?? '', status: step.status, acknowledgement: step.acknowledgement, endpoints };
  });
  const responses = new Map();
  for (const body of journals.bodies) {
    const id = urlId(body.url);
    const entry = responses.get(id) ?? { urlId: id, statuses: [], shapeFingerprints: [] };
    entry.statuses.push(body.status ?? 'unknown');
    if (body.shape !== undefined) entry.shapeFingerprints.push(fingerprint(JSON.stringify(stable(body.shape))));
    responses.set(id, entry);
  }
  return {
    steps,
    responses: [...responses.values()].map(entry => ({ urlId: entry.urlId, statuses: counts(entry.statuses), shapeFingerprints: counts(entry.shapeFingerprints) })).sort((a, b) => a.urlId.localeCompare(b.urlId)),
    gaps: journals.gaps.length,
    requestHops: digest.requests.length,
  };
}

function endpointDelta(control = [], variant = []) {
  const left = new Map(control.map(item => [item.endpointId, item]));
  const right = new Map(variant.map(item => [item.endpointId, item]));
  return [...new Set([...left.keys(), ...right.keys()])].sort().map(id => {
    const a = left.get(id), b = right.get(id);
    const method = a?.method ?? b?.method;
    return { endpointId: id, method, control: a ?? null, variant: b ?? null,
      change: !a ? 'added-in-variant' : !b ? 'missing-in-variant' : JSON.stringify(a) === JSON.stringify(b) ? 'same-observed-profile' : 'changed-observed-profile' };
  });
}

export function compareProfiles(control, variant) {
  const left = new Map(control.steps.map(step => [step.identity, step]));
  const right = new Map(variant.steps.map(step => [step.identity, step]));
  const steps = [...new Set([...left.keys(), ...right.keys()])].sort().map(identity => {
    const a = left.get(identity), b = right.get(identity);
    return { workflowId: a?.workflowId ?? b?.workflowId, stepId: a?.stepId ?? b?.stepId,
      comparison: a && b ? 'paired-intervals' : 'incomparable-missing-step',
      quality: control.gaps || variant.gaps || !a || !b || a.status === 'incomplete' || b.status === 'incomplete' ? 'limited' : 'bounded-observation',
      controlStatus: a?.status ?? null, variantStatus: b?.status ?? null,
      controlAcknowledgement: a?.acknowledgement ?? null, variantAcknowledgement: b?.acknowledgement ?? null,
      // A missing step has no valid interval; avoid reporting its traffic as absent.
      endpoints: a && b ? endpointDelta(a.endpoints, b.endpoints) : [],
    };
  });
  const responseLeft = new Map(control.responses.map(item => [item.urlId, item]));
  const responseRight = new Map(variant.responses.map(item => [item.urlId, item]));
  const responses = [...new Set([...responseLeft.keys(), ...responseRight.keys()])].sort().map(id => {
    const a = responseLeft.get(id), b = responseRight.get(id);
    return { urlId: id, control: a ?? null, variant: b ?? null,
      change: !a ? 'added-in-variant' : !b ? 'missing-in-variant' : JSON.stringify(a) === JSON.stringify(b) ? 'same-observed-profile' : 'changed-observed-profile' };
  });
  return { schemaVersion: 1, method: 'sealed-journal-paired-interval-comparison',
    coverage: { control: { steps: control.steps.length, gaps: control.gaps, requestHops: control.requestHops }, variant: { steps: variant.steps.length, gaps: variant.gaps, requestHops: variant.requestHops } },
    steps, responses,
    limitations: [
      'Requests are associated with step capture intervals, not attributed causally to user actions.',
      'Endpoint IDs and shape fingerprints are hashes; no URL paths, query values, body values or visible-effect text are emitted.',
      'Response body shapes are run-level because body records do not carry an unambiguous step identity.',
      'A missing request, body or step is not evidence that the product lacks the behavior; capture gaps further limit comparison.',
      'HTTP status, action completion and operator acknowledgement do not prove visible effect, durable persistence or correctness.',
    ] };
}

export async function loadSealedRun(directory) {
  const root = await realpath(directory);
  const manifestText = await readFile(resolve(root, 'manifest.json'), 'utf8');
  const manifest = JSON.parse(manifestText);
  const integrity = await verifyManifest(root, manifest);
  if (!integrity.verified) throw new Error(`Refusing unverified run: ${integrity.errors.join('; ')}`);
  for (const name of JOURNALS) if ((await stat(resolve(root, name))).size > MAX_JOURNAL_BYTES) throw new Error(`Journal exceeds offline analysis cap: ${name}`);
  const loaded = await Promise.all(JOURNALS.map(name => readJournal(resolve(root, name))));
  if (loaded.some(item => item.absent)) throw new Error('A required journal is missing');
  return { packetId: fingerprint(manifestText), profile: profile(Object.fromEntries(JOURNALS.map((name, index) => [name.slice(0, -6), loaded[index].rows]))) };
}

export async function compareRuns(controlDirectory, variantDirectory) {
  const [controlPath, variantPath] = await Promise.all([realpath(controlDirectory), realpath(variantDirectory)]);
  if (controlPath === variantPath) throw new Error('Control and variant must be different sealed runs');
  const [control, variant] = await Promise.all([loadSealedRun(controlPath), loadSealedRun(variantPath)]);
  return { packets: { control: control.packetId, variant: variant.packetId }, ...compareProfiles(control.profile, variant.profile) };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    if (process.argv.length !== 4) throw new Error('Usage: node compare.mjs <sealed-control-run> <sealed-variant-run>');
    process.stdout.write(`${JSON.stringify(await compareRuns(process.argv[2], process.argv[3]), null, 2)}\n`);
  } catch (error) { console.error(error.message); process.exitCode = 1; }
}
