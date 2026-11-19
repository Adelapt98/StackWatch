import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
def catalog(): return json.loads((ROOT/'catalog.json').read_text(encoding='utf-8'))
def database_url(): return os.environ.get('DATABASE_URL','sqlite:///'+str(ROOT/'data'/'stackwatch.db'))
