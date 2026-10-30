const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '..');
const NOW = Date.parse('2026-10-30T14:00:00Z');

function snapshot() {
  const base = { id: 'verified', match: 'A vs B', competition: 'UEFA Champions League', kickoff: '2026-11-03T20:00:00Z', type: 'alternate', status: 'confirmed', exactFixtureVerified: true, publicAccessConfirmed: true, verifiedAt: '2026-10-30T10:00:00Z', platform: 'Example', territories: ['United Kingdom'], access: 'subscription', sourceUrl: 'https://example.com/source', watchUrl: 'https://example.com/watch', secondarySourceUrl: 'https://example.com/details', policySourceUrl: 'https://example.com/policy', fixtureSourceUrl: 'https://example.com/fixture' };
  return { schemaVersion: 2, updatedAt: '2026-10-30T10:00:00Z', lastSuccessfulScanAt: '2026-10-30T10:00:00Z', scanStatus: 'ok', sourceHealth: [{ source: 'example', ok: true }], feeds: [base, { ...base, id: 'production', match: 'C vs D', competition: 'Bundesliga', type: 'tactical', status: 'production', publicAccessConfirmed: false }, { id: 'lead', match: 'Undated lead', competition: 'MLS', status: 'candidate', kickoff: null, type: 'ref', sourceUrl: 'https://example.com/lead' }] };
}

async function pageWith(t, { bundled = snapshot(), remote = snapshot() } = {}) {
  const browser = await chromium.launch({ headless: true });
  t.after(() => browser.close());
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(now => { Date.now = () => now; }, NOW);
  await page.route('**/*', route => {
    const url = new URL(route.request().url());
    if (url.hostname === 'raw.githubusercontent.com') return route.fulfill({ json: remote });
    const file = url.pathname.split('/').pop() || 'index.html';
    if (file === 'data.js') return route.fulfill({ contentType: 'application/javascript', body: 'window.TACTICAL_FEED_DATA = ' + JSON.stringify(bundled) + ';' });
    const types = { 'index.html': 'text/html', 'app.js': 'application/javascript', 'styles.css': 'text/css' };
    if (!types[file]) return route.abort();
    return route.fulfill({ contentType: types[file], body: fs.readFileSync(path.join(root, file), 'utf8') });
  });
  await page.goto('https://watchlist.test/');
  await page.waitForLoadState('networkidle');
  return { page, errors };
}

test('real page renders evidence, filters leads and keeps access claims separate', async t => {
  const { page, errors } = await pageWith(t);
  assert.equal(await page.locator('.feed-card').count(), 1);
  for (const label of ['Source evidence', 'Fixture schedule', 'Access policy', 'Product / access details']) {
    assert.equal(await page.locator('.feed-card .source-link').filter({ hasText: label }).count(), 1);
  }
  await page.locator('.quick-row [data-preset="tactical"]').click();
  assert.equal(await page.locator('.feed-card').count(), 0);
  await page.locator('.quick-row [data-preset="leads"]').click();
  assert.equal(await page.locator('.feed-card').count(), 3);
  await page.selectOption('#status', 'production');
  assert.equal(await page.locator('.feed-card').count(), 1);
  assert.equal(await page.locator('.feed-card .watch-link').count(), 0);
  await page.locator('.quick-row [data-preset="us"]').click();
  assert.equal(await page.locator('.feed-card').count(), 0);
  assert.deepEqual(errors, []);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
});

test('malformed remote data preserves the rendered bundled snapshot', async t => {
  const remote = { ...snapshot(), updatedAt: '2026-10-30T11:00:00Z', sourceHealth: {} };
  const { page, errors } = await pageWith(t, { remote });
  assert.match(await page.locator('#dataNotice').innerText(), /last usable snapshot/);
  assert.equal(await page.locator('.feed-card').count(), 1);
  assert.match(await page.locator('.feed-card h3').innerText(), /A vs B/);
  assert.deepEqual(errors, []);
});

test('a damaged bundle can recover from a valid remote snapshot', async t => {
  const { page, errors } = await pageWith(t, { bundled: { feeds: [] } });
  assert.equal(await page.locator('.feed-card').count(), 1);
  assert.equal(await page.locator('#updateLabel').innerText(), 'Discovery scan current');
  assert.deepEqual(errors, []);
});

test('failed source health overrides an incorrect overall success label', async t => {
  const data = snapshot();
  data.sourceHealth[0].ok = false;
  const { page, errors } = await pageWith(t, { bundled: data, remote: data });
  assert.equal(await page.locator('#updateLabel').innerText(), 'Check freshness');
  assert.match(await page.locator('#dataNotice').innerText(), /could not reach every source/);
  assert.equal(await page.locator('.feed-card').count(), 1);
  assert.deepEqual(errors, []);
});
