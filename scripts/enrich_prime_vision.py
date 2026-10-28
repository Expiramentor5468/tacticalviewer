#!/usr/bin/env python3
"""Add Amazon Prime Video UEFA Champions League Prime Vision fixtures.

Uses Amazon-owned public sources only:
- About Amazon UK monthly Prime Video schedule pages for exact UCL fixture/date/time.
- About Amazon UK's UCL rights/Prime Vision policy page for the recurring product.

Prime Vision is data-enhanced alternate coverage, not a persistent full-pitch wide cam.
"""
from __future__ import annotations

import calendar
import hashlib
import html
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
UA = "TacticalFeedFinder/3.2 (+https://github.com/Expiramentor5468/tacticalviewer)"
LONDON = ZoneInfo("Europe/London")
PRIME_POLICY = "https://www.aboutamazon.co.uk/news/entertainment/champions-league-prime-video-uk-renewal"
PRIME_WATCH = "https://www.primevideo.com/"
MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
END_MARKERS = (
    "nba on prime video", "nba", "upcoming with rent", "upcoming to rent",
    "premier league", "formula 1", "wta", "nfl", "movies", "tv shows",
    "stories we think you’ll like", "page overview", "more from amazon",
)


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.hidden += 1
        elif not self.hidden and tag in {"p", "li", "h1", "h2", "h3", "h4", "div", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self.hidden:
            self.hidden -= 1
        elif not self.hidden and tag in {"p", "li", "h1", "h2", "h3", "h4", "div"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)

    def text(self) -> str:
        raw = html.unescape("".join(self.parts)).replace("\xa0", " ")
        return "\n".join(
            re.sub(r"\s+", " ", line).strip(" -*•\t")
            for line in raw.splitlines()
            if line.strip()
        )


def visible_text(content: str) -> str:
    parser = VisibleText()
    parser.feed(content)
    return parser.text()


def get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.read(2_000_000).decode("utf-8", errors="replace")


def month_url(year: int, month: int) -> str:
    return f"https://www.aboutamazon.co.uk/news/entertainment/whats-on-prime-video-uk-{calendar.month_name[month].lower()}-{year}"


def add_months(year: int, month: int, offset: int) -> tuple[int, int]:
    n = year * 12 + month - 1 + offset
    return n // 12, n % 12 + 1


def parse_date_line(line: str, default_year: int) -> tuple[int, int, int] | None:
    m = re.search(
        r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?\s*"
        r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)(?:\s+(\d{4}))?$",
        line,
        re.I,
    )
    if not m:
        return None
    month = MONTHS.get(m.group(2).lower())
    return (int(m.group(3) or default_year), month, int(m.group(1))) if month else None


def parse_match_line(line: str) -> tuple[str, str] | None:
    m = re.match(r"(.+?)\s+vs\.?\s+(.+?)\s*\((\d{1,2}:\d{2}\s*(?:am|pm))\)\s*$", line, re.I)
    if not m:
        return None
    home = re.sub(r"\s+", " ", m.group(1)).strip()
    away = re.sub(r"\s+", " ", m.group(2)).strip()
    return f"{home} vs {away}", m.group(3).replace(" ", "").lower()


def parse_section(lines: list[str], start: int, page_year: int, now: datetime) -> list[dict]:
    stop = len(lines)
    for i in range(start, len(lines)):
        low = lines[i].lower()
        if i > start and any(low == marker or low.startswith(marker + " ") for marker in END_MARKERS):
            stop = i
            break

    current_date: tuple[int, int, int] | None = None
    rows: list[dict] = []
    horizon = now + timedelta(days=60)
    for line in lines[start:stop]:
        parsed_date = parse_date_line(line, page_year)
        if parsed_date:
            current_date = parsed_date
            continue
        match = parse_match_line(line)
        if not match or not current_date:
            continue
        match_name, clock = match
        try:
            local = datetime.strptime(
                f"{current_date[0]}-{current_date[1]:02d}-{current_date[2]:02d} {clock}",
                "%Y-%m-%d %I:%M%p",
            ).replace(tzinfo=LONDON)
        except ValueError:
            continue
        kickoff = local.astimezone(timezone.utc)
        if now - timedelta(hours=6) <= kickoff <= horizon:
            rows.append({"match": match_name, "kickoff": kickoff})
    return rows


