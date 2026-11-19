from contextlib import contextmanager
from pathlib import Path
import sqlite3
from .config import database_url

SCHEMA=[
 'CREATE TABLE IF NOT EXISTS weekly_activity (repo TEXT NOT NULL, week BIGINT NOT NULL, commits INTEGER NOT NULL CHECK(commits>=0), fetched_at TEXT NOT NULL, PRIMARY KEY(repo,week))',
 'CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT, status TEXT NOT NULL, success INTEGER NOT NULL DEFAULT 0, pending INTEGER NOT NULL DEFAULT 0, failed INTEGER NOT NULL DEFAULT 0)',
 'CREATE TABLE IF NOT EXISTS fetch_log (run_id TEXT NOT NULL, repo TEXT NOT NULL, status TEXT NOT NULL, detail TEXT NOT NULL)',
 'CREATE TABLE IF NOT EXISTS quality (run_id TEXT NOT NULL, repo TEXT NOT NULL, weeks INTEGER NOT NULL, latest_week BIGINT, status TEXT NOT NULL)',
 'CREATE TABLE IF NOT EXISTS workspaces (id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL)',
 'CREATE TABLE IF NOT EXISTS workspace_repos (workspace_id TEXT NOT NULL, repo TEXT NOT NULL, PRIMARY KEY(workspace_id,repo))',
 'CREATE TABLE IF NOT EXISTS notes (id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, repo TEXT NOT NULL, note TEXT NOT NULL, created_at TEXT NOT NULL)']

@contextmanager
def connection():
 url=database_url()
 if url.startswith('sqlite:///'):
  path=Path(url[len('sqlite:///'):]);path.parent.mkdir(parents=True,exist_ok=True);db=sqlite3.connect(path,timeout=30)
 elif url.startswith(('postgresql://','postgres://')):
  import psycopg2
  db=psycopg2.connect(url)
 else: raise ValueError('DATABASE_URL must be sqlite:/// or postgresql://')
 try: yield db;db.commit()
 except BaseException: db.rollback();raise
 finally:db.close()

def execute(db,sql,params=()):
 cur=db.cursor()
 if db.__class__.__module__.startswith('psycopg2'):sql=sql.replace('?','%s')
 cur.execute(sql,params);return cur

def initialize():
 with connection() as db:
  for statement in SCHEMA:execute(db,statement)
