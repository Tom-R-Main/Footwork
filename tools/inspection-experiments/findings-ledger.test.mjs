import test from 'node:test';
import assert from 'node:assert/strict';
import { validateFindings, projectFindings } from './findings-ledger.mjs';

const context = { packetFingerprint: 'packet-123', steps: [{ stepFingerprint: 'step-123', intervalKnown: true, startCursor: 4, endCursor: 9 }], eventSequences: new Set([5]) };
const observed = { id: 'C1', text: 'SECRET_PRODUCT has a response', evidenceType: 'observed', confidence: 'medium', coverageLimit: 'observed-interval',
  falsifier: 'SECRET_FALSIFIER via a repeated capture', source: { packetFingerprint: 'packet-123', stepFingerprint: 'step-123', startCursor: 4, endCursor: 9, eventSequence: 5 } };

test('validates bounded observed, documented, and inferred sources without exporting prose', () => {
  const claims = [observed, { id: 'C2', text: 'A vendor documents a capability', evidenceType: 'documented', confidence: 'high', coverageLimit: 'document-only',
    falsifier: 'Updated vendor documentation', source: { citation: 'https://example.test/docs', accessDate: '2026-10-01' } },
  { id: 'C3', text: 'An inferred implementation detail', evidenceType: 'inferred', confidence: 'low', coverageLimit: 'inference',
    falsifier: 'A direct provider identifier', source: { premiseIds: ['C1', 'C2'] } }];
  assert.deepEqual(validateFindings(claims, context), { valid: true, errors: [] });
  const projection = JSON.stringify(projectFindings(claims));
  assert(!projection.includes('SECRET_PRODUCT'));
  assert(!projection.includes('SECRET_FALSIFIER'));
  assert(!projection.includes('example.test'));
  assert(projection.includes('eventSequence'));
});

test('rejects forged packet, nonexistent event, and unsupported inference', () => {
  const forged = { ...observed, source: { ...observed.source, packetFingerprint: 'wrong', eventSequence: 8 } };
  const unsupported = { id: 'C2', text: 'A proposed database', evidenceType: 'inferred', confidence: 'high', coverageLimit: 'inference',
    falsifier: 'Provider error names another database', source: { premiseIds: ['missing'] } };
  const result = validateFindings([forged, unsupported], context);
  assert.equal(result.valid, false);
  assert(result.errors.some(error => error.includes('packet')));
  assert(result.errors.some(error => error.includes('real event')));
  assert(result.errors.some(error => error.includes('prior premises')));
});
