import test from 'node:test';
import assert from 'node:assert/strict';
import { sanitizeInventory, collectFrontend } from './frontend.mjs';
import { mkdtemp, mkdir, readdir, rm } from 'node:fs/promises';
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
