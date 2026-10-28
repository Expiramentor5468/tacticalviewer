#!/usr/bin/env python3
"""Monitor known branded alternate-feed products.

Discovery only. Exact fixture, English audio, public viewing route and territory are
required before a lead can become confirmed. Leads that clearly duplicate an already
confirmed event are suppressed.
"""
from __future__ import annotations
import hashlib, html, json, re, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"data"; UA="TacticalFeedFinder/3.4 (+https://github.com/Expiramentor5468/tacticalviewer)"
MONITORS=[
 {"key":"cbs:golazo-tactical","competition":"UEFA Champions League / Serie A","query":'("Tactical Cam" OR "tactical cam") "CBS Sports Golazo" (site:cbssports.com OR site:paramountpressexpress.com)',"brand":"CBS Sports Golazo Network — Tactical Cam","language":"English","pattern":r"\bTactical\s+Cam\b"},
 {"key":"mls:alternate-cameras","competition":"MLS","query":'MLS ("Ref Cam" OR "alternate broadcast" OR "TikTok Player Spotlight") site:mlssoccer.com',"brand":"MLS / Apple TV alternate cameras","language":"English","pattern":r"\bRef\s+Cam\b|\balternate\s+broadcast\b|TikTok\s+Player\s+Spotlight|Player\s+Spotlight.{0,50}(?:stream|live)"},
 {"key":"premierleague:alternate-cameras","competition":"Premier League","query":'Premier League ("Game Mode" OR "tactical cam" OR "tactical feed") (site:premierleague.com OR site:nbcsports.com OR site:sky.com)',"brand":"Premier League alternate tactical view","language":"English","pattern":r"\bGame\s+Mode\b|\btactical\s+(?:cam|feed)\b"},
 {"key":"ligue1:expert-mode","competition":"Ligue 1","query":'"Ligue 1+" "Expert Mode" (site:ligue1.com OR site:lfp.fr OR site:svgeurope.org)',"brand":"Ligue 1+ — Expert Mode","language":"Unknown","pattern":r"\bExpert\s+Mode\b"},
]
STOP={"the","and","for","with","from","this","that","live","sports","sport","soccer","football","broadcast","alternate","match","team","bring","brings","network","stream"}
def stamp(dt):return dt.astimezone(timezone.utc).isoformat().replace("+00:00","Z")
def get(url):
 req=urllib.request.Request(url,headers={"User-Agent":UA})
 with urllib.request.urlopen(req,timeout=20) as r:return r.read(2_000_000).decode("utf-8",errors="replace")
def rss_url(query):return "https://news.google.com/rss/search?q="+urllib.parse.quote(query+" when:60d")+"&hl=en-US&gl=US&ceid=US:en"
def tokens(text):return {w for w in re.findall(r"[a-z0-9]+",(text or "").lower()) if len(w)>2 and w not in STOP}
def duplicate_of_confirmed(candidate,confirmed):
 ct=tokens(candidate.get("match",""))|tokens(candidate.get("platform",""))
 for f in confirmed:
  if f.get("competition")!=candidate.get("competition"):continue
  ft=tokens(" ".join(str(f.get(k,"")) for k in("match","platform","commentary","notes")))
  if len(ct & ft)>=4:return True
 return False
def parse(xml,monitor,now):
 root=ET.fromstring(xml);out=[];pattern=re.compile(monitor["pattern"],re.I|re.S)
 for item in root.findall("./channel/item")[:40]:
  title=html.unescape(item.findtext("title",""));desc=re.sub("<[^>]+>"," ",html.unescape(item.findtext("description","")));body=title+" "+desc
  if not pattern.search(body):continue
  try:
   published=parsedate_to_datetime(item.findtext("pubDate",""))
   if published.tzinfo is None or not now-timedelta(days=60)<=published<=now+timedelta(hours=1):continue
  except (ValueError,TypeError):continue
  link=item.findtext("link","")
  if not link.startswith(("https://","http://")):continue
  ident=hashlib.sha256((monitor["key"]+link).encode()).hexdigest()[:16]
  out.append({"id":"brand-monitor-"+ident,"match":title,"competition":monitor["competition"],"kickoff":None,"type":"alternate","status":"candidate","platform":monitor["brand"],"language":monitor["language"],"commentary":"English" if monitor["language"]=="English" else "English audio not yet verified","usAvailability":None,"access":"unknown","territories":[],"notes":"Branded-product lead. Exact fixture, public viewing route, territory and kickoff must be verified before confirmation.","sourceUrl":link,"sourcePublishedAt":stamp(published),"checkedAt":stamp(now),"sourceKey":monitor["key"],"exactFixtureVerified":False,"publicAccessConfirmed":False})
 return out
def load():return json.loads((DATA/"feeds.json").read_text(encoding="utf-8"))
def write(payload):
 encoded=json.dumps(payload,indent=2,ensure_ascii=False);(DATA/"feeds.json").write_text(encoded+"\n",encoding="utf-8");(ROOT/"data.js").write_text("window.TACTICAL_FEED_DATA = "+encoded+";\n",encoding="utf-8")
def main():
 now=datetime.now(timezone.utc);payload=load();keys={m["key"] for m in MONITORS};feeds=[f for f in payload.get("feeds",[]) if f.get("sourceKey") not in keys];confirmed=[f for f in feeds if f.get("status")=="confirmed"];health=[h for h in payload.get("sourceHealth",[]) if h.get("source") not in keys]
 for monitor in MONITORS:
  try:
   raw=parse(get(rss_url(monitor["query"])),monitor,now);rows=[r for r in raw if not duplicate_of_confirmed(r,confirmed)];feeds.extend(rows);health.append({"source":monitor["key"],"ok":True,"checkedAt":stamp(now),"count":len(rows),"duplicatesSuppressed":len(raw)-len(rows)})
  except Exception as exc:health.append({"source":monitor["key"],"ok":False,"checkedAt":stamp(now),"error":type(exc).__name__})
 seen=set();merged=[]
 for f in feeds:
  if f.get("id") in seen:continue
  seen.add(f.get("id"));merged.append(f)
 payload["feeds"],payload["sourceHealth"],payload["updatedAt"]=merged,health,stamp(now);write(payload);return 0
if __name__=="__main__":raise SystemExit(main())
