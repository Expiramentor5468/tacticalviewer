(() => {
  'use strict';
  const PRIMARY = new Set(['UEFA Champions League', 'Premier League', 'MLS']);
  const FALLBACK = new Set(['Bundesliga', 'Serie A', 'Ligue 1']);
  const TYPES = { tactical: 'Tactical / wide', coach: 'Coach cam', ref: 'Ref cam', alternate: 'Alternate broadcast' };
  const dateValue = value => typeof value === 'string' && /(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value)) ? Date.parse(value) : null;
  const safeUrl = value => { try { const u = new URL(value); return ['https:', 'http:'].includes(u.protocol) ? u.href : ''; } catch { return ''; } };
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[c]));
  const formatDate = value => dateValue(value) === null ? 'Date not verified' : new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short' }).format(new Date(value));

  function normalizeFeed(row, now = Date.now()) {
    const f = { ...row };
    f.territories = Array.isArray(f.territories) ? f.territories.filter(x => typeof x === 'string' && x.trim()) : [];
    f.language = f.language || (/\bEnglish\b/i.test(f.commentary || '') ? 'English' : 'Unknown / not verified');
    const verified = dateValue(f.verifiedAt);
    const policyReviewed = f.policyReviewedAt == null ? verified : dateValue(f.policyReviewedAt);
    const confirmed = f.status === 'confirmed' && f.exactFixtureVerified === true && f.publicAccessConfirmed === true && dateValue(f.kickoff) !== null && verified !== null && verified <= now && verified >= now - 7 * 86400000 && policyReviewed !== null && policyReviewed <= now && policyReviewed >= now - 7 * 86400000 && safeUrl(f.sourceUrl) && safeUrl(f.watchUrl) && f.platform && f.territories.length;
    if (f.status === 'confirmed' && !confirmed) f.status = 'candidate';
    if (!['confirmed', 'candidate', 'production'].includes(f.status)) f.status = 'candidate';
    if (f.status !== 'confirmed') { f.usAvailability = null; f.access = 'unknown'; f.watchUrl = null; }
    return f;
  }

  function filterFeeds(feeds, filters, now = Date.now()) {
    return feeds.filter(f => {
      const kickoff = dateValue(f.kickoff);
      const haystack = `${f.match || ''} ${f.competition || ''} ${f.platform || ''} ${f.notes || ''} ${(f.territories || []).join(' ')} ${f.language || ''} ${f.commentary || ''}`.toLowerCase();
      if (filters.q && !haystack.includes(filters.q.toLowerCase())) return false;
      if (filters.competition !== 'all' && f.competition !== filters.competition) return false;
      if (filters.type !== 'all' && f.type !== filters.type) return false;
      if (filters.status !== 'all' && f.status !== filters.status) return false;
      if (filters.territory && filters.territory !== 'all' && !(f.territories || []).includes(filters.territory)) return false;
      if (filters.availability === 'us' && (f.status !== 'confirmed' || f.usAvailability !== true)) return false;
      if (['free', 'subscription'].includes(filters.availability) && (f.status !== 'confirmed' || f.access !== filters.availability)) return false;
      if (filters.range !== 'all' && (kickoff === null || kickoff < now || kickoff > now + Number(filters.range) * 86400000)) return false;
      return true;
    });
  }

  function validPayload(data) {
    const object = value => value && typeof value === 'object' && !Array.isArray(value);
    const text = value => typeof value === 'string' && value.trim().length > 0;
    const optionalDate = value => value == null || dateValue(value) !== null;
    const strings = ['id', 'match', 'competition', 'type', 'status', 'platform', 'language', 'commentary', 'notes', 'sourceUrl', 'watchUrl', 'secondarySourceUrl', 'policySourceUrl', 'fixtureSourceUrl', 'sourceKey', 'access'];
    return Boolean(object(data) && data.schemaVersion === 2 && dateValue(data.updatedAt) !== null &&
      ['ok', 'partial', 'failed'].includes(data.scanStatus) && optionalDate(data.lastSuccessfulScanAt) && optionalDate(data.lastAttemptAt) &&
      Array.isArray(data.feeds) && data.feeds.every(f => object(f) && ['id', 'match', 'competition'].every(k => text(f[k])) &&
        strings.every(k => f[k] == null || typeof f[k] === 'string') &&
        ['kickoff', 'verifiedAt', 'checkedAt', 'sourcePublishedAt', 'policyReviewedAt'].every(k => optionalDate(f[k])) &&
        (f.territories == null || (Array.isArray(f.territories) && f.territories.every(text)))) &&
      Array.isArray(data.sourceHealth) && data.sourceHealth.every(h => object(h) && text(h.source) && typeof h.ok === 'boolean' &&
        optionalDate(h.checkedAt) && optionalDate(h.attemptedAt)));
  }

  function evidenceLinks(feed) {
    const seen = new Set();
    return [['Source evidence', 'sourceUrl'], ['Fixture schedule', 'fixtureSourceUrl'], ['Access policy', 'policySourceUrl'], ['Product / access details', 'secondarySourceUrl']]
      .map(([label, key]) => ({ label, url: safeUrl(feed[key]) }))
      .filter(link => { if (!link.url || seen.has(link.url)) return false; seen.add(link.url); return true; });
  }

  if (typeof module !== 'undefined') module.exports = { dateValue, safeUrl, normalizeFeed, filterFeeds, validPayload, evidenceLinks };
  if (typeof document === 'undefined') return;

  const ids = ['search', 'competition', 'type', 'territory', 'availability', 'status', 'dateRange', 'sort', 'feedGrid', 'resultCount', 'emptyState', 'lastUpdated', 'updateLabel', 'dataNotice', 'featured', 'featuredSection', 'confirmedCount', 'productionCount', 'candidateCount', 'sourceHealth', 'listHeading'];
  const el = Object.fromEntries(ids.map(id => [id, document.getElementById(id)]));
  let payload = {}, feeds = [], primaryOnly = true;
  const statusLabel = { confirmed: 'Public access verified', production: 'Production only', candidate: 'Unverified lead' };

  function card(f) {
    const links = evidenceLinks(f), watch = safeUrl(f.watchUrl);
    const kickoff = dateValue(f.kickoff), old = kickoff !== null && kickoff < Date.now();
    const checked = dateValue(f.verifiedAt || f.checkedAt), stale = checked !== null && checked < Date.now() - 86400000;
    const regions = f.territories?.length ? f.territories.join(', ') : 'Not verified';
    return `<article class="feed-card">
      <div class="feed-top"><div class="card-row"><div class="competition">${esc(f.competition)}</div><div class="badges"><span class="badge ${f.status}">${statusLabel[f.status]}</span><span class="badge ${TYPES[f.type] ? f.type : 'alternate'}">${esc(TYPES[f.type] || 'Other feed')}</span></div></div>
      <h3 class="match-title">${esc(f.match)}</h3><div class="time">${kickoff === null ? 'No verified fixture time' : `${old ? 'Past listing · ' : ''}${esc(formatDate(f.kickoff))}`}</div></div>
      <div class="feed-details"><div class="detail"><span>Platform</span><strong>${esc(f.platform || 'Not verified')}</strong></div>
      <div class="detail"><span>Available in</span><strong>${esc(regions)}</strong></div>
      <div class="detail"><span>Access</span><strong>${esc({ free: 'Free', subscription: 'Subscription' }[f.access] || 'Not verified')}</strong></div>
      <div class="detail"><span>Language</span><strong>${esc(f.language || 'Unknown / not verified')}</strong></div>
      <div class="detail"><span>Commentary / audio</span><strong>${esc(f.commentary || 'Not verified; may be video-only')}</strong></div></div>
      ${f.status === 'production' ? '<p class="access-warning">Produced for broadcasters. Public carriage is not verified.</p>' : ''}
      ${f.notes ? `<p class="notes">${esc(f.notes)}</p>` : ''}
      <div class="evidence">${f.sourcePublishedAt ? `<span>Source published ${esc(formatDate(f.sourcePublishedAt))}</span>` : ''}<span>${f.verifiedAt ? 'Evidence reviewed' : 'Source fetched'}: ${checked === null ? 'not recorded' : esc(formatDate(f.verifiedAt || f.checkedAt))}${stale ? ' · recheck before watching' : ''}</span>${f.policyReviewedAt ? `<span>Access policy reviewed: ${esc(formatDate(f.policyReviewedAt))}</span>` : ''}</div>
      <div class="card-actions">${links.length ? links.map(link => `<a class="source-link" href="${esc(link.url)}" target="_blank" rel="noopener noreferrer">${esc(link.label)} ↗</a>`).join('') : '<span class="small-note">Source unavailable</span>'}${f.status === 'confirmed' && watch ? `<a class="watch-link" href="${esc(watch)}" target="_blank" rel="noopener noreferrer">Open viewing service ↗</a>` : '<span class="confidence">No verified watch link</span>'}</div></article>`;
  }

  function applyFilters() {
    const filters = { q: el.search.value.trim(), competition: el.competition.value, type: el.type.value, territory: el.territory.value, status: el.status.value, availability: el.availability.value, range: el.dateRange.value };
    let out = filterFeeds(feeds, filters), suffix = '';
    if (primaryOnly) {
      const preferred = out.filter(f => PRIMARY.has(f.competition));
      out = preferred.length ? preferred : out.filter(f => FALLBACK.has(f.competition));
      suffix = preferred.length ? ' · primary leagues' : out.length ? ' · fallback leagues' : ' · primary + fallback leagues';
    }
    const time = f => dateValue(f.kickoff) ?? Number.MAX_SAFE_INTEGER;
    const rank = f => ({ confirmed: 0, production: 1, candidate: 2 }[f.status] ?? 9);
    out.sort((a, b) => el.sort.value === 'league' ? String(a.competition).localeCompare(String(b.competition)) || time(a) - time(b) : el.sort.value === 'evidence' ? rank(a) - rank(b) || time(a) - time(b) : time(a) - time(b));
    el.feedGrid.innerHTML = out.map(card).join('');
    el.resultCount.textContent = `${out.length} listing${out.length === 1 ? '' : 's'}${suffix}`;
    el.emptyState.classList.toggle('hidden', out.length > 0);
    el.listHeading.textContent = el.status.value === 'confirmed' ? 'Verified public feeds' : 'Feed watchlist';
  }

  function preset(name) {
    primaryOnly = name === 'primary';
    el.search.value = ''; el.competition.value = 'all'; el.type.value = name === 'tactical' ? 'tactical' : 'all'; el.territory.value = 'all';
    el.availability.value = name === 'us' ? 'us' : 'all'; el.status.value = name === 'leads' ? 'all' : 'confirmed';
    el.dateRange.value = name === 'leads' ? 'all' : name === 'reset' ? '60' : '30'; el.sort.value = 'soonest';
    document.querySelectorAll('[data-preset]').forEach(b => { const active = b.dataset.preset === name; b.classList.toggle('active', active); b.setAttribute('aria-pressed', String(active)); });
    applyFilters();
  }

  function render(data, fetchFailed = false) {
    feeds = data.feeds.filter(f => f && typeof f === 'object').map(f => normalizeFeed(f));
    const selectedComp = el.competition.value, selectedTerritory = el.territory.value;
    el.competition.innerHTML = '<option value="all">All competitions</option>' + [...new Set([...PRIMARY, ...FALLBACK, ...feeds.map(f => f.competition).filter(Boolean)])].sort().map(c => `<option value="${esc(c)}">${esc(c)}</option>`).join('');
    el.competition.value = [...el.competition.options].some(o => o.value === selectedComp) ? selectedComp : 'all';
    const territories = [...new Set(feeds.flatMap(f => f.territories || []))].sort();
    el.territory.innerHTML = '<option value="all">All territories</option>' + territories.map(t => `<option value="${esc(t)}">${esc(t)}</option>`).join('');
    el.territory.value = [...el.territory.options].some(o => o.value === selectedTerritory) ? selectedTerritory : 'all';
    const checked = dateValue(data.lastSuccessfulScanAt), attempt = dateValue(data.lastAttemptAt), stale = checked === null || checked < Date.now() - 86400000;
    const status = data.scanStatus === 'ok' && data.sourceHealth.some(h => !h.ok) ? 'partial' : data.scanStatus;
    const degraded = fetchFailed || stale || status !== 'ok';
    el.updateLabel.textContent = degraded ? 'Check freshness' : 'Discovery scan current';
    document.querySelector('.update-box').classList.toggle('degraded', degraded);
    el.lastUpdated.textContent = checked === null ? 'No complete scan recorded' : `Complete scan: ${formatDate(data.lastSuccessfulScanAt)}`;
    el.dataNotice.textContent = fetchFailed ? 'Could not refresh this page. Showing the last usable snapshot; check source dates before relying on a listing.' : status === 'partial' || status === 'failed' ? `Latest scan ${status === 'partial' ? 'could not reach every source' : 'failed'}. Retained evidence keeps its original date.${attempt ? ` Attempt: ${formatDate(data.lastAttemptAt)}.` : ''}` : stale ? 'This snapshot has no complete scan in the last 24 hours. Source links may help you verify availability.' : 'Worldwide discovery is enabled. Confirmed results require an exact public viewing route and territory; commentary language and audio are descriptive, not eligibility requirements.';
    el.dataNotice.classList.toggle('warning', degraded);
    const upcoming = feeds.filter(f => f.status === 'confirmed' && dateValue(f.kickoff) >= Date.now());
    el.confirmedCount.textContent = upcoming.length;
    el.productionCount.textContent = feeds.filter(f => f.status === 'production').length;
    el.candidateCount.textContent = feeds.filter(f => f.status === 'candidate').length;
    el.sourceHealth.innerHTML = (data.sourceHealth || []).map(h => `<li><span>${esc(h.source)}</span><strong class="${h.ok ? '' : 'failed'}">${h.ok ? 'Fetched' : 'Unavailable'}${h.checkedAt ? ` · ${esc(formatDate(h.checkedAt))}` : ''}${Number.isFinite(h.count) ? ` · ${h.count} found` : ''}${h.policyReviewExpired ? ' · access policy review expired' : ''}</strong></li>`).join('') || '<li>No automated source-check results in this snapshot.</li>';
    const next = upcoming.filter(f => f.type === 'tactical').sort((a, b) => dateValue(a.kickoff) - dateValue(b.kickoff))[0];
    el.featuredSection.classList.toggle('hidden', !next);
    if (next) el.featured.innerHTML = `<div><div class="match">${esc(next.match)}</div><div class="meta">${esc(next.competition)} · ${esc(formatDate(next.kickoff))} · ${esc(next.territories.join(', '))}</div></div><a class="watch-link" href="${esc(safeUrl(next.watchUrl))}" target="_blank" rel="noopener noreferrer">Open viewing service ↗</a>`;
    applyFilters();
    payload = data;
  }
  async function refresh() {
    const url = window.TACTICAL_FEED_DATA_URL || (location.protocol === 'file:' ? null : 'https://raw.githubusercontent.com/Expiramentor5468/tacticalviewer/main/data/feeds.json');
    if (!url) return;
    const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 8000);
    try {
      const response = await fetch(url, { cache: 'no-store', signal: controller.signal });
      if (!response.ok) throw new Error('Data unavailable');
      const next = await response.json();
      if (!validPayload(next)) throw new Error('Invalid data');
      if ((dateValue(next.updatedAt) ?? 0) < (dateValue(payload.updatedAt) ?? 0)) throw new Error('Remote snapshot is older');
      render(next);
    } catch { render(payload, true); }
    finally { clearTimeout(timer); }
  }

  ['search', 'competition', 'type', 'territory', 'availability', 'status', 'dateRange', 'sort'].forEach(id => el[id].addEventListener(id === 'search' ? 'input' : 'change', () => {
    primaryOnly = false;
    document.querySelectorAll('[data-preset]').forEach(b => { b.classList.remove('active'); b.setAttribute('aria-pressed', 'false'); });
    applyFilters();
  }));
  document.querySelectorAll('[data-preset]').forEach(b => b.addEventListener('click', () => preset(b.dataset.preset)));
  render(validPayload(window.TACTICAL_FEED_DATA) ? window.TACTICAL_FEED_DATA : { schemaVersion: 2, updatedAt: '1970-01-01T00:00:00Z', scanStatus: 'failed', sourceHealth: [], feeds: [] });
  preset('primary'); refresh();
  setInterval(() => { if (!document.hidden) { render(payload); refresh(); } }, 5 * 60 * 1000);
})();