def parse_month_page(content: str, page_year: int, now: datetime) -> list[dict]:
    lines = visible_text(content).splitlines()
    headings = [i for i, line in enumerate(lines) if line.strip().lower() == "uefa champions league"]
    if not headings:
        return []
    # Amazon repeats the section name in navigation/footer overviews. Evaluate every
    # occurrence and keep the section that actually contains dated match rows.
    candidates = [parse_section(lines, i + 1, page_year, now) for i in headings]
    return max(candidates, key=len, default=[])


def prime_vision_policy_available(content: str) -> bool:
    text = re.sub(r"\s+", " ", visible_text(content))
    return bool(
        re.search(r"Prime Vision", text, re.I)
        and re.search(r"top[- ]pick Tuesday match", text, re.I)
        and re.search(r"this season", text, re.I)
    )


def load_payload() -> dict:
    path = DATA / "feeds.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"feeds": []}


def write_payload(payload: dict) -> None:
    encoded = json.dumps(payload, indent=2, ensure_ascii=False)
    (DATA / "feeds.json").write_text(encoded + "\n", encoding="utf-8")
    (ROOT / "data.js").write_text("window.TACTICAL_FEED_DATA = " + encoded + ";\n", encoding="utf-8")


def main() -> int:
    now = datetime.now(timezone.utc)
    payload = load_payload()
    feeds = [f for f in payload.get("feeds", []) if f.get("sourceKey") != "amazon:prime-vision"]
    health = [h for h in payload.get("sourceHealth", []) if h.get("source") != "amazon:prime-vision"]

    try:
        policy_content = get(PRIME_POLICY)
        if not prime_vision_policy_available(policy_content):
            raise ValueError("Prime Vision policy wording not found")
        product_ok = True
        policy_error = None
    except Exception as exc:
        product_ok = False
        policy_error = type(exc).__name__

    found: list[dict] = []
    pages_checked = 0
    page_errors: list[str] = []
    for offset in range(3):
        year, month = add_months(now.year, now.month, offset)
        url = month_url(year, month)
        try:
            content = get(url)
            pages_checked += 1
            for row in parse_month_page(content, year, now):
                kickoff = row["kickoff"]
                ident = hashlib.sha256((row["match"] + kickoff.isoformat()).encode()).hexdigest()[:16]
                found.append({
                    "id": "prime-vision-" + ident,
                    "match": row["match"],
                    "competition": "UEFA Champions League",
                    "kickoff": kickoff.isoformat().replace("+00:00", "Z"),
                    "type": "alternate",
                    "status": "confirmed" if product_ok else "candidate",
                    "platform": "Prime Video — Prime Vision",
                    "commentary": "English; Prime Vision adds live tactical/data overlays",
                    "usAvailability": False if product_ok else None,
                    "access": "subscription" if product_ok else "unknown",
                    "territories": ["United Kingdom"] if product_ok else [],
                    "notes": (
                        "Amazon's official monthly schedule confirms this as Prime Video's UCL top-pick fixture. "
                        "Amazon's official UCL policy confirms Prime Vision is part of its Champions League coverage this season. "
                        "Prime Vision adds live statistics, passing options and tactical analytics; it is not a persistent full-pitch wide camera."
                    ),
                    "sourceUrl": url,
                    "watchUrl": PRIME_WATCH if product_ok else None,
                    "sourceKey": "amazon:prime-vision",
                    "checkedAt": now.isoformat().replace("+00:00", "Z"),
                    "verifiedAt": now.isoformat().replace("+00:00", "Z") if product_ok else None,
                    "exactFixtureVerified": True,
                    "publicAccessConfirmed": product_ok,
                    "secondarySourceUrl": PRIME_POLICY,
                })
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                page_errors.append(f"{calendar.month_name[month]}:{type(exc).__name__}")
        except Exception as exc:
            page_errors.append(f"{calendar.month_name[month]}:{type(exc).__name__}")

    seen = set()
    merged = []
    for item in feeds + found:
        key = (item.get("competition"), item.get("match"), item.get("kickoff"), item.get("platform"))
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)

    payload["feeds"] = merged
    health.append({
        "source": "amazon:prime-vision",
        "ok": product_ok and not page_errors and pages_checked > 0,
        "checkedAt": now.isoformat().replace("+00:00", "Z"),
        "count": len(found),
        "pagesChecked": pages_checked,
        **({"error": policy_error} if policy_error else {}),
        **({"pageErrors": page_errors} if page_errors else {}),
    })
    payload["sourceHealth"] = health
    payload["updatedAt"] = now.isoformat().replace("+00:00", "Z")
    write_payload(payload)
    print(f"Prime Vision enrichment: {len(found)} upcoming fixture(s), {pages_checked} monthly page(s) checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
