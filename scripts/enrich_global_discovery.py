#!/usr/bin/env python3
"""Worldwide discovery net for soccer camera-feed products not yet covered by a verifier.

Leads only. Exact fixture, public territory and watch route are required before anything
can be confirmed. Commentary language and audio presence are metadata only.
"""
from __future__ import annotations
import hashlib, html, json, re, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from update_feeds import retain_evidence
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"data"; UA="TacticalFeedFinder/3.4 (+https://github.com/Expiramentor5468/tacticalviewer)"; SOURCE="global:camera-feed-discovery"
QUERIES=[
 '("tactical cam" OR "tactical feed" OR "tactical view") (soccer OR football) (live OR stream OR broadcast)',
 '("wide angle camera" OR "wide-angle camera" OR "wide tactical view" OR "coach cam" OR "manager mode") (soccer OR football) (live OR broadcast)',
 '("ref cam" OR "referee cam") (soccer OR football) (live OR broadcast)',
]
PATTERN=re.compile(r'\b(?:tactical\s*(?:cam|camera|feed|view)|wide[- ]angle\s+(?:cam|camera|view|feed)|wide\s+tactical\s+view|coach\s*cam|manager\s*mode|ref(?:eree)?\s*cam)\b',re.I)
BROADCAST=re.compile(r'\b(?:live|stream|broadcast|coverage|feed|camera|cam|match|game|fixture)\b',re.I)
REJECT=re.compile(r'\b(?:acquisition|acquires|merger|agency|marketing|investment|group\s+(?:acquires|adds|buys)|company)\b',re.I)
def stamp(dt):return dt.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':UA})
 with urllib.request.urlopen(req,timeout=20) as r:return r.read(2_000_000).decode('utf-8',errors='replace')
def rss_url(q):return 'https://news.google.com/rss/search?q='+urllib.parse.quote(q+' when:45d')+'&hl=en&gl=US&ceid=US:en'
def parse(xml,now):
 root=ET.fromstring(xml)
 if root.tag!="rss" or root.find("channel") is None:raise ValueError("Expected RSS channel")
 out=[]
 for item in root.findall('./channel/item')[:50]:
  title=html.unescape(item.findtext('title',''));desc=re.sub('<[^>]+>',' ',html.unescape(item.findtext('description','')));body=title+' '+desc
  if not PATTERN.search(body) or not BROADCAST.search(body) or REJECT.search(title):continue
  try:
   published=parsedate_to_datetime(item.findtext('pubDate',''))
   if published.tzinfo is None or not now-timedelta(days=45)<=published<=now+timedelta(hours=1):continue
  except (ValueError,TypeError):continue
  link=item.findtext('link','')
  if not link.startswith(('https://','http://')):continue
  low=body.lower();kind='tactical' if 'tactical' in low or re.search(r'wide[- ]angle\s+(?:cam|camera|view|feed)',low) else 'coach' if 'coach cam' in low or 'manager mode' in low else 'ref' if 'ref cam' in low or 'referee cam' in low else 'alternate'
  ident=hashlib.sha256(link.encode()).hexdigest()[:16]
  out.append({'id':'global-lead-'+ident,'match':title,'competition':'Other / global','kickoff':None,'type':kind,'status':'candidate','platform':'Global discovery — carrier unverified','language':'Unknown','commentary':'Audio/commentary not yet verified','usAvailability':None,'access':'unknown','territories':[],'notes':'Worldwide discovery lead. Exact fixture, public territory and viewing route must be verified before confirmation. Any language or video-only feed is eligible.','sourceUrl':link,'sourcePublishedAt':stamp(published),'checkedAt':stamp(now),'sourceKey':SOURCE,'exactFixtureVerified':False,'publicAccessConfirmed':False})
 return out
def load():return json.loads((DATA/'feeds.json').read_text(encoding='utf-8'))
def write(p):
 encoded=json.dumps(p,indent=2,ensure_ascii=False);(DATA/'feeds.json').write_text(encoded+'\n',encoding='utf-8');(ROOT/'data.js').write_text('window.TACTICAL_FEED_DATA = '+encoded+';\n',encoding='utf-8')
def main():
 now=datetime.now(timezone.utc);p=load();feeds=[f for f in p.get('feeds',[]) if f.get('sourceKey')!=SOURCE];health=[h for h in p.get('sourceHealth',[]) if h.get('source')!=SOURCE];found=[];ok=0;errors=[]
 for q in QUERIES:
  try:found.extend(parse(get(rss_url(q)),now));ok+=1
  except Exception as exc:errors.append(type(exc).__name__)
 complete=ok==len(QUERIES)
 if not complete:found=[f for f in p.get("feeds",[]) if f.get("sourceKey")==SOURCE]+found
 seen=set();unique=[]
 for f in retain_evidence(found,now):
  if f['id'] in seen:continue
  seen.add(f['id']);unique.append(f)
 feeds.extend(unique);health.append({'source':SOURCE,'ok':complete,'checkedAt':stamp(now),'count':len(unique),'queriesChecked':ok,'queriesExpected':len(QUERIES),**({'errors':errors} if errors else {})});p['feeds'],p['sourceHealth'],p['updatedAt']=feeds,health,stamp(now);write(p);return 0 if complete else 2
if __name__=='__main__':raise SystemExit(main())
