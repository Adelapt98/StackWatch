"""Retrieve only GitHub's aggregate weekly commit statistics for curated repositories."""
import json
from datetime import datetime,timezone
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen
from uuid import uuid4
from .config import catalog
from .db import connection,execute,initialize

class Pending(Exception): pass
class RateLimited(Exception): pass

def fetch(repo):
 request=Request('https://api.github.com/repos/'+repo+'/stats/commit_activity',headers={'Accept':'application/vnd.github+json','User-Agent':'StackWatch/0.1 (github.com/Adelapt98)','X-GitHub-Api-Version':'2022-11-28'})
 try:
  with urlopen(request,timeout=25) as response:
   if response.status in (202,204): raise Pending('GitHub statistics are not ready')
   payload=response.read(1_000_001)
   if len(payload)>1_000_000: raise ValueError('Response too large')
   return json.loads(payload)
 except HTTPError as exc:
  if exc.code in (403,429) and (exc.code==429 or exc.headers.get('X-RateLimit-Remaining')=='0' or exc.headers.get('Retry-After')):
   raise RateLimited('GitHub rate limit reached; retry after the indicated reset') from exc
  raise

def validate(payload):
 if not isinstance(payload,list):raise ValueError('Expected a list of weekly statistics')
 records=[];seen=set()
 for item in payload:
  if not isinstance(item,dict):raise ValueError('Invalid week')
  week=item.get('week');total=item.get('total')
  if not isinstance(week,int) or isinstance(week,bool) or week<0 or not isinstance(total,int) or isinstance(total,bool) or total<0 or week in seen:raise ValueError('Invalid or duplicate weekly count')
  days=item.get('days')
  if days is not None and (not isinstance(days,list) or len(days)!=7 or any(not isinstance(v,int) or isinstance(v,bool) or v<0 for v in days)):raise ValueError('Invalid daily counts')
  seen.add(week);records.append((week,total,days))
 if not records:raise ValueError('No weekly observations returned')
 return records

def collect(fetcher=None):
 fetcher=fetcher or fetch;initialize();run_id=str(uuid4());now=datetime.now(timezone.utc).isoformat();counts={'success':0,'pending':0,'failed':0}; stopped=False
 with connection() as db:execute(db,'INSERT INTO runs(id,started_at,status) VALUES(?,?,?)',(run_id,now,'running'))
 for item in catalog():
  repo=item['id'];state='failed';detail=''
  try:
   if stopped:raise RateLimited('Skipped after rate limit')
   rows=validate(fetcher(repo))
   with connection() as db:
    for week,total,days in rows:
     execute(db,'INSERT INTO weekly_activity(repo,week,commits,fetched_at) VALUES(?,?,?,?) ON CONFLICT(repo,week) DO UPDATE SET commits=excluded.commits,fetched_at=excluded.fetched_at',(repo,week,total,now))
     if days is not None:
      for i,count in enumerate(days):execute(db,'INSERT INTO daily_activity(repo,day,commits,fetched_at) VALUES(?,?,?,?) ON CONFLICT(repo,day) DO UPDATE SET commits=excluded.commits,fetched_at=excluded.fetched_at',(repo,week+i*86400,count,now))
   state='success'
  except Pending as exc:state='pending';detail=str(exc)
  except RateLimited as exc:stopped=True;detail=str(exc)
  except (HTTPError,URLError,OSError,ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:detail=str(exc)[:200]
  counts[state]+=1
  with connection() as db:execute(db,'INSERT INTO fetch_log VALUES(?,?,?,?)',(run_id,repo,state,detail))
 status='success' if counts['success'] and not counts['pending'] and not counts['failed'] else 'partial' if counts['success'] else 'pending' if counts['pending'] and not counts['failed'] else 'failed'
 with connection() as db:execute(db,'UPDATE runs SET finished_at=?,status=?,success=?,pending=?,failed=? WHERE id=?',(datetime.now(timezone.utc).isoformat(),status,counts['success'],counts['pending'],counts['failed'],run_id))
 return {'id':run_id,'status':status,**counts}

def quality(run_id):
 initialize()
 with connection() as db:
  execute(db,'DELETE FROM quality WHERE run_id=?',(run_id,))
  for item in catalog():
   row=execute(db,'SELECT COUNT(*),MAX(week) FROM weekly_activity WHERE repo=?',(item['id'],)).fetchone()
   execute(db,'INSERT INTO quality VALUES(?,?,?,?,?)',(run_id,item['id'],row[0],row[1],'available' if row[0] else 'no_data'))
 return {'run_id':run_id,'repositories':len(catalog())}
