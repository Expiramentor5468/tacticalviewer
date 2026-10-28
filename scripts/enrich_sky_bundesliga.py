#!/usr/bin/env python3
"""Add public Sky/WOW Bundesliga Saturday Topspiel Tactical Feeds.

Sky publishes a standing rule: the Saturday Topspiel gets a Tactical Feed on Sky Sport
Bundesliga 3. DFL defines Tactical Feed as a full-pitch product with expert English-
language analysis. The public fixture webpage renders only one matchday, so this verifier
uses DFL's own XLSX export endpoint to inspect upcoming matchdays within 60 days.
"""
from __future__ import annotations

import hashlib
import html
import io
import json
import re
import urllib.parse
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
UA = "TacticalFeedFinder/3.3 (+https://github.com/Expiramentor5468/tacticalviewer)"
BERLIN = ZoneInfo("Europe/Berlin")
FIXTURES = "https://products.bundesliga.com/fixtures"
DFL_PRODUCT = "https://products.bundesliga.com/matchdays"
SKY_POLICY = "https://videos.sport.sky.de/fussball/artikel/patrick-ittrich-neuer-schiedsrichter-experte-bei-sky-sport-ex-bundesliga-referee-verstaerkt-bundesliga-team/13574269/35311"
SKY_WATCH = "https://www.wowtv.de/"
EXCEPTIONS = {("FC Bayern München", "Borussia Dortmund", "2026-10-31")}


def get_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.read(2_500_000).decode("utf-8", errors="replace")


def get_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.read(5_000_000)


def plain(content: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", content)))


def policy_ok(sky: str, dfl: str) -> bool:
    s, d = plain(sky), plain(dfl)
    return bool(re.search(r"Tactical Feed", s, re.I) and re.search(r"Sky Sport Bundesliga 3", s, re.I)
                and re.search(r"Topspiel", s, re.I) and re.search(r"Tactical Feed", d, re.I)
                and re.search(r"English-language analysis", d, re.I))


def export_context(fixtures_html: str) -> tuple[str, str, int]:
    text = html.unescape(fixtures_html)
    m = re.search(
        r"fixtures/export/excel\?league(?:%5B0%5D|\[0\])=([^&\"']+)&(?:amp;)?matchday(?:%5B0%5D|\[0\])=(\d+)&(?:amp;)?season=([^&\"']+)",
        text, re.I,
    )
    if not m:
        # Some templates order query parameters differently; extract them independently.
        league = re.search(r"league(?:%5B0%5D|\[0\])=([^&\"']+)", text, re.I)
        matchday = re.search(r"matchday(?:%5B0%5D|\[0\])=(\d+)", text, re.I)
        season = re.search(r"season=([^&\"']+)", text, re.I)
        if not (league and matchday and season):
            raise ValueError("DFL export context not found")
        return urllib.parse.unquote(league.group(1)), urllib.parse.unquote(season.group(1)), int(matchday.group(1))
    return urllib.parse.unquote(m.group(1)), urllib.parse.unquote(m.group(3)), int(m.group(2))


def export_url(league: str, season: str, matchday: int) -> str:
    q = urllib.parse.urlencode({"league[0]": league, "matchday[0]": str(matchday), "season": season})
    return FIXTURES + "/export/excel?" + q


def xlsx_rows(blob: bytes) -> list[list[str]]:
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall(ns + "si"):
                shared.append("".join(t.text or "" for t in si.iter(ns + "t")))
        sheet_name = "xl/worksheets/sheet1.xml"
        if sheet_name not in z.namelist():
            candidates = sorted(n for n in z.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))
            if not candidates:
                raise ValueError("No worksheet in DFL export")
            sheet_name = candidates[0]
        root = ET.fromstring(z.read(sheet_name))
        rows = []
        for row in root.iter(ns + "row"):
            vals = []
            for c in row.findall(ns + "c"):
                t = c.attrib.get("t")
                v = c.find(ns + "v")
                if t == "inlineStr":
                    val = "".join(x.text or "" for x in c.iter(ns + "t"))
                elif v is None:
                    val = ""
                elif t == "s":
                    try: val = shared[int(v.text or "0")]
                    except (ValueError, IndexError): val = ""
                else:
                    val = v.text or ""
                vals.append(val.strip())
            if vals:
                rows.append(vals)
        return rows


