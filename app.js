(() => {
  const payload = window.TACTICAL_FEED_DATA || { updatedAt: null, feeds: [] };
  const feeds = payload.feeds || [];
  const els = Object.fromEntries(['search','competition','type','availability','status','dateRange','sort','feedGrid','resultCount','emptyState','lastUpdated','featured','featuredSection'].map(id => [id, document.getElementById(id)]));

  const primary = new Set(['UEFA Champions League','Premier League','MLS']);
  const typeLabel = { tactical:'True tactical / wide', coach:'Coach cam', ref:'Ref cam', alternate:'Alternate broadcast' };
  const formatDate = iso => iso ? new Intl.DateTimeFormat(undefined,{weekday:'short',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'}).format(new Date(iso)) : 'Kickoff not yet verified';
  const escapeHtml = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
  const daysFromNow = iso => iso ? (new Date(iso) - new Date()) / 86400000 : null;

  function setUpdated() {
    if (!payload.updatedAt) return els.lastUpdated.textContent = 'Update time unavailable';
    const d = new Date(payload.updatedAt);
    els.lastUpdated.textContent = `Last checked ${new Intl.DateTimeFormat(undefined,{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}).format(d)}`;
  }

  function populateCompetitions() {
    [...new Set(feeds.map(f => f.competition))].sort().forEach(c => {
      const o = document.createElement('option'); o.value = c; o.textContent = c; els.competition.appendChild(o);
    });
  }

  function statusBadge(f) {
    return `<span class="badge ${f.status}">${f.status === 'confirmed' ? 'CONFIRMED' : 'CANDIDATE'}</span>`;
  }

  function card(f) {
    const us = f.usAvailability === true ? 'Yes' : f.usAvailability === false ? 'No / not known to be carried' : 'Unknown';
    const cost = f.access === 'free' ? 'Free' : f.access === 'subscription' ? 'Subscription' : 'Unknown';
    return `<article class="feed-card">
      <div class="feed-top">
        <div class="card-row"><div class="competition">${escapeHtml(f.competition)}</div><div class="badges">${statusBadge(f)}<span class="badge ${f.type}">${escapeHtml(typeLabel[f.type] || f.type)}</span></div></div>
        <div class="match-title">${escapeHtml(f.match)}</div>
        <div class="time">${escapeHtml(formatDate(f.kickoff))}</div>
      </div>
      <div class="feed-details">
        <div class="detail"><span>Platform</span><strong>${escapeHtml(f.platform || 'TBD')}</strong></div>
        <div class="detail"><span>Commentary</span><strong>${escapeHtml(f.commentary || 'Unknown')}</strong></div>
        <div class="detail"><span>U.S. availability</span><strong>${escapeHtml(us)}</strong></div>
        <div class="detail"><span>Access</span><strong>${escapeHtml(cost)}</strong></div>
      </div>
      ${f.notes ? `<div class="notes">${escapeHtml(f.notes)}</div>` : ''}
      <div class="card-actions">
        ${f.sourceUrl ? `<a class="source-link" href="${escapeHtml(f.sourceUrl)}" target="_blank" rel="noreferrer">Verify source ↗</a>` : '<span></span>'}
        <span class="confidence">Confidence ${escapeHtml(f.confidence || '—')}</span>
      </div>
    </article>`;
  }

  function applyFilters() {
    const q = els.search.value.trim().toLowerCase();
    const comp = els.competition.value;
    const type = els.type.value;
    const availability = els.availability.value;
    const status = els.status.value;
    const range = els.dateRange.value;

    let out = feeds.filter(f => {
      const hay = `${f.match} ${f.competition} ${f.platform} ${f.commentary} ${f.notes || ''}`.toLowerCase();
      if (q && !hay.includes(q)) return false;
      if (comp !== 'all' && f.competition !== comp) return false;
      if (type !== 'all' && f.type !== type) return false;
      if (status !== 'all' && f.status !== status) return false;
      if (availability === 'us' && f.usAvailability !== true) return false;
      if (availability === 'free' && f.access !== 'free') return false;
      if (availability === 'subscription' && f.access !== 'subscription') return false;
      if (range !== 'all') {
        const d = daysFromNow(f.kickoff);
        if (d !== null && (d < -0.2 || d > Number(range))) return false;
      }
      return true;
    });

    const sort = els.sort.value;
    const timeVal = f => f.kickoff ? new Date(f.kickoff).getTime() : Number.MAX_SAFE_INTEGER;
    out.sort((a,b) => sort === 'league' ? a.competition.localeCompare(b.competition) || timeVal(a)-timeVal(b) : sort === 'confidence' ? (b.confidenceScore||0)-(a.confidenceScore||0) : timeVal(a)-timeVal(b));

    els.feedGrid.innerHTML = out.map(card).join('');
    els.resultCount.textContent = `${out.length} feed${out.length === 1 ? '' : 's'} shown`;
    els.emptyState.classList.toggle('hidden', out.length > 0);
  }

  function showFeatured() {
    const next = feeds.filter(f => f.status === 'confirmed' && f.type === 'tactical' && f.kickoff && new Date(f.kickoff) > new Date()).sort((a,b)=>new Date(a.kickoff)-new Date(b.kickoff))[0];
    if (!next) return;
    els.featured.innerHTML = `<div><div class="match">${escapeHtml(next.match)}</div><div class="meta">${escapeHtml(next.competition)} · ${escapeHtml(formatDate(next.kickoff))}<br>${escapeHtml(next.platform || '')}${next.commentary ? ` · ${escapeHtml(next.commentary)}` : ''}</div></div>${next.sourceUrl ? `<a class="source-link" href="${escapeHtml(next.sourceUrl)}" target="_blank" rel="noreferrer">Official source ↗</a>` : ''}`;
    els.featured.className = 'featured';
    els.featuredSection.classList.remove('hidden');
  }

  function preset(name, button) {
    document.querySelectorAll('.chip').forEach(b => b.classList.remove('active'));
    if (button && name !== 'reset') button.classList.add('active');
    els.search.value=''; els.competition.value='all'; els.type.value='all'; els.availability.value='all'; els.status.value='confirmed'; els.dateRange.value='30'; els.sort.value='soonest';
    if (name === 'primary') {
      const shown = feeds.filter(f => primary.has(f.competition));
      window.__primaryOnly = true;
      renderPrimary(shown); return;
    }
    window.__primaryOnly = false;
    if (name === 'tactical') els.type.value='tactical';
    if (name === 'us') els.availability.value='us';
    applyFilters();
  }

  function renderPrimary(primaryFeeds) {
    const within30 = f => { const d = daysFromNow(f.kickoff); return f.status === 'confirmed' && d !== null && d >= -0.2 && d <= 30; };
    let out = primaryFeeds.filter(within30).sort((a,b)=>new Date(a.kickoff)-new Date(b.kickoff));
    let label = 'primary-league';

    if (!out.length) {
      out = feeds.filter(f => !primary.has(f.competition) && within30(f))
        .sort((a,b)=>(b.confidenceScore||0)-(a.confidenceScore||0) || new Date(a.kickoff)-new Date(b.kickoff));
      label = 'fallback';
    }

    els.feedGrid.innerHTML = out.map(card).join('');
    els.resultCount.textContent = `${out.length} ${label} feed${out.length === 1 ? '' : 's'} shown`;
    els.emptyState.classList.toggle('hidden', out.length > 0);
  }

  ['search','competition','type','availability','status','dateRange','sort'].forEach(id => els[id].addEventListener(id === 'search' ? 'input' : 'change', () => { window.__primaryOnly=false; document.querySelectorAll('.chip').forEach(b=>b.classList.remove('active')); applyFilters(); }));
  document.querySelectorAll('.chip').forEach(b => b.addEventListener('click', () => preset(b.dataset.preset, b)));

  setUpdated(); populateCompetitions(); showFeatured(); preset('primary', document.querySelector('[data-preset="primary"]'));
})();
