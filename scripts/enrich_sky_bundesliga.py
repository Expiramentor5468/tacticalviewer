#!/usr/bin/env python3
"""Add public Sky/WOW Bundesliga Saturday Topspiel Tactical Feeds.

Evidence chain:
- Sky's current Bundesliga programming policy: Saturday Topspiel + Tactical Feed on
  Sky Sport Bundesliga 3, available through Sky/WOW.
- DFL Global Product Portfolio: Tactical Feed includes expert English-language analysis.
- DFL fixture table: exact Saturday 18:30 CET Topspiel fixtures.

Only Germany is asserted as a public territory here. Other carriers/territories must be
verified separately rather than inferred from the existence of the DFL production feed.
"""
from __future__ import annotations

import calendar
import hashlib
import html
import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
UA = "TacticalFeedFinder/3.1 (+https://github.com/Expiramentor5468/tacticalviewer)"
BERLIN = ZoneInfo("Europe/Berlin")
FIXTURES = "https://products.bundesliga.com/fixtures"
DFL_PRODUCT = "https://products.bundesliga.com/matchdays"
SKY_POLICY = "https://videos.sport.sky.de/fussball/artikel/patrick-ittrich-neuer-schiedsrichter-experte-bei-sky-sport-ex-bundesliga-referee-verstaerkt-bundesliga-team/13574269/35311"
SKY_WATCH = "https://www.wowtv.de/"
# Explicit current exception: Sky/RTL announced that Bundesliga 3 carries the animated
# Next Level feed for this fixture instead of the normal Tactical Feed slot.
EXCEPTIONS = {("FC Bayern München", "Borussia Dortmund", "2026-10-31")}


def get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.read(2_500_000).decode("utf-8", errors="replace")


class TableRows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in {"td", "th"} and self.row is not None:
            self.cell = []

    def handle_data(self, value):
        if self.cell is not None:
            value = value.strip()
            if value:
                self.cell.append(value)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.row is not None and self.cell is not None:
            self.row.append(" ".join(self.cell))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row, self.cell = None, None


def plain(content: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", content)))


def policy_ok(sky: str, dfl: str) -> bool:
    s, d = plain(sky), plain(dfl)
    return bool(
        re.search(r"Tactical Feed", s, re.I)
        and re.search(r"Sky Sport Bundesliga 3", s, re.I)
        and re.search(r"Topspiel", s, re.I)
        and re.search(r"Tactical Feed", d, re.I)
        and re.search(r"English-language analysis", d, re.I)
    )


def parse_topspiele(content: str, now: datetime) -> list[dict]:
    parser = TableRows(); parser.feed(content)
    out, horizon = [], now + timedelta(days=60)
    for cells in parser.rows:
        date_cell = next((c for c in cells if re.fullmatch(r"\d{1,2}-[A-Za-z]{3}-\d{4}", c)), None)
        if not date_cell or not any(c.strip().lower() == "sat" for c in cells):
            continue
        times = [c for c in cells if re.fullmatch(r"\d{2}:\d{2}", c.strip())]
        if not times or times[0] != "18:30":
            continue
        type_i = next((i for i, c in enumerate(cells) if c.strip() in {"Platinum", "Gold", "Silver"}), None)
        if type_i is None or type_i < 2:
            continue
        home, away = cells[type_i - 2].strip(), cells[type_i - 1].strip()
        try:
            local = datetime.strptime(f"{date_cell} 18:30", "%d-%b-%Y %H:%M").replace(tzinfo=BERLIN)
        except ValueError:
            continue
        kickoff = local.astimezone(timezone.utc)
        if kickoff < now - timedelta(hours=6) or kickoff > horizon:
            continue
        if (home, away, local.date().isoformat()) in EXCEPTIONS:
            continue
        out.append({"home": home, "away": away, "kickoff": kickoff})
    return out


def load() -> dict:
    return json.loads((DATA / "feeds.json").read_text(encoding="utf-8"))


def write(payload: dict) -> None:
    encoded = json.dumps(payload, indent=2, ensure_ascii=False)
    (DATA / "feeds.json").write_text(encoded + "\n", encoding="utf-8")
    (ROOT / "data.js").write_text("window.TACTICAL_FEED_DATA = " + encoded + ";\n", encoding="utf-8")


def main() -> int:
    now = datetime.now(timezone.utc)
    payload = load()
    feeds = [f for f in payload.get("feeds", []) if f.get("sourceKey") != "sky:bundesliga-tactical"]
    health = [h for h in payload.get("sourceHealth", []) if h.get("source") != "sky:bundesliga-tactical"]
    try:
        sky, dfl, fixtures = get(SKY_POLICY), get(DFL_PRODUCT), get(FIXTURES)
        if not policy_ok(sky, dfl):
            raise ValueError("Sky/DFL Tactical Feed policy evidence not found")
        rows = parse_topspiele(fixtures, now)
        for row in rows:
            match = f"{row['home']} vs {row['away']}"
            kick = row["kickoff"].isoformat().replace("+00:00", "Z")
            ident = hashlib.sha256((match + kick).encode()).hexdigest()[:16]
            feeds.append({
                "id": "sky-bundesliga-tactical-" + ident,
                "match": match,
                "competition": "Bundesliga",
                "kickoff": kick,
                "type": "tactical",
                "status": "confirmed",
                "platform": "Sky Sport Bundesliga 3 / WOW",
                "language": "English",
                "commentary": "English tactical analysis (DFL Tactical Feed)",
                "usAvailability": False,
                "access": "subscription",
                "territories": ["Germany"],
                "notes": "Sky's current Bundesliga policy assigns a Tactical Feed to the Saturday Topspiel on Sky Sport Bundesliga 3. DFL defines the Tactical Feed as a full-pitch tactical product with expert English-language analysis.",
                "sourceUrl": SKY_POLICY,
                "secondarySourceUrl": DFL_PRODUCT,
                "fixtureSourceUrl": FIXTURES,
                "watchUrl": SKY_WATCH,
                "sourceKey": "sky:bundesliga-tactical",
                "checkedAt": now.isoformat().replace("+00:00", "Z"),
                "verifiedAt": now.isoformat().replace("+00:00", "Z"),
                "exactFixtureVerified": True,
                "publicAccessConfirmed": True,
            })
        health.append({"source": "sky:bundesliga-tactical", "ok": True, "checkedAt": now.isoformat().replace("+00:00", "Z"), "count": len(rows)})
    except Exception as exc:
        health.append({"source": "sky:bundesliga-tactical", "ok": False, "checkedAt": now.isoformat().replace("+00:00", "Z"), "error": type(exc).__name__})
    payload["feeds"], payload["sourceHealth"] = feeds, health
    payload["updatedAt"] = now.isoformat().replace("+00:00", "Z")
    write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
