import { createRequire } from 'node:module';
import { mkdir, writeFile, access } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
import path from 'node:path';

const require = createRequire(import.meta.url);
const { chromium } = require('/Users/frigidcrow/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root = '/Users/frigidcrow/Documents/dafeiyu/architecture';
const evidence = path.join(root, 'verification');
await mkdir(evidence, { recursive: true });
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1500, height: 1100 }, deviceScaleFactor: 1 });
const errors = [];
const network = [];
page.on('pageerror', err => errors.push(String(err)));
page.on('request', req => { if (/^https?:/.test(req.url())) network.push(req.url()); });
const report = { views: [], errors, externalRequests: network };
try {
  await page.goto(pathToFileURL(path.join(root, '架构图.html')).href);
  for (const view of ['product', 'runtime', 'flows', 'deployment']) {
    await page.locator(`[data-view="${view}"]`).click();
    const panel = page.locator(`#view-${view}`);
    if (!await panel.isVisible()) throw new Error(`Panel hidden: ${view}`);
    if (await page.locator('.view:visible').count() !== 1) throw new Error('Multiple visible panels');
    const href = await page.locator('#download').getAttribute('href');
    if (href !== `diagrams/${view}.svg`) throw new Error(`Wrong download: ${href}`);
    await access(path.join(root, href));
    const nodes = panel.locator('[data-node]');
    let checked = 0;
    for (let i = 0; i < await nodes.count(); i++) {
      const node = nodes.nth(i);
      await node.click();
      const title = await page.locator('#detail-title').textContent();
      const expected = (await node.getAttribute('aria-label')).replace(/：查看职责与边界$/, '');
      if (title !== expected) throw new Error(`Detail mismatch ${view}: ${title} != ${expected}`);
      checked++;
    }
    await nodes.first().focus();
    await page.keyboard.press('Enter');
    const textOverflows = await panel.evaluate(el => [...el.querySelectorAll('.node')].flatMap(g => {
      const rect = g.querySelector('rect').getBBox();
      return [...g.querySelectorAll('text')].flatMap(t => {
        const b = t.getBBox();
        return b.x < rect.x + 3 || b.y < rect.y + 3 || b.x + b.width > rect.x + rect.width - 3 || b.y + b.height > rect.y + rect.height - 3
          ? [{ node: g.dataset.node, text: t.textContent, bbox: [b.x, b.y, b.width, b.height], rect: [rect.x, rect.y, rect.width, rect.height] }]
          : [];
      });
    }));
    report.views.push({ view, checkedNodes: checked, textOverflows });
    await page.screenshot({ path: path.join(evidence, `${view}-desktop.png`), fullPage: true });
  }
  await page.locator('[data-view="product"]').click();
  await page.setViewportSize({ width: 390, height: 844 });
  report.mobile = await page.evaluate(() => ({ viewport: innerWidth, documentWidth: document.documentElement.scrollWidth }));
  await page.screenshot({ path: path.join(evidence, 'mobile.png'), fullPage: true });
  const exportPage = await browser.newPage({ viewport: { width: 1440, height: 1200 }, deviceScaleFactor: 1 });
  for (const view of ['product', 'runtime', 'flows', 'deployment']) {
    await exportPage.goto(pathToFileURL(path.join(root, 'diagrams', `${view}.svg`)).href);
    await exportPage.locator('svg').screenshot({ path: path.join(root, 'diagrams', `${view}.png`) });
  }
  report.passed = !errors.length && !network.length && report.views.every(x => !x.textOverflows.length) && report.mobile.documentWidth <= report.mobile.viewport + 1;
  await writeFile(path.join(evidence, 'browser-check.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  if (!report.passed) process.exitCode = 1;
} finally {
  await browser.close();
}
