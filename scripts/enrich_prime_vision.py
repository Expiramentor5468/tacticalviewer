#!/usr/bin/env python3
"""Add Amazon Prime Video UEFA Champions League Prime Vision fixtures.

The UCL help page is client-rendered: its public rendered content confirms Prime Vision,
English default commentary, and UK/ROI territories, but urllib cannot extract those
sentences from the raw shell. Those reviewed facts are therefore explicit constants tied
to the official help URL; every run still requires that official page to be reachable,
Amazon's current rights page to advertise Prime Vision, and the monthly schedule to name
the exact fixture.
"""
from __future__ import annotations
import calendar, hashlib, html, json, re, urllib.error, urllib.request
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from update_feeds import retain_evidence
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/"data";UA="TacticalFeedFinder/3.4 (+https://github.com/Expiramentor5468/tacticalviewer)";LONDON=ZoneInfo("Europe/London")
PRIME_POLICY="https://www.aboutamazon.co.uk/news/entertainment/champions-league-prime-video-uk-renewal"
PRIME_HELP="https://www.primevideo.com/salp/ucl-help/?content-id=amzn1.sym.dd781929-775e-45af-be91-40c39fedce52"
PRIME_WATCH="https://www.primevideo.com/"
# Reviewed against PRIME_HELP on 2026-10-28. Keep territory statements conservative.
TERRITORIES=["United Kingdom","Republic of Ireland","Channel Islands","Isle of Man"]
LANGUAGE="English"
POLICY_REVIEWED_AT="2026-10-28T00:00:00Z"  # Date of actual review, never the fetch time.
MONTHS={name.lower():i for i,name in enumerate(calendar.month_name) if name}
END_MARKERS=("nba on prime video","nba","upcoming with rent","upcoming to rent","premier league","formula 1","wta","nfl","movies","tv shows","stories we think you’ll like","page overview","more from amazon")
class VisibleText(HTMLParser):
 def __init__(self):super().__init__();self.parts=[];self.hidden=0
 def handle_starttag(self,tag,attrs):
  if tag in{"script","style","noscript"}:self.hidden+=1
  elif not self.hidden and tag in{"p","li","h1","h2","h3","h4","div","br"}:self.parts.append("\n")
 def handle_endtag(self,tag):
  if tag in{"script","style","noscript"} and self.hidden:self.hidden-=1
  elif not self.hidden and tag in{"p","li","h1","h2","h3","h4","div"}:self.parts.append("\n")
 def handle_data(self,data):
  if not self.hidden:self.parts.append(data)
 def text(self):
  raw=html.unescape("".join(self.parts)).replace("\xa0"," ");return "\n".join(re.sub(r"\s+"," ",line).strip(" -*•\t") for line in raw.splitlines() if line.strip())
def visible_text(content):p=VisibleText();p.feed(content);return p.text()
def get(url):
 req=urllib.request.Request(url,headers={"User-Agent":UA})
 with urllib.request.urlopen(req,timeout=20) as r:return r.read(2_000_000).decode("utf-8",errors="replace")
