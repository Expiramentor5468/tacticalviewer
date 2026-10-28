const test = require('node:test');
const assert = require('node:assert/strict');
const { dateValue, safeUrl, normalizeFeed, filterFeeds } = require('../app.js');
const now = Date.parse('2026-10-27T12:00:00Z');
const filters = { q: '', competition: 'all', type: 'all', territory: 'all', status: 'all', availability: 'all', range: '30' };

test('unknown, invalid and past kickoff do not enter upcoming results', () => {
  const rows = [{ kickoff: null }, { kickoff: 'bad' }, { kickoff: '2026-10-26T12:00:00Z' }, { kickoff: '2026-10-28T12:00:00Z' }];
  assert.equal(filterFeeds(rows, filters, now).length, 1);
  assert.equal(filterFeeds(rows, { ...filters, range: 'all' }, now).length, 4);
});

test('bundled legacy claims do not bypass public-access verification', () => {
  const f = normalizeFeed({ status: 'confirmed', usAvailability: true, access: 'free' }, now);
  assert.equal(f.status, 'candidate'); assert.equal(f.usAvailability, null); assert.equal(f.access, 'unknown');
});

test('production listings cannot enter US watchable filter', () => {
  assert.equal(filterFeeds([{ status: 'production', usAvailability: true }], { ...filters, range: 'all', availability: 'us' }, now).length, 0);
});

test('safe URL and date handling', () => {
  assert.equal(safeUrl('javascript:alert(1)'), ''); assert.equal(dateValue('bad'), null);
  assert.equal(dateValue('2026-10-27T12:00:00'), null);
});

test('confirmed feeds require public territory but not a particular audio language', () => {
  const base = {
    status: 'confirmed', exactFixtureVerified: true, publicAccessConfirmed: true,
    kickoff: '2026-10-28T12:00:00Z', verifiedAt: '2026-10-27T10:00:00Z',
    sourceUrl: 'https://example.com/source', watchUrl: 'https://example.com/watch',
    platform: 'Example', territories: ['Germany'], access: 'subscription'
  };
  assert.equal(normalizeFeed({ ...base, language: 'English' }, now).status, 'confirmed');
  assert.equal(normalizeFeed({ ...base, language: 'Italian' }, now).status, 'confirmed');
  assert.equal(normalizeFeed({ ...base, language: 'Unknown', commentary: 'No commentary / raw video' }, now).status, 'confirmed');
  assert.equal(normalizeFeed({ ...base, territories: [] }, now).status, 'candidate');
});

test('territory filter is exact and global', () => {
  const rows = [
    { kickoff: '2026-10-28T12:00:00Z', territories: ['United Kingdom', 'Republic of Ireland'] },
    { kickoff: '2026-10-29T12:00:00Z', territories: ['United States'] },
  ];
  assert.equal(filterFeeds(rows, { ...filters, territory: 'Republic of Ireland' }, now).length, 1);
  assert.equal(filterFeeds(rows, { ...filters, territory: 'United States' }, now).length, 1);
  assert.equal(filterFeeds(rows, { ...filters, territory: 'Germany' }, now).length, 0);
});