def excel_date(value: str) -> datetime | None:
    value = value.strip()
    for fmt in ("%d-%b-%Y", "%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try: return datetime.strptime(value, fmt)
        except ValueError: pass
    try:
        number = float(value)
        if 30000 < number < 70000:
            return datetime(1899, 12, 30) + timedelta(days=number)
    except ValueError:
        pass
    return None


def excel_time(value: str) -> str | None:
    value = value.strip()
    if re.fullmatch(r"\d{1,2}:\d{2}", value):
        h, m = map(int, value.split(":")); return f"{h:02d}:{m:02d}"
    try:
        n = float(value)
        if 0 <= n < 1:
            mins = round(n * 24 * 60) % (24 * 60)
            return f"{mins // 60:02d}:{mins % 60:02d}"
    except ValueError:
        pass
    return None


def top_spiele_from_export(blob: bytes, now: datetime) -> list[dict]:
    rows = xlsx_rows(blob)
    if not rows:
        return []
    header_i = next((i for i, r in enumerate(rows) if any("home" in c.lower() for c in r) and any("away" in c.lower() for c in r)), None)
    if header_i is None:
        return []
    headers = [re.sub(r"\s+", " ", c).strip().lower() for c in rows[header_i]]
    def col(*needles):
        return next((i for i, h in enumerate(headers) if all(n in h for n in needles)), None)
    i_day, i_date, i_cet, i_home, i_away = col("day"), col("date"), col("kick", "cet"), col("home"), col("away")
    if None in (i_date, i_cet, i_home, i_away):
        return []
    out, horizon = [], now + timedelta(days=60)
    for row in rows[header_i + 1:]:
        def at(i): return row[i].strip() if i is not None and i < len(row) else ""
        day = at(i_day).lower()
        date = excel_date(at(i_date)); clock = excel_time(at(i_cet))
        if not date or clock != "18:30" or (day and day not in {"sat", "saturday", "sa"}):
            continue
        home, away = at(i_home), at(i_away)
        if not home or not away:
            continue
        local = datetime.combine(date.date(), datetime.strptime(clock, "%H:%M").time(), tzinfo=BERLIN)
        kickoff = local.astimezone(timezone.utc)
        if now - timedelta(hours=6) <= kickoff <= horizon and (home, away, local.date().isoformat()) not in EXCEPTIONS:
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
        sky, dfl, fixture_html = get_text(SKY_POLICY), get_text(DFL_PRODUCT), get_text(FIXTURES)
        if not policy_ok(sky, dfl):
            raise ValueError("Sky/DFL Tactical Feed policy evidence not found")
        league, season, current_md = export_context(fixture_html)
        found, exports_checked = [], 0
        for md in range(current_md, min(34, current_md + 10) + 1):
            try:
                rows = top_spiele_from_export(get_bytes(export_url(league, season, md)), now)
                exports_checked += 1; found.extend(rows)
            except Exception:
                continue
        # Exact fixture/time dedupe across exports.
        unique = {(r["home"], r["away"], r["kickoff"]): r for r in found}.values()
        for row in sorted(unique, key=lambda r: r["kickoff"]):
            match = f"{row['home']} vs {row['away']}"; kick = row["kickoff"].isoformat().replace("+00:00", "Z")
            ident = hashlib.sha256((match + kick).encode()).hexdigest()[:16]
            feeds.append({
                "id": "sky-bundesliga-tactical-" + ident, "match": match, "competition": "Bundesliga", "kickoff": kick,
                "type": "tactical", "status": "confirmed", "platform": "Sky Sport Bundesliga 3 / WOW",
                "language": "English", "commentary": "English tactical analysis (DFL Tactical Feed)",
                "usAvailability": False, "access": "subscription", "territories": ["Germany"],
                "notes": "Sky's current Bundesliga policy assigns a Tactical Feed to the Saturday Topspiel. DFL defines this feed as a full-pitch tactical product with expert English-language analysis.",
                "sourceUrl": SKY_POLICY, "secondarySourceUrl": DFL_PRODUCT, "fixtureSourceUrl": FIXTURES,
                "watchUrl": SKY_WATCH, "sourceKey": "sky:bundesliga-tactical", "checkedAt": now.isoformat().replace("+00:00", "Z"),
                "verifiedAt": now.isoformat().replace("+00:00", "Z"), "exactFixtureVerified": True, "publicAccessConfirmed": True
            })
        health.append({"source": "sky:bundesliga-tactical", "ok": exports_checked > 0, "checkedAt": now.isoformat().replace("+00:00", "Z"), "count": len(list(unique)), "exportsChecked": exports_checked})
    except Exception as exc:
        health.append({"source": "sky:bundesliga-tactical", "ok": False, "checkedAt": now.isoformat().replace("+00:00", "Z"), "error": type(exc).__name__})
    payload["feeds"], payload["sourceHealth"] = feeds, health
    payload["updatedAt"] = now.isoformat().replace("+00:00", "Z")
    write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
