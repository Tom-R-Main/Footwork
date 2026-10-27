import { createHash } from 'node:crypto';
import path from 'node:path';
import { readJournal } from '../browser-inspection/summarize.mjs';
import { auditSealedRun } from './coverage.mjs';

const id = value => typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$/.test(value);
const hash = value => createHash('sha256').update(value).digest('hex').slice(0, 20);
const CONFIDENCE = new Set(['low', 'medium', 'high']);
const LIMIT = new Set(['page-target-only', 'partial-lifecycle', 'observed-interval', 'document-only', 'inference']);

export function validateFindings(claims, { packetFingerprint, steps = [], eventSequences = new Set() } = {}) {
  if (!Array.isArray(claims) || !claims.length || claims.length > 1000) throw new Error('Bounded nonempty claims required');
  const known = new Set(), stepMap = new Map(steps.map(step => [step.stepFingerprint, step]));
  const errors = [];
  for (const [index, claim] of claims.entries()) {
    if (!id(claim?.id) || known.has(claim.id)) { errors.push(`claim ${index}: invalid or duplicate ID`); continue; }
    known.add(claim.id);
    if (typeof claim.text !== 'string' || claim.text.length < 3 || claim.text.length > 2000) errors.push(`${claim.id}: bounded text required`);
    if (!CONFIDENCE.has(claim.confidence) || !LIMIT.has(claim.coverageLimit)) errors.push(`${claim.id}: confidence and coverage limit required`);
    if (typeof claim.falsifier !== 'string' || claim.falsifier.length < 3 || claim.falsifier.length > 1000) errors.push(`${claim.id}: falsifier required`);
    if (claim.evidenceType === 'observed') {
      const source = claim.source;
      const step = stepMap.get(source?.stepFingerprint);
      if (source?.packetFingerprint !== packetFingerprint || !step || !step.intervalKnown ||
          source?.startCursor !== step.startCursor || source?.endCursor !== step.endCursor) errors.push(`${claim.id}: verified packet and exact step interval required`);
      if (!Number.isSafeInteger(source?.eventSequence) || !eventSequences.has(source.eventSequence) ||
          !step || source.eventSequence < step.startCursor || source.eventSequence > step.endCursor) errors.push(`${claim.id}: real event inside step interval required`);
      if (claim.coverageLimit === 'document-only' || claim.coverageLimit === 'inference') errors.push(`${claim.id}: observed claim has wrong coverage class`);
    } else if (claim.evidenceType === 'documented') {
      if (typeof claim.source?.citation !== 'string' || !/^https:\/\//.test(claim.source.citation) ||
          !/^\d{4}-\d{2}-\d{2}$/.test(claim.source?.accessDate || '') || claim.coverageLimit !== 'document-only') errors.push(`${claim.id}: documented source/date required`);
    } else if (claim.evidenceType === 'inferred') {
      if (!Array.isArray(claim.source?.premiseIds) || !claim.source.premiseIds.length || claim.source.premiseIds.some(premise => !known.has(premise)) || claim.coverageLimit !== 'inference') errors.push(`${claim.id}: prior premises required`);
    } else errors.push(`${claim.id}: unknown evidence type`);
  }
  return { valid: errors.length === 0, errors };
}

export async function validateSealedFindings({ runDirectory, claims }) {
  const audit = await auditSealedRun(runDirectory);
  const journal = await readJournal(path.join(runDirectory, 'actions.jsonl'));
  const events = await readJournal(path.join(runDirectory, 'events.jsonl'));
  if (journal.absent || events.absent) throw new Error('Required journal unavailable');
  const starts = new Map(journal.rows.filter(row => row.type === 'step_begin').map(row => [JSON.stringify([row.workflowId, row.stepId]), row]));
  const steps = journal.rows.filter(row => row.type === 'step_end').map(end => {
    const key = JSON.stringify([end.workflowId, end.stepId]);
    const begin = starts.get(key);
    return { stepFingerprint: hash(key), intervalKnown: Number.isSafeInteger(begin?.cursorBefore) && Number.isSafeInteger(end.cursorAfter),
      startCursor: begin?.cursorBefore, endCursor: end.cursorAfter };
  });
  const eventSequences = new Set(events.rows.map(row => row.event?.sequence ?? row.sequence).filter(Number.isSafeInteger));
  const result = validateFindings(claims, { packetFingerprint: audit.packetFingerprint, steps, eventSequences });
  return { ...result, packetFingerprint: audit.packetFingerprint, packetAssessment: audit.assessment };
}

/** Safe index for a shared research note; claim prose and URLs remain in the private ledger. */
export function projectFindings(claims) {
  return claims.map(claim => ({ id: claim.id, evidenceType: claim.evidenceType, confidence: claim.confidence,
    coverageLimit: claim.coverageLimit, packetFingerprint: claim.evidenceType === 'observed' ? claim.source?.packetFingerprint : undefined,
    stepFingerprint: claim.evidenceType === 'observed' ? claim.source?.stepFingerprint : undefined,
    interval: claim.evidenceType === 'observed' ? [claim.source?.startCursor, claim.source?.endCursor] : undefined,
    eventSequence: claim.evidenceType === 'observed' ? claim.source?.eventSequence : undefined,
    premiseIds: claim.evidenceType === 'inferred' ? claim.source?.premiseIds : undefined }));
}
