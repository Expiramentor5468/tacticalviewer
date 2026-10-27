# Tactical Feed Finder

A static, mobile-friendly guide for finding live soccer tactical cams, full-pitch/wide feeds, coach cams, ref cams and worthwhile alternate broadcasts.

## What it does

- Defaults to **confirmed** feeds only.
- Prioritizes **UEFA Champions League, Premier League and MLS**.
- Also tracks **Bundesliga, Serie A and Ligue 1 / PSG**.
- Filters by competition, feed type, U.S. availability, access type, date and confidence.
- Uses local device time automatically.
- Keeps **candidate discoveries** separate from confirmed feeds to avoid false positives.
- Includes a no-key automatic discovery pipeline using official pages plus Google News RSS.

## Run locally

You can open `index.html` directly. No web server or build step is required.

## Automatic updates

The included GitHub Actions workflow runs every 3 hours and updates `data.js` / `data/feeds.json`.

The updater is intentionally conservative:

- `data/manual_overrides.json` contains exact confirmed feeds.
- Automatic news discovery creates **Candidate** items, not Confirmed items.
- Bundesliga's official production page is watched directly because it explicitly publishes Tactical Feed production metadata.

This prevents a headline mentioning an “alternate broadcast” from being incorrectly presented as a true full-pitch tactical feed.

## Deploy free with GitHub Pages

For this repository (`Expiramentor5468/tacticalviewer`):

1. In GitHub: **Settings → Pages**.
2. Set **Deploy from a branch** → `main` → `/ (root)`.
3. GitHub Actions will refresh the feed data every 3 hours.

No API keys are required for the included updater.

## Improving verification

The strongest next step is a source-specific parser for each rights holder:

- CBS Sports / Paramount press schedules for UCL and Serie A
- NBC Sports / Peacock press schedules for Premier League
- MLS / Apple announcements for MLS
- Bundesliga Global Product Portfolio
- Ligue 1 / rights-holder announcements

Once a source has a stable exact-match format, promote it from discovery-only to automatic confirmation in `scripts/update_feeds.py`.
