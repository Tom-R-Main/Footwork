#!/usr/bin/env node
// Manual calibration against public, unauthenticated websites. No shared Chrome attachment.
import { createRequire } from 'node:module';
import { randomUUID } from 'node:crypto';
import { open } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createCapture } from '../browser-inspection/capture.mjs';
import { createPlaywrightCdpBridge, writeEnvelopeArtifact } from '../inspection-transport/playwright-cdp-bridge.mjs';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const site = process.argv[2];
const packageDirectory = process.env.PLAYWRIGHT_PACKAGE_DIR;
if (!['todo', 'graphql', 'websocket'].includes(site) || !path.isAbsolute(packageDirectory || '')) {
  throw new Error('Usage: PLAYWRIGHT_PACKAGE_DIR=/absolute/path/to/node_modules node live-public-smoke.mjs todo|graphql|websocket');
}
const require = createRequire(path.join(packageDirectory, 'playwright', 'package.json'));
const { chromium } = require('playwright');
const scenarios = {
  todo: { url: 'https://demo.playwright.dev/todomvc/', origin: 'https://demo.playwright.dev' },
  graphql: { url: 'https://rickandmortyapi.com/documentation', origin: 'https://rickandmortyapi.com', graphqlPath: '/graphql', allowedOperations: ['PublicCharacter'] },
  websocket: { url: 'https://echo.websocket.org/.ws', origin: 'https://echo.websocket.org' },
};
const scenario = scenarios[site];
const marker = `footwork-calibration-${randomUUID().slice(0, 8)}`;
const runId = `${site}-${new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)}-${randomUUID().slice(0, 8)}`;
const executablePath = process.env.PLAYWRIGHT_CHROMIUM_PATH;
const browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}) });
let bridge, capture, started = false;
try {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();
  await page.goto(scenario.url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  bridge = await createPlaywrightCdpBridge({ page, allowedOrigin: scenario.origin, graphqlPath: scenario.graphqlPath, allowedOperations: scenario.allowedOperations });
  capture = createCapture({ tab: bridge.tab, cdp: bridge.cdp, target: bridge.target, projectRoot,
    allowedOrigin: scenario.origin, outputName: 'inspection-public-smoke', runId,
    privateDom: true, privateScreenshots: false, ownDomainLifecycle: true,
    domainsToEnable: ['Network', 'Runtime'], maxDrainPages: 100 });
  await capture.start(); started = true;
  await capture.snapshotNow({ label: 'baseline' });
  const outcome = { site, browserActions: [], renderedReadback: false, responseObserved: false, actionFailed: false };
  try {
  if (site === 'todo') {
    await capture.step({ workflowId: 'todo-local', stepId: 'add-item', intent: 'Add an inert calibration item', action: async () => {
      const input = page.getByPlaceholder('What needs to be done?');
      await input.fill(marker); await input.press('Enter');
      await page.getByText(marker, { exact: true }).waitFor({ state: 'visible' });
    } });
    outcome.browserActions.push('add-item');
    await capture.step({ workflowId: 'todo-local', stepId: 'reload-readback', intent: 'Reload and verify the item remains rendered', action: async () => {
      await page.reload({ waitUntil: 'domcontentloaded' });
      await page.getByText(marker, { exact: true }).waitFor({ state: 'visible' });
      outcome.renderedReadback = true;
    } });
    outcome.browserActions.push('reload-readback');
  } else if (site === 'graphql') {
    const result = await capture.step({ workflowId: 'graphql-public', stepId: 'named-query', intent: 'Run a public named GraphQL query from the documentation page', action: async () => page.evaluate(async () => {
      const response = await fetch('/graphql', { method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ operationName: 'PublicCharacter', query: 'query PublicCharacter { character(id: 1) { id name } }' }) });
      const json = await response.json();
      return { status: response.status, hasCharacter: Boolean(json?.data?.character?.name), hasErrors: Array.isArray(json?.errors) };
    }) });
    outcome.browserActions.push('named-query');
    outcome.responseObserved = result.status === 200 && result.hasCharacter && !result.hasErrors;
  } else {
    await capture.step({ workflowId: 'websocket-echo', stepId: 'reconnect', intent: 'Reconnect the public echo socket using rendered controls', action: async () => {
      await page.getByRole('button', { name: 'Disconnect from Server' }).click();
      await page.getByRole('button', { name: 'Connect to Server' }).click();
      await page.getByRole('button', { name: 'Disconnect from Server' }).waitFor({ state: 'visible' });
    } });
    outcome.browserActions.push('reconnect');
    await capture.step({ workflowId: 'websocket-echo', stepId: 'echo-message', intent: 'Send an inert marker and verify its echo', action: async () => {
      await page.getByRole('textbox').fill(marker);
      await page.getByRole('button', { name: 'Send Message' }).click();
      for (let attempt = 0; attempt < 40; attempt++) {
        const snapshot = await page.locator('body').ariaSnapshot();
        if (snapshot.includes(`[recv] ${marker}`)) { outcome.renderedReadback = true; break; }
        await page.waitForTimeout(250);
      }
      if (!outcome.renderedReadback) throw new Error('Echo was not visible in the accessibility snapshot');
    } });
    outcome.browserActions.push('echo-message');
  }
  } catch { outcome.actionFailed = true; }
  await capture.snapshotNow({ label: 'settled' });
  const artifact = await writeEnvelopeArtifact({ runDirectory: capture.status().directory, bridge });
  const reportHandle = await open(path.join(capture.status().directory, 'artifacts', 'outcome.json'), 'wx', 0o600);
  try { await reportHandle.writeFile(`${JSON.stringify(outcome)}\n`); await reportHandle.sync(); }
  finally { await reportHandle.close(); }
  await capture.stop(); started = false;
  console.log(JSON.stringify({ runDirectory: capture.status().directory, capture: capture.status().counts, artifact: { count: artifact.count, coverage: artifact.coverage }, outcome }));
  if (outcome.actionFailed) process.exitCode = 1;
} finally {
  if (started) { try { await capture.stop(); } catch { /* Preserve original failure; capture already records cleanup. */ } }
  if (bridge) { try { await bridge.close(); } catch { /* Browser cleanup follows. */ } }
  await browser.close();
}
