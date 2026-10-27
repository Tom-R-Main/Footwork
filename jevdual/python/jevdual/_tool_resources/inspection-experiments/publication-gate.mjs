#!/usr/bin/env node
// Local-only pre-push review. Keep the policy file ignored and never print its contents.
import { readFile, realpath } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

function git(repo, args, allowNoMatch = false) {
  const result = spawnSync('git', args, { cwd: repo, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
  if (result.error || (result.status !== 0 && !(allowNoMatch && result.status === 1))) throw new Error('Git publication scan failed');
  return { status: result.status, output: result.stdout };
}

export async function checkPublication({ repo, base, policyPath }) {
  if (!repo || !base || !policyPath) throw new Error('Repository, base and private policy are required');
  const policy = (await readFile(policyPath, 'utf8')).split(/\r?\n/).map(s => s.trim()).filter(s => s && !s.startsWith('#'));
  if (!policy.length || policy.some(s => s.length < 3 || s.includes('\0'))) throw new Error('Private policy has no valid search terms');
  const root = git(repo, ['rev-parse', '--show-toplevel']).output.trim();
  if (await realpath(root) !== await realpath(repo)) throw new Error('Repository root must be explicit');
  const excluded = git(repo, ['check-ignore', '-q', '--', path.resolve(policyPath)], true).status === 0;
  if (!excluded) throw new Error('Private policy must be ignored by Git');
  git(repo, ['rev-parse', '--verify', `${base}^{commit}`]);
  git(repo, ['merge-base', '--is-ancestor', base, 'HEAD']);
  const commits = git(repo, ['rev-list', '--reverse', `${base}..HEAD`]).output.trim().split('\n').filter(Boolean);
  const messages = git(repo, ['log', '--format=%H%n%B', `${base}..HEAD`]).output.toLowerCase();
  const messageHits = policy.reduce((n, term) => n + (messages.includes(term.toLowerCase()) ? 1 : 0), 0);
  const policyArgs = ['-I', '-i', '-l', '-F', '-f', path.resolve(policyPath)];
  const trackedHits = git(repo, ['grep', ...policyArgs, 'HEAD', '--'], true).output.trim().split('\n').filter(Boolean).length;
  let historyCommitsWithHits = 0;
  for (const commit of commits) {
    if (git(repo, ['grep', ...policyArgs, commit, '--'], true).status === 0) historyCommitsWithHits++;
  }
  return { safeToPublish: trackedHits === 0 && historyCommitsWithHits === 0 && messageHits === 0,
    scannedCommits: commits.length, trackedHits, historyCommitsWithHits, messageHits };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [repo, base, policyPath] = process.argv.slice(2);
  try {
    const result = await checkPublication({ repo, base, policyPath });
    console.log(JSON.stringify(result));
    if (!result.safeToPublish) process.exitCode = 2;
  } catch {
    console.error('Publication gate could not complete; publication blocked.');
    process.exitCode = 2;
  }
}
