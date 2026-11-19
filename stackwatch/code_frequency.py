"""Collect GitHub's aggregate lines added and removed by week."""
import json
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from uuid import uuid4
from .config import catalog
from .db import connection,execute,initialize
from .ingest import Pending,RateLimited

class Unsupported(Exception): pass

def fetch(repo):
 req=Request('https://api.github.com/repos/'+repo+'/stats/code_frequency',headers={'Accept':'application/vnd.github+json','User-Agent':'StackWatch/0.1 (github.com/Adelapt98)','X-GitHub-Api-Version':'2022-11-28'})
 try:
  with urlopen(req,timeout=25) as response:
   if response.status in (202,204):raise Pending('GitHub statistics are not ready')
   data=response.read(1_000_001)
   if len(data)>1_000_000:raise ValueError('Response too large')
   return json.loads(data)
 except HTTPError as exc:
  if exc.code==422:raise Unsupported('GitHub does not provide code frequency for this repository') from exc
  if exc.code in (403,429) and (exc.code==429 or exc.headers.get('X-RateLimit-Remaining')=='0' or exc.headers.get('Retry-After')):raise RateLimited('GitHub rate limit reached') from exc
  raise

def validate(payload):
 if not isinstance(payload,list) or not payload:raise ValueError('Expected weekly code frequency rows')
 seen=set();rows=[]
 for item in payload:
  if not isinstance(item,list) or len(item)!=3 or any(not isinstance(v,int) or isinstance(v,bool) for v in item):raise ValueError('Invalid code frequency row')
  week,added,removed=item
  if week<0 or added<0 or removed>0 or week in seen:raise ValueError('Invalid code frequency values')
  seen.add(week);rows.append((week,added,-removed))
 return rows

def collect_code_frequency(fetcher=None):
 initialize();fetcher=fetcher or fetch;run=str(uuid4());now=datetime.now(timezone.utc).isoformat();counts={'success':0,'pending':0,'unsupported':0,'failed':0};stopped=False
 for item in catalog():
  repo=item['id'];status='failed';detail=''
  try:
   if stopped:raise RateLimited('Skipped after rate limit')
   rows=validate(fetcher(repo))
   with connection() as db:
    for week,added,removed in rows:execute(db,'INSERT INTO code_changes(repo,week,additions,deletions,fetched_at) VALUES(?,?,?,?,?) ON CONFLICT(repo,week) DO UPDATE SET additions=excluded.additions,deletions=excluded.deletions,fetched_at=excluded.fetched_at',(repo,week,added,removed,now))
   status='success'
  except Pending as exc:status='pending';detail=str(exc)
  except Unsupported as exc:status='unsupported';detail=str(exc)
  except RateLimited as exc:stopped=True;detail=str(exc)
  except (HTTPError,URLError,OSError,ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:detail=str(exc)[:200]
  counts[status]+=1
  with connection() as db:execute(db,'INSERT INTO code_fetch_log VALUES(?,?,?,?,?)',(run,repo,status,detail,now))
 return {'run_id':run,**counts}
