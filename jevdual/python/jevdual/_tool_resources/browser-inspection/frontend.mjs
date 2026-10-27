import { open, realpath } from 'node:fs/promises';
import { resolve, relative, isAbsolute, join } from 'node:path';
import { createHash } from 'node:crypto';
import { safeText, safeUrl } from './redaction.mjs';

function inventorySummary(value) {
  // PageAssetsTabCapability.list() exposes only these aggregate counts, not bundle() metadata.
  const result = {};
  if (!value || typeof value !== 'object' || Array.isArray(value)) return result;
  const count = n => Number.isSafeInteger(n) && n >= 0;
  for (const key of ['totalCount', 'inlineSvgCount']) {
    if (!Object.hasOwn(value, key)) continue;
    const n = value[key];
    if (count(n)) result[key] = n;
  }
  const byKind = Object.hasOwn(value, 'byKind') ? value.byKind : undefined;
  if (byKind && typeof byKind === 'object' && !Array.isArray(byKind)) {
    result.byKind = {};
    for (const key of ['script', 'other', 'font', 'image', 'stylesheet', 'video']) {
      if (!Object.hasOwn(byKind, key)) continue;
      const n = byKind[key];
      if (count(n)) result.byKind[key] = n;
    }
  }
  return result;
}

export function sanitizeInventory(inventory) {
  return {
    inventoryId: safeText(inventory.id, 100), pageUrl: safeUrl(inventory.pageUrl),
    summary: inventorySummary(inventory.summary),
    assets: (inventory.assets ?? []).map(asset => ({ id: safeText(asset.id, 100), kind: safeText(asset.kind, 40),
      name: safeText(asset.name, 160), url: safeUrl(asset.url),
      sources: (asset.sources ?? []).map(source => ({kind: safeText(source.kind, 40),
        ...(source.property ? {property: safeText(source.property, 80)} : {})})) })),
    // SVG markup can embed document content or URLs. Retain identity/count only.
    inlineSvgIds: (inventory.inlineSvgs ?? []).map(svg => safeText(svg.id, 100)),
  };
}

/** Read rendered DOM only, through the caller's existing permitted browser adapter. */
export async function collectFrontend({ tab, pageAssets, runDirectory, label, allowedOrigin }) {
  if (!/^[\w-]{1,100}$/.test(label ?? '')) throw new Error('Safe artifact label required');
  if (new URL(await tab.url()).origin !== allowedOrigin) throw new Error('Frontend inventory is outside declared origin');
  const root = await realpath(runDirectory);
  const artifacts = await realpath(join(root, 'artifacts'));
  const rel = relative(root, artifacts);
  if (!rel || rel.startsWith('..') || isAbsolute(rel)) throw new Error('Artifact directory escapes run');
  const dom = await tab.playwright.evaluate(() => {
    const visible = element => {
      const rect = element.getBoundingClientRect();
      const style = window.getComputedStyle(element);
      return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
    };
    const counts = {};
    for (const el of document.querySelectorAll('*')) counts[el.tagName.toLowerCase()] = (counts[el.tagName.toLowerCase()] ?? 0) + 1;
    const controls = Array.from(document.querySelectorAll('button,a,input,textarea,select,[role],[contenteditable]')).filter(visible).slice(0, 500).map(el => ({
      tag: el.tagName.toLowerCase(), role: el.getAttribute('role'), type: el.getAttribute('type'),
      accessibleLabel: el.getAttribute('aria-label'), text: el.matches('button,a') ? el.textContent?.trim().slice(0, 200) : undefined,
      contentEditable: el.getAttribute('contenteditable'), disabled: el.hasAttribute('disabled') || el.getAttribute('aria-disabled') === 'true',
      href: el.matches('a') ? el.getAttribute('href') : undefined,
      // Never record field values, file paths, style-rule text or arbitrary DOM data attributes.
    }));
    return { title: document.title, counts, controls,
      controlLimit: 500, controlsTruncated: document.querySelectorAll('button,a,input,textarea,select,[role],[contenteditable]').length > 500,
      frames: Array.from(document.querySelectorAll('iframe')).map(el => ({title: el.getAttribute('title'), src: el.getAttribute('src')})),
      editorSurfaces: document.querySelectorAll('[contenteditable="true"],[role="textbox"],textarea').length,
      viewport: {width: window.innerWidth, height: window.innerHeight, devicePixelRatio: window.devicePixelRatio},
      limitation: 'DOM inventory excludes closed shadow roots and iframe contents; geometry-visible can include offscreen elements',
    };
  });
  const url = await tab.url();
  if (new URL(url).origin !== allowedOrigin) throw new Error('Origin changed during frontend inventory');
  const sanitizeLink = link => { try { return safeUrl(new URL(link, url).href); } catch { return '[INVALID_URL]'; } };
  const safeDom = { ...dom, title: safeText(dom.title),
    controls: dom.controls.map(control => ({...control, accessibleLabel: safeText(control.accessibleLabel), text: safeText(control.text), href: control.href ? sanitizeLink(control.href) : undefined})),
    frames: dom.frames.map(frame => ({title: safeText(frame.title), src: frame.src ? sanitizeLink(frame.src) : undefined})),
  };
  const inventory = sanitizeInventory(await pageAssets.list());
  if (new URL(await tab.url()).origin !== allowedOrigin) throw new Error('Origin changed during asset inventory');
  const result = {schemaVersion:1,type:'frontend_inventory',capturedAt:new Date().toISOString(),url:safeUrl(url),dom:safeDom,inventory};
  const bytes = Buffer.from(JSON.stringify(result,null,2)+'\n');
  const name = `${label}.frontend.json`;
  const handle = await open(resolve(artifacts,name), 'wx', 0o600);
  try { await handle.writeFile(bytes); await handle.sync(); } finally { await handle.close(); }
  return {path:`artifacts/${name}`,bytes:bytes.length,sha256:createHash('sha256').update(bytes).digest('hex'),
    assetCount:inventory.assets.length,controlCount:safeDom.controls.length};
}
