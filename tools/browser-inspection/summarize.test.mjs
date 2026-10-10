import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import { join } from 'node:path';
import { createHash } from 'node:crypto';
import { analyze, verifyManifest, contained } from './summarize.mjs';

const event = (method, sequence, params, source = {tabId:1}) => ({event:{method,sequence,params,source}});

test('redirect hops and identical IDs on different targets remain distinct', () => {
  const result = analyze({events:[
    event('Network.requestWillBeSent',1,{requestId:'r',request:{method:'GET',url:'https://studio.symbolic.ai/a?secret=hidden'}}),
    event('Network.requestWillBeSent',2,{requestId:'r',redirectResponse:{status:302},request:{method:'GET',url:'https://studio.symbolic.ai/b'}}),
    event('Network.requestWillBeSent',3,{requestId:'r',request:{method:'POST',url:'https://studio.symbolic.ai/c'}},{tabId:1,sessionId:'child'}),
    event('Network.responseReceived',4,{requestId:'r',response:{status:200}}),
    event('Network.loadingFinished',5,{requestId:'r'}),
  ]});
  assert.equal(result.requests.length,3);
  assert.equal(result.requests[0].status,302);
  assert.equal(result.requests[0].redirect,true);
  assert.equal(result.requests[1].status,200);
  assert.equal(result.requests[2].status,null);
  assert.equal(JSON.stringify(result).includes('hidden'),false);
});

test('incomplete steps and request failures are not reported as successful effects', () => {
  const result = analyze({events:[
    event('Network.requestWillBeSent',8,{requestId:'r',request:{method:'POST',url:'https://studio.symbolic.ai/api'}}),
    event('Network.loadingFailed',9,{requestId:'r'}),
  ],actions:[{type:'step_begin',stepId:'1',cursorBefore:7},{type:'step_end',stepId:'1',cursorAfter:10,status:'failed'},
    {type:'step_begin',stepId:'2',cursorBefore:10}]});
  assert.equal(result.steps[0].associatedRequests.length,1);
  assert.equal(result.steps[0].acknowledgement,'not-evaluated');
  assert.equal(result.steps[1].status,'incomplete');
  assert.equal(result.endpoints[0].failures,1);
});

test('manifest detects tampering and path escape', async () => {
  const root=resolve(import.meta.dirname,'../../output/browser-inspection');
  await mkdir(root,{recursive:true});
  const dir = await mkdtemp(join(root,'digest-test-'));
  try {
    const bytes=Buffer.from('{}\n');
    for(const name of ['events.jsonl','actions.jsonl','gaps.jsonl','bodies.jsonl']) await writeFile(join(dir,name),bytes);
    const files=['events.jsonl','actions.jsonl','gaps.jsonl','bodies.jsonl'].map(path=>({path,bytes:bytes.length,sha256:createHash('sha256').update(bytes).digest('hex')}));
    assert.equal((await verifyManifest(dir,{files})).verified,true);
    await writeFile(join(dir,'events.jsonl'),'changed');
    const result=await verifyManifest(dir,{files:[...files,{path:'../escape',sha256:'x'}]});
    assert.equal(result.verified,false);
    assert(result.errors.some(e=>e.includes('Hash mismatch')));
    assert(result.errors.some(e=>e.includes('escapes')));
    assert.equal(contained(dir,join(dir,'../other')),false);
  } finally { await rm(dir,{recursive:true,force:true}); }
});
