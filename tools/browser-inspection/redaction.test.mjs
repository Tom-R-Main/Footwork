import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, rm } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { resolve, join } from 'node:path';
import { safeUrl, eventMetadata } from './redaction.mjs';
import { createCapture } from './capture.mjs';

const ORIGIN = 'https://example.test';
const credentialUrls = [
  `${ORIGIN}/reset/01234567-89ab-4cde-8fab-0123456789ab`,
  `${ORIGIN}/files/0123456789abcdef0123456789abcdef`,
  `${ORIGIN}/files/abcdefghijklmnopqrstuvwxyzabcdef`,
  `${ORIGIN}/files/abcdefghijklmnopqrstuvwxyz012345`,
  `${ORIGIN}/files/AbcdefGHIJKLMNOPQRSTuvwxyz0123456`,
  `${ORIGIN}/invite/ShortInvite7`,
  `${ORIGIN}/reset-password/short-reset-value`,
  `${ORIGIN}/password/reset/shortReset7`,
  `${ORIGIN}/invitations/accept/shortInvitation7`,
  `${ORIGIN}/magic-link/shortMagic7`,
  `${ORIGIN}/signed/ShortSigned7/download`,
  `${ORIGIN}/api/token/ShortToken7`,
  `${ORIGIN}/%69%6e%76%69%74%65/EncodedInvite7`,
  `${ORIGIN}/invite%2FEncodedBoundary7`,
];

for (const url of credentialUrls) {
  test(`credential path omitted from metadata: ${new URL(url).pathname}`, () => {
    const credential = decodeURIComponent(new URL(url).pathname).split('/').find(segment =>
      /01234567|short|encoded/i.test(segment) || /^[\w-]{32,}$/.test(segment));
    const output = safeUrl(url);
    assert.equal(output.includes(credential), false);
    const metadata = eventMetadata({method:'Network.requestWillBeSent',params:{
      request:{url,method:'GET'}, initiator:{url}, redirectResponse:{url,status:302},
    }});
    assert.equal(JSON.stringify(metadata).includes(credential), false);
  });
}

test('known noncredential route structure stays available', () => {
  for (const path of ['/projects/alpha-1/assets/app.js', '/projects/mixed-Case-1/assets/app.js', '/docs/password-reset', '/home', '/api/reports/2026-10-10']) {
    assert.equal(safeUrl(ORIGIN + path), ORIGIN + path);
  }
});

test('credential path strings never reach persisted capture journals', async () => {
  let pending = [];
  let cursor = 0;
  const capture = createCapture({projectRoot:resolve(import.meta.dirname,'../..'), allowedOrigin:ORIGIN,
    runId:`test-path-redaction-${randomUUID()}`, ownDomainLifecycle:true,
    tab:{url:async()=>ORIGIN}, cdp:{send:async()=>({}),readEvents:async()=>{
      const events = pending; pending = []; cursor += events.length;
      return {cursor,events,hasMore:false,truncated:false};
    }}});
  await capture.start();
  try {
    pending = credentialUrls.map((url,index)=>({sequence:index+1,method:'Network.requestWillBeSent',
      params:{requestId:`request-${index}`,request:{url,method:'GET'}}}));
    await capture.drain();
  } finally { await capture.stop(); }
  const directory = capture.status().directory;
  try {
    const journal = await readFile(join(directory,'events.jsonl'),'utf8');
    assert.equal(journal.trim().split('\n').length, credentialUrls.length);
    for (const url of credentialUrls) {
      const credential = decodeURIComponent(new URL(url).pathname).split('/').find(segment =>
        /01234567|short|encoded/i.test(segment) || /^[\w-]{32,}$/.test(segment));
      assert.equal(journal.includes(credential), false);
    }
  } finally { await rm(directory,{recursive:true}); }
});
