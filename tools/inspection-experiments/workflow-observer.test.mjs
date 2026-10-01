import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { createWorkflowObserver } from './workflow-observer.mjs';

test('checkpoints use separate action/readback steps and persist bounded statuses', async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'workflow-observer-'));
  const calls = [];
  try {
    await mkdir(path.join(directory, 'artifacts'));
    const capture = { step: async ({ stepId, action }) => { calls.push(stepId); return action(); } };
    const observer = createWorkflowObserver({ capture, runDirectory: directory });
    const receipt = await observer.run({ workflowId: 'public', stepId: 'submit', intent: 'SECRET_INTENT',
      precondition: () => true, action: () => { calls.push('click'); }, immediate: () => true,
      settled: () => true, readback: () => true });
    assert.equal(receipt.outcome, 'verified');
    assert.deepEqual(calls, ['submit', 'click', 'submit-readback']);
    const artifact = await observer.writeArtifact();
    const text = await readFile(artifact.path, 'utf8');
    assert(!text.includes('SECRET_INTENT'));
    assert.equal(JSON.parse(text).receipts[0].readback, 'passed');
    await writeFile(path.join(directory, 'manifest.json'), '{}');
    await assert.rejects(observer.writeArtifact({ label: 'late' }), /sealed/);
  } finally { await rm(directory, { recursive: true, force: true }); }
});

test('failed precondition skips action; absent readback cannot verify persistence', async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'workflow-observer-'));
  try {
    let count = 0;
    const capture = { step: async ({ action }) => { count++; return action(); } };
    const observer = createWorkflowObserver({ capture, runDirectory: directory });
    const skipped = await observer.run({ workflowId: 'public', stepId: 'skip', precondition: () => false, action: () => { count++; } });
    assert.equal(skipped.outcome, 'incomplete'); assert.equal(count, 0);
    const unknown = await observer.run({ workflowId: 'public', stepId: 'partial', precondition: () => true,
      action: () => {}, immediate: () => true, settled: () => true });
    assert.equal(unknown.readback, 'unknown'); assert.equal(unknown.outcome, 'incomplete');
    assert.equal(count, 1);
  } finally { await rm(directory, { recursive: true, force: true }); }
});
