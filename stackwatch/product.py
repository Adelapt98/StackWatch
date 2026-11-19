"""Workspace decisions use completed weeks and explain the comparison."""
from datetime import datetime,timezone
from uuid import uuid4
from .config import catalog
from .db import connection,execute,initialize

def now():return datetime.now(timezone.utc).isoformat()

def workspaces():
 initialize()
 with connection() as db:
  spaces=execute(db,'SELECT id,name,created_at FROM workspaces ORDER BY created_at').fetchall()
  memberships=execute(db,'SELECT workspace_id,repo FROM workspace_repos').fetchall()
  notes=execute(db,'SELECT id,workspace_id,repo,note,created_at FROM notes ORDER BY created_at DESC').fetchall()
 return [{'id':s[0],'name':s[1],'created_at':s[2],'repos':[m[1] for m in memberships if m[0]==s[0]],'notes':[dict(zip(('id','workspace_id','repo','note','created_at'),n)) for n in notes if n[1]==s[0]]} for s in spaces]

def create_workspace(name):
 if not isinstance(name,str) or not 1<=len(name.strip())<=80:raise ValueError('Workspace name must contain 1 to 80 characters')
 initialize();ident=str(uuid4())
 with connection() as db:execute(db,'INSERT INTO workspaces VALUES(?,?,?)',(ident,name.strip(),now()))
 return ident

def set_repositories(workspace,repos):
 if not isinstance(repos,list) or len(repos)>100 or not all(isinstance(r,str) for r in repos):raise ValueError('Invalid repository selection')
 if not set(repos).issubset({r['id'] for r in catalog()}):raise ValueError('Choose repositories from the catalog')
 initialize()
 with connection() as db:
  if not execute(db,'SELECT id FROM workspaces WHERE id=?',(workspace,)).fetchone():raise ValueError('Workspace not found')
  execute(db,'DELETE FROM workspace_repos WHERE workspace_id=?',(workspace,))
  for repo in set(repos):execute(db,'INSERT INTO workspace_repos VALUES(?,?)',(workspace,repo))

def add_note(workspace,repo,note):
 if not isinstance(note,str) or not 1<=len(note.strip())<=500:raise ValueError('Note must contain 1 to 500 characters')
 initialize();ident=str(uuid4())
 with connection() as db:
  if not execute(db,'SELECT repo FROM workspace_repos WHERE workspace_id=? AND repo=?',(workspace,repo)).fetchone():raise ValueError('Add the repository to the workspace first')
  execute(db,'INSERT INTO notes VALUES(?,?,?,?,?)',(ident,workspace,repo,note.strip(),now()))
 return ident

def delete_note(workspace,note):
 with connection() as db:execute(db,'DELETE FROM notes WHERE workspace_id=? AND id=?',(workspace,note))

def overview(workspace_id,now_ts=None):
 space=next((w for w in workspaces() if w['id']==workspace_id),None)
 if space is None:raise ValueError('Workspace not found')
 stamp=int(datetime.now(timezone.utc).timestamp()) if now_ts is None else now_ts;reference={x['id']:x for x in catalog()}
 with connection() as db:
  rows=execute(db,'SELECT repo,week,commits,fetched_at FROM weekly_activity ORDER BY week').fetchall()
  runs=execute(db,'SELECT id,started_at,finished_at,status,success,pending,failed FROM runs ORDER BY started_at DESC LIMIT 5').fetchall()
  fetches=execute(db,'SELECT repo,status,detail FROM fetch_log WHERE run_id=(SELECT id FROM runs ORDER BY started_at DESC LIMIT 1)').fetchall()
  days=execute(db,'SELECT repo,day,commits FROM daily_activity ORDER BY day').fetchall()
  changes=execute(db,'SELECT repo,week,additions,deletions FROM code_changes ORDER BY week').fetchall()
  code_logs=execute(db,'SELECT repo,status,detail,fetched_at FROM code_fetch_log ORDER BY fetched_at').fetchall()
 groups={}
 for repo,week,count,fetched in rows:
  if week+604800<=stamp:groups.setdefault(repo,[]).append({'week':int(week),'commits':int(count),'fetched_at':fetched})
 latest={r[0]:{'status':r[1],'detail':r[2]} for r in fetches};result=[]
 day_groups={};change_groups={};code_status={}
 for repo,day,count in days:day_groups.setdefault(repo,{})[int(day)]=int(count)
 for repo,week,added,removed in changes:change_groups.setdefault(repo,{})[int(week)]={'additions':int(added),'deletions':int(removed)}
 for repo,status,detail,fetched_at in code_logs:code_status[repo]={'status':status,'detail':detail,'fetched_at':fetched_at}
 for repo in space['repos']:
  if repo not in reference:continue
  values=groups.get(repo,[]);tail=values[-5:];contiguous=len(tail)==5 and all(tail[i]['week']-tail[i-1]['week']==604800 for i in range(1,5))
  fresh=bool(tail and 0<=stamp-(tail[-1]['week']+604800)<=14*86400)
  baseline=sum(x['commits'] for x in tail[:4])/4 if contiguous else None
  change=round((tail[-1]['commits']-baseline)*100/baseline,1) if contiguous and fresh and baseline else None
  signal='unavailable' if change is None else 'increased' if change>=50 else 'decreased' if change<=-50 else 'steady'
  latest_week=tail[-1]['week'] if tail else None
  daily=[{'day':latest_week+i*86400,'commits':day_groups.get(repo,{}).get(latest_week+i*86400)} for i in range(7)] if latest_week is not None else []
  result.append({**reference[repo],'latest_week':latest_week,'latest_count':tail[-1]['commits'] if tail else None,'baseline':baseline,'change_pct':change,'signal':signal,'fresh':fresh,'contiguous':contiguous,'history':values[-52:],'daily':daily,'code_change':change_groups.get(repo,{}).get(latest_week),'code_source':code_status.get(repo,{'status':'not fetched','detail':''}),'source':latest.get(repo,{'status':'not fetched','detail':''})})
 return {'workspace':space,'repositories':result,'runs':[dict(zip(('id','started_at','finished_at','status','success','pending','failed'),r)) for r in runs]}
