import test from 'node:test';
import assert from 'node:assert/strict';
import { sanitizeInventory, collectFrontend } from './frontend.mjs';
import { mkdtemp, mkdir, readFile, readdir, rm } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

test('asset inventory retains delivered identities and strips URL credentials and SVG contents', () => {
  const result=sanitizeInventory({id:'inventory-1',pageUrl:'https://example.test/home?token=PRIVATE_TOKEN',summary:{totalCount:1},
    assets:[{id:'asset-1',kind:'script',name:'index.js',url:'https://user:PRIVATE_PASSWORD@example.test/index.js?signature=PRIVATE_SIGN',sources:[{kind:'attribute',property:'src',nodeId:44}]}],
    inlineSvgs:[{id:'svg-1',markup:'PRIVATE_CONTENT'}]});
  assert.equal(result.assets[0].id,'asset-1');
  assert.deepEqual(result.inlineSvgIds,['svg-1']);
  assert.equal(JSON.stringify(result).includes('PRIVATE'),false);
  assert.equal(result.assets[0].sources[0].nodeId,undefined);
});

test('origin departure during asset collection writes no frontend artifact', async () => {
  const output = fileURLToPath(new URL('../../output/browser-inspection/', import.meta.url));
  await mkdir(output, { recursive: true });
  const directory = await mkdtemp(output + 'test-frontend-');
  await mkdir(directory + '/artifacts');
  let current = 'https://example.test/home';
  const tab = { url: async () => current, playwright: { evaluate: async () => ({ title: 'Home', controls: [], frames: [] }) } };
  const pageAssets = { list: async () => { current = 'https://outside.test/'; return { id: 'inventory', assets: [], inlineSvgs: [] }; } };
  try {
    await assert.rejects(collectFrontend({ tab, pageAssets, runDirectory: directory, label: 'home', allowedOrigin: 'https://example.test' }), /Origin changed/);
    assert.deepEqual(await readdir(directory + '/artifacts'), []);
  } finally { await rm(directory, { recursive: true }); }
});

test('inventory summary preserves only documented aggregate counts', () => {
  const summary = {totalCount:7,inlineSvgCount:0,byKind:{script:1,other:0,font:1,image:3,stylesheet:1,video:1,
    PRIVATE_KIND:'PRIVATE_VALUE',unknownCount:1}, raw:'PRIVATE_SUMMARY', credentials:{token:'PRIVATE_TOKEN'}};
  const result=sanitizeInventory({id:'inventory-1',pageUrl:'https://example.test/home',summary});
  assert.deepEqual(result.summary,{totalCount:7,inlineSvgCount:0,byKind:{script:1,other:0,font:1,image:3,stylesheet:1,video:1}});
  assert.equal(JSON.stringify(result).includes('PRIVATE'),false);
  summary.byKind.image=99;
  assert.equal(result.summary.byKind.image,3);
});

test('inventory count allowlist rejects coercions, invalid counts and unknown fields', () => {
  const result=sanitizeInventory({id:'inventory',pageUrl:'https://example.test/',summary:{
    totalCount:'PRIVATE_COUNT',inlineSvgCount:-1,unknownCount:4,
    byKind:{script:NaN,other:Infinity,font:-1,image:1.5,stylesheet:'2',video:{value:'PRIVATE_VALUE'}},
  }});
  assert.deepEqual(result.summary,{byKind:{}});
  for (const summary of [null,undefined,'PRIVATE_RAW',[1,2]]) {
    assert.deepEqual(sanitizeInventory({pageUrl:'https://example.test/',summary}).summary,{});
  }
});

test('persisted frontend artifact omits raw summary fields and credential paths', async () => {
  const output=fileURLToPath(new URL('../../output/browser-inspection/',import.meta.url));
  await mkdir(output,{recursive:true});
  const directory=await mkdtemp(output+'test-frontend-redaction-');
  await mkdir(directory+'/artifacts');
  const pageUrl='https://example.test/home';
  const tab={url:async()=>pageUrl,playwright:{evaluate:async()=>({title:'Home',controls:[],frames:[]})}};
  const pageAssets={list:async()=>({id:'inventory',pageUrl,assets:[{id:'asset',kind:'other',
    url:'https://example.test/signed/PRIVATE_SHORT_PATH'}],summary:{totalCount:1,inlineSvgCount:0,
      byKind:{other:1,PRIVATE_KIND:4},raw:'PRIVATE_RAW',signedUrl:'https://example.test/invite/PRIVATE_INVITE'}})};
  try {
    const result=await collectFrontend({tab,pageAssets,runDirectory:directory,label:'home',allowedOrigin:'https://example.test'});
    const bytes=await readFile(directory+'/'+result.path,'utf8');
    assert.equal(bytes.includes('PRIVATE'),false);
    assert.deepEqual(JSON.parse(bytes).inventory.summary,{totalCount:1,inlineSvgCount:0,byKind:{other:1}});
  } finally { await rm(directory,{recursive:true}); }
});
