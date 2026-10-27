import { open, readFile } from 'node:fs/promises';
import path from 'node:path';

const safeId = value => typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$/.test(value);
async function check(callback) {
  if (typeof callback !== 'function') return 'unknown';
  try {
    const value = await callback();
    return value === true ? 'passed' : value === false ? 'failed' : 'unknown';
  } catch { return 'failed'; }
}

/** One action, then an independently recorded reload/readback action if supplied. */
export function createWorkflowObserver({ capture, runDirectory } = {}) {
  if (!capture?.step || !runDirectory) throw new Error('Recorder and private run directory required');
  const receipts = [];
  return {
    async run({ workflowId, stepId, intent, precondition, action, immediate, settled, readback } = {}) {
      if (!safeId(workflowId) || !safeId(stepId) || stepId.length > 71 || typeof action !== 'function') throw new Error('Safe IDs and one action required');
      if (receipts.some(row => row.stepId === stepId)) throw new Error('Step ID already observed');
      const receipt = { workflowId, stepId, precondition: await check(precondition), action: 'not-run',
        immediate: 'unknown', settled: 'unknown', readback: 'unknown', outcome: 'incomplete' };
      receipts.push(receipt);
      if (receipt.precondition !== 'passed') return { ...receipt };
      try {
        await capture.step({ workflowId, stepId, intent, action: async () => {
          await action();
          receipt.immediate = await check(immediate);
          receipt.settled = await check(settled);
        } });
        receipt.action = 'completed';
      } catch { receipt.action = 'failed'; return { ...receipt }; }
      if (typeof readback === 'function') {
        try {
          await capture.step({ workflowId, stepId: `${stepId}-readback`, intent: 'Independent readback',
            action: async () => { receipt.readback = await check(readback); } });
        } catch { receipt.readback = 'failed'; }
      }
      receipt.outcome = [receipt.immediate, receipt.settled, receipt.readback].every(value => value === 'passed') ? 'verified' : 'incomplete';
      return { ...receipt };
    },
    receipts: () => receipts.map(row => ({ ...row })),
    async writeArtifact({ label = 'workflow-checkpoints' } = {}) {
      if (!safeId(label)) throw new Error('Safe artifact label required');
      try { await readFile(path.join(runDirectory, 'manifest.json')); throw new Error('Run is already sealed'); }
      catch (error) { if (error.code !== 'ENOENT') throw error; }
      const filename = path.join(runDirectory, 'artifacts', `${label}.json`);
      const handle = await open(filename, 'wx', 0o600);
      try { await handle.writeFile(`${JSON.stringify({ schemaVersion: 1, kind: 'workflow-checkpoints', receipts })}\n`); await handle.sync(); }
      finally { await handle.close(); }
      return { path: filename, count: receipts.length };
    },
  };
}
