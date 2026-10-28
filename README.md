# Tactical Feed Finder

A zero-build, auto-updating watchlist for useful live soccer camera feeds around the world. UEFA Champions League, Premier League and MLS are prioritized, but any competition is eligible when an English-language public stream can be verified.

## What counts as confirmed

**Public access verified** is intentionally strict. A listing needs all of the following:

- an exact fixture and kickoff time;
- a public consumer viewing route;
- the exact countries/territories where that route is available;
- verified **English commentary/audio**;
- a watch URL and supporting source URL;
- evidence reviewed within the last seven days.

A feed can be public in Germany, the UK, Australia, Japan, the U.S., or anywhere else. U.S. availability is only a filter — it is not an assumption.

**Production only** means a league or production supplier confirms the camera/feed exists for broadcasters, but no qualifying consumer route has been proven.

**Unverified lead** means a source or branded product looks relevant but is still missing one or more of: exact fixture, English audio, public territory, watch route, or access terms.

## Feed types

- **Tactical / wide** — the main target: a high/wide view that keeps most or all players visible.
- **Coach cam** — manager/bench view.
- **Ref cam** — referee POV.
- **Alternate broadcast** — included when it provides useful angles, live tactical data, or analysis even when it is not a persistent full-pitch view.

## Automated sources

The GitHub Actions updater currently combines several layers:

1. **Amazon Prime Vision** — reads Amazon's official monthly Champions League schedule and joins it to Prime Vision's official product/territory/language evidence.
2. **Bundesliga production** — parses DFL fixture/product data for Tactical Feed and extra-camera production metadata.
3. **Sky/WOW Bundesliga monitor** — tracks the Saturday Topspiel Tactical Feed, but does not mark it English-confirmed unless consumer audio is independently verified.
4. **Branded-product monitors** — watches for CBS Golazo Tactical Cam, MLS/Apple Ref Cam and altcasts, Premier League Game Mode/tactical variants, and Ligue 1+ Expert Mode.
5. **Worldwide discovery net** — searches for tactical cams, tactical feeds, wide-angle cameras, coach cams, manager modes and referee cams outside the known services.

Known branded products are preferred over generic keyword discovery. Generic discoveries remain leads until the full confirmation standard is met.

## Current territory handling

Every confirmed row carries a `territories` array. The site builds the Territory filter from the data automatically and displays the verified regions directly on each card.

English is currently required for confirmed status. A public stream with only Italian, German, French, Spanish, etc. audio can still be discovered internally, but it will not enter the confirmed English watchlist until English audio is proven.

## Open or deploy

Open `index.html` directly, or serve the repository from GitHub Pages / any static host. No build step or API key is required.

Hosted pages fetch `https://raw.githubusercontent.com/Expiramentor5468/tacticalviewer/main/data/feeds.json` on load and every five minutes while visible. The bundled `data.js` remains as an offline/failure fallback.

## Automatic updates

The GitHub Actions workflow runs every three hours and can also be started manually. It runs tests, refreshes all discovery/enrichment stages, commits changed `data.js` / `data/feeds.json`, and lets GitHub Pages republish the result.

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
- `language: "English"`
- supported access terms (`free` or `subscription`) when known

Both the updater and browser client downgrade stale/incomplete confirmation claims rather than guessing.

## Philosophy

The goal is not to maximize the number of cards. It is to maximize the number of cards you can actually use.

A broadcaster producing a tactical feed is not the same thing as fans being able to watch it. A stream existing in one country is not evidence it exists elsewhere. A broadcaster offering English on its normal feed is not proof that an alternate feed has English. TacticalViewer keeps those distinctions explicit.
