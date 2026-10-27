# Tactical Feed Finder

A zero-build soccer camera-feed watchlist. Champions League, Premier League and MLS come first, with Bundesliga and Serie A as fallback.

## Evidence, not promises

- **Public access verified** means an exact fixture and public viewing route have been manually verified, with regions and evidence reviewed within seven days. A source and a viewing-service URL are both required.
- **Production only** means a league lists a camera feed for broadcasters. It does **not** mean a consumer service carries it. U.S. availability, cost and the watch link remain unknown.
- **Unverified lead** means a recent article mentions a potentially useful camera feed. It does not confirm a current fixture.

The initial Bayern–Dortmund listing is production only. Its official fixture-row tooltip lists Tactical Feed, but a public viewing route has not been verified. Zero publicly verified results is an honest outcome.

## Open or deploy

Open `index.html` directly, or serve these static files from GitHub Pages / any static host. No build step, API key or third-party Python package is needed.

Hosted pages fetch `https://raw.githubusercontent.com/Expiramentor5468/tacticalviewer/main/data/feeds.json` on load and every five minutes while visible. This lets mirrors and GitHub Pages pick up scheduled data commits without a site rebuild. The bundled `data.js` works offline and is retained if the fetch fails, with a visible warning. Never replace a newer snapshot with an older remote response.

To use another repository or a same-origin data file, set this before `app.js`:

```html
<script>window.TACTICAL_FEED_DATA_URL = 'data/feeds.json';</script>
```

## Update and test

```sh
python scripts/update_feeds.py
python -m unittest discover -s tests -v
node --test tests/app.test.js
```

Python 3.11+ and Node 18+ are sufficient. The updater searches Google News RSS for recent leads and parses the official Bundesliga fixture table (including Extra Feeds tooltip templates) into production-only entries. It uses the UTC column, never the CET display column. If the table layout changes, it falls back to a clearly undated catalogue lead instead of guessing fixtures.

The updater publishes per-source health. Failed sources retain prior evidence with its original timestamp; retained news still expires after 21 days. A complete successful scan timestamp advances only when all sources respond. Partial and failed scans write honest metadata and then exit 2 so scheduled failures are visible. The workflow should commit the metadata before reporting the failure. A scan checks discovery sources; it does not renew manual evidence or prove public access.

## Manual verification

Edit `data/manual_overrides.json`. A confirmed row requires all of:

- `status: "confirmed"`, `exactFixtureVerified: true`, `publicAccessConfirmed: true`
- a timezone-aware ISO `kickoff` and `verifiedAt` (within seven days, not in the future)
- HTTP(S) `sourceUrl` and `watchUrl`, a named `platform`, and non-empty `territories` such as `["US"]`
- evidence for the stated feed, fixture and territory; set `usAvailability`, `access` and `commentary` only when supported

The updater and client downgrade incomplete or stale confirmed rows to leads. Expired fixtures leave the generated data six hours after kickoff. Upcoming filters exclude past, invalid and unknown kickoff times. “Explore evidence & leads” deliberately includes undated records; article publication and source-fetch dates are displayed separately from kickoff.

Production-only manual rows use `status: "production"`, `publicAccessConfirmed: false`, and `usAvailability: null` / `access: "unknown"`. Never infer carriage from a league supplying a feed or an old article describing past availability.

## Limits

This is a discovery watchlist, not a full fixture database or a live-stream provider. UCL, Premier League and MLS discovery does not yet have source-specific automatic fixture/access confirmation. News indexing can miss announcements; broadcaster sign-in, regional restrictions and last-minute schedule changes still need checking. Source health is visible in the page footer. The workflow's schedule is best effort, not a freshness guarantee.
