# Tactical Feed Finder

A zero-build, auto-updating watchlist for useful live soccer camera feeds around the world. UEFA Champions League, Premier League and MLS are prioritized, but any competition is eligible when a public viewing route can be verified.

## What counts as confirmed

**Public access verified** is intentionally strict about access, not audio. A listing needs all of the following:

- an exact fixture and kickoff time;
- a public consumer viewing route;
- the exact countries/territories where that route is available;
- a watch URL and supporting source URL;
- evidence reviewed within the last seven days.

Commentary language, audio language, and even the presence of audio are metadata only. English, German, Italian, French, Spanish, other languages, unknown audio, and video-only/raw camera feeds are all eligible if the public video route itself is verified.

A feed can be public in Germany, the UK, Australia, Japan, the U.S., or anywhere else. U.S. availability is only a filter — it is not an assumption.

**Production only** means a league or production supplier confirms the camera/feed exists for broadcasters, but no qualifying consumer route has been proven.

**Unverified lead** means a source or branded product looks relevant but is still missing one or more of: exact fixture, public territory, watch route, or current access terms.

## Feed types

- **Tactical / wide** — the main target: a high/wide view that keeps most or all players visible.
- **Coach cam** — manager/bench view.
- **Ref cam** — referee POV.
- **Alternate broadcast** — included when it provides useful angles, live tactical data, analysis, or other camera access even when it is not a persistent full-pitch view.

## Automated sources

The GitHub Actions updater currently combines several layers:

1. **Amazon Prime Vision** — reads Amazon's official monthly Champions League schedule and joins it to Prime Vision's official product/territory evidence. Language is recorded when known.
2. **Bundesliga production** — parses DFL fixture/product data for Tactical Feed and extra-camera production metadata.
3. **Sky/WOW Bundesliga monitor** — tracks the Saturday Topspiel Tactical Feed and can confirm the public German viewing route even when consumer audio language is unknown.
4. **Branded-product monitors** — watches for CBS Golazo Tactical Cam, MLS/Apple Ref Cam and altcasts, Premier League Game Mode/tactical variants, and Ligue 1+ Expert Mode.
5. **Worldwide discovery net** — searches for tactical cams, tactical feeds, wide-angle cameras, coach cams, manager modes and referee cams outside the known services.

Known branded products are preferred over generic keyword discovery. Generic discoveries remain leads until the public route and exact fixture can be verified.

## Territory and audio handling

Every confirmed row carries a `territories` array. The site builds the Territory filter from the data automatically and displays the verified regions directly on each card.

Audio is deliberately separate from availability. `language` and `commentary` describe what is known, including `Unknown / not verified` or video-only/raw feeds. They do not control confirmed status.

## Open or deploy

Open `index.html` directly, or serve the repository from GitHub Pages / any static host. No build step or API key is required.

Hosted pages fetch `https://raw.githubusercontent.com/Expiramentor5468/tacticalviewer/main/data/feeds.json` on load and every five minutes while visible. The bundled `data.js` remains as an offline/failure fallback.

## Automatic updates

The GitHub Actions workflow runs every three hours and can also be started manually. It runs tests, refreshes all discovery/enrichment stages, commits changed `data.js` / `data/feeds.json`, and lets GitHub Pages republish the result.

This updater is entirely repository-side. It does **not** require or consume a ChatGPT automation slot.

```sh
python scripts/update_feeds.py
python scripts/enrich_prime_vision.py
python scripts/enrich_sky_bundesliga.py
python scripts/enrich_branded_monitors.py
python scripts/enrich_global_discovery.py
python -m unittest discover -s tests -v
node --test tests/app.test.js
```

Python 3.11+ and Node 18+ are sufficient.

## Manual verification

`data/manual_overrides.json` is reserved for exact feeds that have been manually verified but do not yet have a reliable source-specific parser.

A confirmed row requires:

- `status: "confirmed"`
- `exactFixtureVerified: true`
- `publicAccessConfirmed: true`
- timezone-aware `kickoff` and fresh `verifiedAt`
- HTTP(S) `sourceUrl` and `watchUrl`
- named `platform`
- non-empty `territories`
- supported access terms (`free` or `subscription`) when known

`language` and `commentary` should be populated when known, but they are not required for confirmation.

Both the updater and browser client downgrade stale/incomplete confirmation claims rather than guessing.

## Philosophy

The goal is not to maximize the number of cards. It is to maximize the number of cards you can actually use.

A broadcaster producing a tactical feed is not the same thing as fans being able to watch it. A stream existing in one country is not evidence it exists elsewhere. Audio information is useful, but a silent or non-English tactical feed is still useful if you can actually watch it.
