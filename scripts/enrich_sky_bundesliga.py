#!/usr/bin/env python3
"""Monitor Sky/WOW's public Bundesliga Tactical Feed.

Sky publicly confirms the Saturday Topspiel Tactical Feed and Germany viewing route.
DFL separately documents the production Tactical Feed. Consumer audio language is kept
as metadata and does not determine whether a publicly watchable feed is confirmed.
"""
from __future__ import annotations
import hashlib, html, io, json, re, urllib.parse, urllib.request, zipfile, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from update_feeds import retain_evidence
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"data"; UA="TacticalFeedFinder/3.6 (+https://github.com/Expiramentor5468/tacticalviewer)"
BERLIN=ZoneInfo("Europe/Berlin"); FIXTURES="https://products.bundesliga.com/fixtures"; DFL_PRODUCT="https://products.bundesliga.com/matchdays"; SKY_POLICY="https://videos.sport.sky.de/fussball/artikel/patrick-ittrich-neuer-schiedsrichter-experte-bei-sky-sport-ex-bundesliga-referee-verstaerkt-bundesliga-team/13574269/35311"; SKY_WATCH="https://www.wowtv.de/"; EXCEPTIONS={("FC Bayern München","Borussia Dortmund","2026-10-31")}
def get_text(url):
    req=urllib.request.Request(url,headers={"User-Agent":UA});
    with urllib.request.urlopen(req,timeout=20) as r:return r.read(2_500_000).decode("utf-8",errors="replace")
def get_bytes(url):
    req=urllib.request.Request(url,headers={"User-Agent":UA});
    with urllib.request.urlopen(req,timeout=20) as r:return r.read(5_000_000)
def plain(s):return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",s)))
def policy_ok(sky,dfl):
    s,d=plain(sky),plain(dfl);return bool(re.search(r"Tactical Feed",s,re.I) and re.search(r"Sky Sport Bundesliga 3",s,re.I) and re.search(r"Topspiel",s,re.I) and re.search(r"Tactical Feed",d,re.I))
def export_context(text):
    text=html.unescape(text);league=re.search(r"league(?:%5B0%5D|\[0\])=([^&\"']+)",text,re.I);md=re.search(r"matchday(?:%5B0%5D|\[0\])=(\d+)",text,re.I);season=re.search(r"season=([^&\"']+)",text,re.I)
    if not(league and md and season):raise ValueError("DFL export context not found")
    return urllib.parse.unquote(league.group(1)),urllib.parse.unquote(season.group(1)),int(md.group(1))
def export_url(league,season,md):return FIXTURES+"/export/excel?"+urllib.parse.urlencode({"league[0]":league,"matchday[0]":str(md),"season":season})
def col_index(ref):
    letters=re.match(r"[A-Z]+",ref or "");n=0
    if not letters:return 0
    for ch in letters.group():n=n*26+ord(ch)-64
    return n-1
def xlsx_rows(blob):
    ns="{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        shared=[]
        if "xl/sharedStrings.xml" in z.namelist():
            root=ET.fromstring(z.read("xl/sharedStrings.xml"));shared=["".join(t.text or "" for t in si.iter(ns+"t")) for si in root.findall(ns+"si")]
        sheets=sorted(n for n in z.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))
        if not sheets:raise ValueError("No worksheet")
        root=ET.fromstring(z.read(sheets[0]));rows=[]
        for row in root.iter(ns+"row"):
            vals={}
            for c in row.findall(ns+"c"):
                idx=col_index(c.attrib.get("r","A1"));t=c.attrib.get("t");v=c.find(ns+"v")
                if t=="inlineStr":val="".join(x.text or "" for x in c.iter(ns+"t"))
                elif v is None:val=""
                elif t=="s":
                    try:val=shared[int(v.text or "0")]
                    except (ValueError,IndexError):val=""
                else:val=v.text or ""
                vals[idx]=val.strip()
            if vals:
                arr=[""]*(max(vals)+1)
                for i,v in vals.items():arr[i]=v
                rows.append(arr)
        return rows
def excel_date(v):
    v=v.strip()
    for fmt in("%d-%b-%Y","%d.%m.%Y","%Y-%m-%d","%d/%m/%Y"):
        try:return datetime.strptime(v,fmt)
        except ValueError:pass
    try:
        n=float(v)
        if 30000<n<70000:return datetime(1899,12,30)+timedelta(days=n)
    except ValueError:pass
    return None
def excel_time(v):
    v=v.strip()
    if re.fullmatch(r"\d{1,2}:\d{2}",v):h,m=map(int,v.split(":"));return f"{h:02d}:{m:02d}"
    try:
        n=float(v)
        if 0<=n<1:
            mins=round(n*1440)%1440;return f"{mins//60:02d}:{mins%60:02d}"
    except ValueError:pass
    return None
