#!/usr/bin/env python3
"""Discover leads; never infer public carriage from a production listing. Standard library only."""
from __future__ import annotations
import hashlib
import html
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
UA = 'TacticalFeedFinder/2.0 (+https://github.com/Expiramentor5468/tacticalviewer)'
KEYWORDS = re.compile(r'\b(tactical\s*(?:cam|camera|feed|view)|wide[- ]angle|coach\s*cam|ref\s*cam|manager\s*mode|game\s*mode)\b', re.I)
SEARCHES = [
    ('UEFA Champions League', '"tactical cam" Champions League CBS Golazo'),
    ('Premier League', '"tactical cam" Premier League NBC Peacock'),
    ('MLS', 'MLS "tactical cam" OR "wide angle" broadcast'),
    ('Bundesliga', 'Bundesliga "tactical feed" broadcast'),
    ('Serie A', 'Serie A "tactical cam" OR "tactical feed" CBS'),
]

def stamp(dt):
    return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')

def parse_date(value):
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (ValueError, TypeError):
        return None

def safe_url(value):
    try:
        parts = urllib.parse.urlsplit(value or '')
        return parts.scheme in ('http', 'https') and bool(parts.hostname)
    except ValueError:
        return False

def get(url):
    request = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read(2_000_000).decode('utf-8', errors='replace')

def normalize(item, now):
    """Validate dates and expire claims, including manually supplied claims."""
    f = dict(item)
    if not f.get('id') or not f.get('match') or not f.get('competition'):
        return None
    kickoff = parse_date(f.get('kickoff'))
    if f.get('kickoff') and not kickoff:
        f['kickoff'] = None
    if kickoff and kickoff < now - timedelta(hours=6):
        return None
    verified = parse_date(f.get('verifiedAt'))
    recent = verified and now - timedelta(days=7) <= verified <= now
    confirmed = (f.get('exactFixtureVerified') is True and
                 f.get('publicAccessConfirmed') is True and kickoff and recent and
                 safe_url(f.get('sourceUrl')) and safe_url(f.get('watchUrl')) and
                 f.get('platform') and f.get('territories'))
    if f.get('status') == 'confirmed' and not confirmed:
        f['status'] = 'candidate'
        f['notes'] = 'Public access needs re-verification. ' + f.get('notes', '')
        f['usAvailability'] = None
        f['access'] = 'unknown'
    if f.get('status') not in ('confirmed', 'production', 'candidate'):
        f['status'] = 'candidate'
    # Discovery metadata is not proof of public access or a free/subscription offer.
    if f['status'] != 'confirmed':
        f['usAvailability'] = None
        f['access'] = 'unknown'
        f.pop('watchUrl', None)
    return f

def news_candidates(xml, comp, key, now):
    root = ET.fromstring(xml)  # malformed responses are errors, not empty successes
    if root.tag not in ('rss', 'feed', '{http://www.w3.org/2005/Atom}feed'):
        raise ValueError('Expected an RSS/Atom response')
    out = []
    for e in root.findall('./channel/item')[:30]:
        title = html.unescape(e.findtext('title', ''))
        summary = re.sub('<[^>]+>', ' ', html.unescape(e.findtext('description', '')))
        body = title + ' ' + summary
        if not KEYWORDS.search(body):
            continue
        try:
            published = parsedate_to_datetime(e.findtext('pubDate', ''))
            if published.tzinfo is None:
                continue
        except (ValueError, TypeError):
            continue
        if not now - timedelta(days=21) <= published <= now + timedelta(hours=1):
            continue
        link = e.findtext('link', '')
        if not safe_url(link):
            continue
        kind = 'tactical' if re.search(r'tactical|wide', body, re.I) else 'coach' if re.search(r'coach|manager', body, re.I) else 'ref' if re.search(r'ref\s*cam', body, re.I) else 'alternate'
        out.append({
            'id': 'news-' + hashlib.sha256((comp + link).encode()).hexdigest()[:16],
            'match': title, 'competition': comp, 'kickoff': None, 'type': kind,
            'status': 'candidate', 'platform': 'Publisher / carrier needs verification',
            'commentary': 'Unknown', 'usAvailability': None, 'access': 'unknown',
            'notes': 'News lead only. Publication does not verify a current fixture, full-match camera view, or public viewing route.',
            'sourceUrl': link, 'sourcePublishedAt': stamp(published), 'checkedAt': stamp(now),
            'sourceKey': key,
        })
    return out

class FixtureTable(HTMLParser):
    """Keep tooltip/template text inside its fixture row; ignore unrelated page text."""
    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.row = []
        elif tag == 'td' and self.row is not None:
            self.cell = []

    def handle_data(self, value):
        if self.cell is not None:
            self.cell.append(value.strip())

    def handle_endtag(self, tag):
        if tag == 'td' and self.row is not None and self.cell is not None:
            self.row.append(' '.join(x for x in self.cell if x))
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row, self.cell = None, None