def month_url(year,month):return f"https://www.aboutamazon.co.uk/news/entertainment/whats-on-prime-video-uk-{calendar.month_name[month].lower()}-{year}"
def add_months(year,month,offset):n=year*12+month-1+offset;return n//12,n%12+1
def parse_date_line(line,default_year):
 m=re.search(r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?\s*(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)(?:\s+(\d{4}))?$",line,re.I)
 if not m:return None
 month=MONTHS.get(m.group(2).lower());return(int(m.group(3) or default_year),month,int(m.group(1))) if month else None
def parse_match_line(line):
 m=re.match(r"(.+?)\s+vs\.?\s+(.+?)\s*\((\d{1,2}:\d{2}\s*(?:am|pm))\)\s*$",line,re.I)
 if not m:return None
 return f"{re.sub(r'\s+',' ',m.group(1)).strip()} vs {re.sub(r'\s+',' ',m.group(2)).strip()}",m.group(3).replace(" ","").lower()
def parse_section(lines,start,page_year,now):
 stop=len(lines)
 for i in range(start,len(lines)):
  low=lines[i].lower()
  if i>start and any(low==m or low.startswith(m+" ") for m in END_MARKERS):stop=i;break
 current=None;rows=[];horizon=now+timedelta(days=60)
 for line in lines[start:stop]:
  d=parse_date_line(line,page_year)
  if d:current=d;continue
  match=parse_match_line(line)
  if not match or not current:continue
  name,clock=match
  try:local=datetime.strptime(f"{current[0]}-{current[1]:02d}-{current[2]:02d} {clock}","%Y-%m-%d %I:%M%p").replace(tzinfo=LONDON)
  except ValueError:continue
  kickoff=local.astimezone(timezone.utc)
  if now-timedelta(hours=6)<=kickoff<=horizon:rows.append({"match":name,"kickoff":kickoff})
 return rows
def parse_month_page(content,page_year,now):
 lines=visible_text(content).splitlines();heads=[i for i,l in enumerate(lines) if l.strip().lower()=="uefa champions league"];return max((parse_section(lines,i+1,page_year,now) for i in heads),key=len,default=[])
def policy_ok(content):
 text=re.sub(r"\s+"," ",visible_text(content));return bool(re.search(r"Prime Vision",text,re.I) and re.search(r"top[- ]pick Tuesday match",text,re.I) and re.search(r"2030/31|2031",text,re.I))
def load():
 p=DATA/"feeds.json";return json.loads(p.read_text(encoding="utf-8")) if p.exists() else{"feeds":[]}
def write(p):
 encoded=json.dumps(p,indent=2,ensure_ascii=False);(DATA/"feeds.json").write_text(encoded+"\n",encoding="utf-8");(ROOT/"data.js").write_text("window.TACTICAL_FEED_DATA = "+encoded+";\n",encoding="utf-8")
def main():
 now=datetime.now(timezone.utc);p=load();previous=p.get("feeds",[]);feeds=[f for f in p.get("feeds",[]) if f.get("sourceKey")!="amazon:prime-vision"];health=[h for h in p.get("sourceHealth",[]) if h.get("source")!="amazon:prime-vision"]
 try:
  policy=get(PRIME_POLICY);help_shell=get(PRIME_HELP);product_ok=policy_ok(policy) and len(help_shell)>100
  if not product_ok:raise ValueError("Prime Vision evidence unavailable")
  err=None
 except Exception as exc:product_ok=False;err=type(exc).__name__
 for old in previous:
  if old.get("sourceKey")=="amazon:prime-vision":
   old["policyReviewedAt"]=POLICY_REVIEWED_AT
 reviewed=datetime.fromisoformat(POLICY_REVIEWED_AT.replace("Z","+00:00"));policy_fresh=now-timedelta(days=7)<=reviewed<=now
 access_ok=product_ok and policy_fresh
 found=[];checked=0;page_errors=[]
 for offset in range(3):
  year,month=add_months(now.year,now.month,offset);url=month_url(year,month)
  try:
   content=get(url);checked+=1
   for row in parse_month_page(content,year,now):
    kickoff=row["kickoff"];ident=hashlib.sha256((row["match"]+kickoff.isoformat()).encode()).hexdigest()[:16]
    found.append({"id":"prime-vision-"+ident,"match":row["match"],"competition":"UEFA Champions League","kickoff":kickoff.isoformat().replace("+00:00","Z"),"type":"alternate","status":"confirmed" if access_ok else "candidate","platform":"Prime Video — Prime Vision","language":LANGUAGE if access_ok else "Unknown","commentary":"English default commentary; Prime Vision adds live tactical/data overlays" if access_ok else "English audio not yet verified","usAvailability":False if access_ok else None,"access":"subscription" if access_ok else "unknown","territories":TERRITORIES if access_ok else [],"notes":"Amazon's monthly schedule confirms the exact UCL top-pick fixture. The official UCL help page confirms Prime Vision, English default commentary, and UK/Republic of Ireland access. Prime Vision is data-enhanced alternate coverage, not a persistent full-pitch wide camera. Access evidence expires seven days after the recorded policy review.","sourceUrl":url,"watchUrl":PRIME_WATCH if access_ok else None,"sourceKey":"amazon:prime-vision","checkedAt":now.isoformat().replace("+00:00","Z"),"verifiedAt":POLICY_REVIEWED_AT if access_ok else None,"policyReviewedAt":POLICY_REVIEWED_AT,"exactFixtureVerified":True,"publicAccessConfirmed":access_ok,"secondarySourceUrl":PRIME_HELP,"policySourceUrl":PRIME_POLICY})
  except urllib.error.HTTPError as exc:
   if exc.code!=404:page_errors.append(f"{calendar.month_name[month]}:{type(exc).__name__}")
  except Exception as exc:page_errors.append(f"{calendar.month_name[month]}:{type(exc).__name__}")
 complete=product_ok and not page_errors and checked>0
 if not complete:
  retained=[f for f in previous if f.get("sourceKey")=="amazon:prime-vision"]
  found=found+retained if product_ok else retained+found
 seen=set();merged=[]
 for item in retain_evidence(feeds+found,now):
  key=(item.get("competition"),item.get("match"),item.get("kickoff"),item.get("platform"))
  if key in seen:continue
  seen.add(key);merged.append(item)
 p["feeds"]=merged;health.append({"source":"amazon:prime-vision","ok":complete,"checkedAt":now.isoformat().replace("+00:00","Z"),"count":len(found),"pagesChecked":checked,"evidenceMode":"official-help-reviewed/client-rendered","policyReviewedAt":POLICY_REVIEWED_AT,"policyReviewExpired":not policy_fresh,**({"error":err} if err else{}),**({"pageErrors":page_errors} if page_errors else{})});p["sourceHealth"]=health;p["updatedAt"]=now.isoformat().replace("+00:00","Z");write(p);print(f"Prime Vision enrichment: {len(found)} upcoming fixture(s), {checked} monthly page(s) checked");return 0 if complete else 2
if __name__=="__main__":raise SystemExit(main())