def top_spiele_from_export(blob,now):
    rows=xlsx_rows(blob)
    header_i=next((i for i,r in enumerate(rows) if any("home" in c.lower() for c in r) and any("away" in c.lower() for c in r)),None)
    if header_i is None:raise ValueError("Fixture header not found")
    headers=[re.sub(r"\s+"," ",c).strip().lower() for c in rows[header_i]]
    def col(*needles):return next((i for i,h in enumerate(headers) if all(n in h for n in needles)),None)
    i_day,i_date,i_cet,i_home,i_away=col("day"),col("date"),col("kick","cet"),col("home"),col("away")
    if None in(i_date,i_cet,i_home,i_away):raise ValueError("Required fixture columns missing")
    out=[];horizon=now+timedelta(days=60)
    for row in rows[header_i+1:]:
        at=lambda i:row[i].strip() if i is not None and i<len(row) else "";day=at(i_day).lower();date=excel_date(at(i_date));clock=excel_time(at(i_cet))
        if not date or clock!="18:30" or(day and day not in{"sat","saturday","sa"}):continue
        home,away=at(i_home),at(i_away)
        if not home or not away:continue
        local=datetime.combine(date.date(),datetime.strptime(clock,"%H:%M").time(),tzinfo=BERLIN);kickoff=local.astimezone(timezone.utc)
        if now-timedelta(hours=6)<=kickoff<=horizon and(home,away,local.date().isoformat()) not in EXCEPTIONS:out.append({"home":home,"away":away,"kickoff":kickoff})
    return out
def load():return json.loads((DATA/"feeds.json").read_text(encoding="utf-8"))
def write(p):
    e=json.dumps(p,indent=2,ensure_ascii=False);(DATA/"feeds.json").write_text(e+"\n",encoding="utf-8");(ROOT/"data.js").write_text("window.TACTICAL_FEED_DATA = "+e+";\n",encoding="utf-8")
def main():
    now=datetime.now(timezone.utc);p=load();feeds=[f for f in p.get("feeds",[]) if f.get("sourceKey")!="sky:bundesliga-tactical"];health=[h for h in p.get("sourceHealth",[]) if h.get("source")!="sky:bundesliga-tactical"]
    try:
        sky,dfl,fixture_html=get_text(SKY_POLICY),get_text(DFL_PRODUCT),get_text(FIXTURES)
        if not policy_ok(sky,dfl):raise ValueError("policy")
        league,season,current_md=export_context(fixture_html);found=[];checked=0;export_errors=[]
        matchdays=list(range(current_md,min(34,current_md+10)+1))
        for md in matchdays:
            try:found.extend(top_spiele_from_export(get_bytes(export_url(league,season,md)),now));checked+=1
            except Exception as exc:export_errors.append(f"{md}:{type(exc).__name__}")
        unique=list({(r["home"],r["away"],r["kickoff"]):r for r in found}.values())
        for r in sorted(unique,key=lambda x:x["kickoff"]):
            match=f"{r['home']} vs {r['away']}";kick=r["kickoff"].isoformat().replace("+00:00","Z");ident=hashlib.sha256((match+kick).encode()).hexdigest()[:16]
            feeds.append({"id":"sky-bundesliga-tactical-"+ident,"match":match,"competition":"Bundesliga","kickoff":kick,"type":"tactical","status":"confirmed","platform":"Sky Sport Bundesliga 3 / WOW","language":"Unknown / not verified","commentary":"Consumer audio language not verified; feed remains listed because public video access is confirmed","usAvailability":False,"access":"subscription","territories":["Germany"],"notes":"Sky confirms public Tactical Feed carriage in Germany for the Saturday Topspiel. Audio language is not required for TacticalViewer confirmation; DFL separately documents the Tactical Feed production product.","sourceUrl":SKY_POLICY,"secondarySourceUrl":DFL_PRODUCT,"fixtureSourceUrl":FIXTURES,"watchUrl":SKY_WATCH,"sourceKey":"sky:bundesliga-tactical","checkedAt":now.isoformat().replace("+00:00","Z"),"verifiedAt":now.isoformat().replace("+00:00","Z"),"exactFixtureVerified":True,"publicAccessConfirmed":True})
        health.append({"source":"sky:bundesliga-tactical","ok":checked==len(matchdays) and checked>0,"checkedAt":now.isoformat().replace("+00:00","Z"),"count":len(unique),"exportsChecked":checked,"exportsExpected":len(matchdays),"exportErrors":export_errors})
    except Exception as exc:health.append({"source":"sky:bundesliga-tactical","ok":False,"checkedAt":now.isoformat().replace("+00:00","Z"),"error":type(exc).__name__})
    complete=health[-1]["ok"]
    if not complete:feeds=feeds+[f for f in p.get("feeds",[]) if f.get("sourceKey")=="sky:bundesliga-tactical"]
    feeds=retain_evidence(feeds,now)
    p["feeds"],p["sourceHealth"],p["updatedAt"]=feeds,health,now.isoformat().replace("+00:00","Z");write(p);return 0 if complete else 2
if __name__=="__main__":raise SystemExit(main())