def production_fixtures(content, now):
    parser = FixtureTable()
    parser.feed(content)
    rows = []
    for cells in parser.rows:
        if len(cells) != 8 or not re.search(r'\bTactical Feed\b', cells[7]):
            continue
        date_match = re.search(r'\d{1,2}-[A-Za-z]{3}-\d{4}', cells[1])
        time_match = re.fullmatch(r'\d{2}:\d{2}', cells[3].strip())
        if not date_match or not time_match or not cells[4] or not cells[5]:
            continue
        try:
            kickoff = datetime.strptime(date_match.group() + ' ' + time_match.group(), '%d-%b-%Y %H:%M').replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if kickoff < now or kickoff > now + timedelta(days=60):
            continue
        match = cells[4] + ' vs ' + cells[5]
        rows.append({
            'id': 'production-' + hashlib.sha256((match + stamp(kickoff)).encode()).hexdigest()[:16],
            'match': match, 'competition': 'Bundesliga', 'kickoff': stamp(kickoff),
            'type': 'tactical', 'status': 'production', 'platform': 'Bundesliga production; consumer carrier unverified',
            'commentary': 'Viewer audio unverified', 'usAvailability': None, 'access': 'unknown',
            'sourceUrl': 'https://products.bundesliga.com/fixtures', 'sourceKey': 'bundesliga:production',
            'checkedAt': stamp(now), 'exactFixtureVerified': True, 'publicAccessConfirmed': False,
            'notes': 'The fixture row lists Tactical Feed under Extra Feeds. This verifies production only; public viewing service, regions and price remain unverified.',
        })
    return rows


def dedupe(items):
    out, seen = [], set()
    for item in items:
        if item and item['id'] not in seen:
            fixture_key = (item.get('competition'), item.get('match'), item.get('kickoff'), item.get('type')) if item.get('kickoff') else None
            if fixture_key and fixture_key in seen:
                continue
            seen.add(item['id'])
            if fixture_key:
                seen.add(fixture_key)
            out.append(item)
    return out

def build_payload(manual, previous, fetch=get, now=None):
    now = now or datetime.now(timezone.utc)
    health, found = [], []
    for comp, query in SEARCHES:
        key = 'news:' + comp
        url = 'https://news.google.com/rss/search?q=' + urllib.parse.quote(query + ' when:21d') + '&hl=en-US&gl=US&ceid=US:en'
        try:
            rows = news_candidates(fetch(url), comp, key, now)
            found.extend(rows)
            health.append({'source': key, 'ok': True, 'checkedAt': stamp(now), 'count': len(rows)})
        except Exception as exc:
            health.append({'source': key, 'ok': False, 'attemptedAt': stamp(now), 'error': type(exc).__name__})
            found.extend(f for f in previous.get('feeds', []) if f.get('sourceKey') == key)
    key = 'bundesliga:production'
    url = 'https://products.bundesliga.com/fixtures'
    try:
        content = fetch(url)
        if len(content.strip()) < 100:
            raise ValueError('Incomplete production page')
        # This is a supplier catalogue. Even a named fixture would not prove carriage.
        fixtures = production_fixtures(content, now)
        found.extend(fixtures)
        if not fixtures and re.search(r'Tactical\s+Feed', html.unescape(content), re.I):
            found.append({
                'id': 'bundesliga-production-catalogue', 'match': 'Bundesliga tactical-feed production catalogue',
                'competition': 'Bundesliga', 'kickoff': None, 'type': 'tactical', 'status': 'production',
                'platform': 'Bundesliga Global Product Portfolio', 'commentary': 'Check source',
                'usAvailability': None, 'access': 'unknown', 'sourceUrl': url,
                'sourceKey': key, 'checkedAt': stamp(now),
                'notes': 'A feed product is listed for broadcasters. No current match or consumer viewing service is verified here. A production listing is not a watch link.',
            })
        health.append({'source': key, 'ok': True, 'checkedAt': stamp(now)})
    except Exception as exc:
        health.append({'source': key, 'ok': False, 'attemptedAt': stamp(now), 'error': type(exc).__name__})
        found.extend(f for f in previous.get('feeds', []) if f.get('sourceKey') == key)
    # Failed-source retained news still expires; failure must not make old articles current.
    found = [f for f in found if not f.get('sourceKey', '').startswith('news:') or
             (parse_date(f.get('sourcePublishedAt')) and parse_date(f['sourcePublishedAt']) >= now - timedelta(days=21))]
    feeds = dedupe(normalize(f, now) for f in manual + found)
    all_ok = all(h['ok'] for h in health)
    return {
        'schemaVersion': 2, 'updatedAt': stamp(now), 'lastAttemptAt': stamp(now),
        'lastSuccessfulScanAt': stamp(now) if all_ok else previous.get('lastSuccessfulScanAt'),
        'scanStatus': 'ok' if all_ok else 'partial' if any(h['ok'] for h in health) else 'failed',
        'sourceHealth': health, 'feeds': feeds,
    }

def read_json(path, fallback):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else fallback

def write_payload(payload):
    DATA.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, ensure_ascii=False)
    for path, content in ((DATA / 'feeds.json', encoded + '\n'), (ROOT / 'data.js', 'window.TACTICAL_FEED_DATA = ' + encoded + ';\n')):
        temp = path.with_suffix(path.suffix + '.tmp')
        temp.write_text(content, encoding='utf-8')
        temp.replace(path)

if __name__ == '__main__':
    payload = build_payload(read_json(DATA / 'manual_overrides.json', {'feeds': []})['feeds'], read_json(DATA / 'feeds.json', {}))
    write_payload(payload)
    print(f"Scan {payload['scanStatus']}: {len(payload['feeds'])} listings; {sum(h['ok'] for h in payload['sourceHealth'])}/{len(payload['sourceHealth'])} sources checked")
    # The workflow should commit the honest failure metadata before surfacing this failure.
    sys.exit(0 if payload['scanStatus'] == 'ok' else 2)
