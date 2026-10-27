#!/usr/bin/env python3
"""Conservative tactical-feed discovery updater.

Confirmed entries come from manual overrides or exact official-source rules.
News/RSS discoveries become candidates until an exact match/feed/platform can be verified.
No API keys are required.
"""
from __future__ import annotations
import json, re, html, urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests
import feedparser
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
UA = "TacticalFeedFinder/1.0 (+https://github.com/)"
KEYWORDS = re.compile(r"\b(tactical\s*(?:cam|camera|feed|view)|wide[- ]angle|coach\s*cam|ref\s*cam|manager\s*mode|game\s*mode)\b", re.I)

SEARCHES = [
    ("UEFA Champions League", '"tactical cam" Champions League CBS Golazo'),
    ("Premier League", '"tactical cam" Premier League NBC Peacock'),
    ("MLS", 'MLS "tactical cam" OR "wide angle" broadcast'),
    ("Serie A", 'Serie A "tactical cam" OR "tactical feed" CBS'),
    ("Ligue 1", 'Ligue 1 PSG "tactical feed" OR "tactical cam"'),
]

def get(url: str) -> str:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=25)
    r.raise_for_status()
    return r.text

def load_manual():
    p = DATA / "manual_overrides.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"feeds": []}

def google_news_candidates():
    out = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=21)
    for comp, query in SEARCHES:
        url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(query) + "&hl=en-US&gl=US&ceid=US:en"
        try:
            feed = feedparser.parse(requests.get(url, headers={"User-Agent": UA}, timeout=25).content)
        except Exception:
            continue
        for e in feed.entries[:20]:
            title = html.unescape(getattr(e, "title", ""))
            summary = BeautifulSoup(getattr(e, "summary", ""), "html.parser").get_text(" ", strip=True)
            text = f"{title} {summary}"
            if not KEYWORDS.search(text):
                continue
            published = getattr(e, "published_parsed", None)
            if published:
                dt = datetime(*published[:6], tzinfo=timezone.utc)
                if dt < cutoff: continue
            slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:90]
            out.append({
                "id": f"candidate-{slug}",
                "match": title,
                "competition": comp,
                "kickoff": None,
                "type": "tactical" if re.search(r"tactical|wide", text, re.I) else "alternate",
                "status": "candidate",
                "platform": "Needs verification",
                "commentary": "Unknown",
                "usAvailability": None,
                "access": "unknown",
                "confidence": "Lead only",
                "confidenceScore": 35,
                "notes": "Automatic discovery lead. Open the source and verify the exact match, consumer availability, feed type and kickoff before treating this as confirmed.",
                "sourceUrl": getattr(e, "link", "")
            })
    return out

def bundesliga_official_candidates():
    try:
        text = BeautifulSoup(get("https://products.bundesliga.com/fixtures"), "html.parser").get_text(" ", strip=True)
    except Exception:
        return []
    if not re.search(r"Tactical Feed", text, re.I):
        return []
    return [{
        "id": "candidate-bundesliga-official-fixtures",
        "match": "Bundesliga official fixture-production page contains Tactical Feed listings",
        "competition": "Bundesliga",
        "kickoff": None,
        "type": "tactical",
        "status": "candidate",
        "platform": "Bundesliga Global Product Portfolio",
        "commentary": "English tactical analysis on Tactical Feed product",
        "usAvailability": None,
        "access": "unknown",
        "confidence": "Official lead",
        "confidenceScore": 70,
        "notes": "Official production page currently contains Tactical Feed information. Verify the specific fixture association before promotion to Confirmed.",
        "sourceUrl": "https://products.bundesliga.com/fixtures"
    }]

def dedupe(items):
    seen, out = set(), []
    for x in items:
        key = x.get("id") or (x.get("match"), x.get("competition"), x.get("kickoff"), x.get("type"))
        if key in seen: continue
        seen.add(key); out.append(x)
    return out

def write_payload(feeds):
    payload = {"updatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00","Z"), "feeds": feeds}
    (DATA / "feeds.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    (ROOT / "data.js").write_text("window.TACTICAL_FEED_DATA = " + json.dumps(payload, indent=2, ensure_ascii=False) + ";\n", encoding="utf-8")

if __name__ == "__main__":
    manual = load_manual().get("feeds", [])
    candidates = google_news_candidates() + bundesliga_official_candidates()
    write_payload(dedupe(manual + candidates))
    print(f"Updated {len(manual)} confirmed/manual + {len(candidates)} discovery candidates")
