import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { checkPublication } from './publication-gate.mjs';

const run = (root, ...args) => execFileSync('git', args, { cwd: root, encoding: 'utf8' }).trim();
async function repoFixture() {
  const root = await mkdtemp(path.join(os.tmpdir(), 'footwork-publication-'));
  run(root, 'init', '-q');
  run(root, 'config', 'user.name', 'Fixture');
  run(root, 'config', 'user.email', 'fixture@example.test');
  await mkdir(path.join(root, 'output'));
  await writeFile(path.join(root, '.git', 'info', 'exclude'), '/output/\n');
  const policyPath = path.join(root, 'output', 'policy.txt');
  await writeFile(policyPath, 'PrivateTarget\n');
  await writeFile(path.join(root, 'readme.md'), 'generic baseline\n');
  run(root, 'add', 'readme.md'); run(root, 'commit', '-qm', 'baseline');
  return { root, policyPath, base: run(root, 'rev-parse', 'HEAD') };
}

test('clean proposed range passes and missing private policy fails closed', async () => {
  const f = await repoFixture();
  try {
    await writeFile(path.join(f.root, 'readme.md'), 'generic update\n');
    run(f.root, 'commit', '-qam', 'generic update');
    assert.deepEqual(await checkPublication({ repo: f.root, base: f.base, policyPath: f.policyPath }), {
      safeToPublish: true, scannedCommits: 1, trackedHits: 0, historyCommitsWithHits: 0, messageHits: 0,
    });
    await assert.rejects(checkPublication({ repo: f.root, base: f.base, policyPath: path.join(f.root, 'missing') }));
  } finally { await rm(f.root, { recursive: true, force: true }); }
});

test('deleted historical content and current tracked content both block publication without echoing token', async () => {
  const f = await repoFixture();
  try {
    await writeFile(path.join(f.root, 'readme.md'), 'mentions PrivateTarget\n');
    run(f.root, 'commit', '-qam', 'temporary note');
    await writeFile(path.join(f.root, 'readme.md'), 'generic again\n');
    run(f.root, 'commit', '-qam', 'remove note');
    const history = await checkPublication({ repo: f.root, base: f.base, policyPath: f.policyPath });
    assert.equal(history.safeToPublish, false);
    assert.equal(history.trackedHits, 0);
    assert.equal(history.historyCommitsWithHits, 1);
    assert(!JSON.stringify(history).includes('PrivateTarget'));
    await writeFile(path.join(f.root, 'readme.md'), 'PRIVATEtarget again\n');
    run(f.root, 'commit', '-qam', 'new note');
    const current = await checkPublication({ repo: f.root, base: f.base, policyPath: f.policyPath });
    assert.equal(current.trackedHits, 1);
    assert.equal(current.safeToPublish, false);
  } finally { await rm(f.root, { recursive: true, force: true }); }
});
