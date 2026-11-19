import argparse,csv,io,json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from .config import catalog
from .product import workspaces,create_workspace,set_repositories,add_note,delete_note,overview

STATIC=Path(__file__).parent/'static'
class Handler(BaseHTTPRequestHandler):
 def send_body(self,body,mime='application/json; charset=utf-8',status=200):
  if isinstance(body,str):body=body.encode('utf-8')
  self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(body)));self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(body)
 def do_GET(self):
  parsed=urlparse(self.path);path=parsed.path
  files={'/':('index.html','text/html; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8')}
  if path in files:
   name,mime=files[path];return self.send_body((STATIC/name).read_bytes(),mime)
  if path=='/api/workspaces':return self.send_body(json.dumps({'workspaces':workspaces(),'catalog':catalog()}))
  if path in ('/api/overview','/api/report.csv'):
   try:result=overview(parse_qs(parsed.query).get('workspace',[''])[0])
   except ValueError:return self.send_body(json.dumps({'error':'Workspace not found'}),status=404)
   if path.endswith('.csv'):
    out=io.StringIO(newline='');writer=csv.writer(out);writer.writerow(['repository','category','latest_completed_week_unix','commits','previous_four_week_average','change_percent','signal','source_status'])
    for r in result['repositories']:writer.writerow([r['id'],r['category'],r['latest_week'],r['latest_count'],r['baseline'],r['change_pct'],r['signal'],r['source']['status']])
    return self.send_body(out.getvalue(),'text/csv; charset=utf-8')
   return self.send_body(json.dumps(result,ensure_ascii=False))
  return self.send_body('Not found','text/plain',404)
 def do_POST(self):
  if self.headers.get('Origin') not in (None,'http://'+self.headers.get('Host','')):return self.send_body('{"error":"Invalid origin"}',status=403)
  try:
   size=int(self.headers.get('Content-Length','0'))
   if not 0<=size<=16384:raise ValueError('Request too large')
   body=json.loads(self.rfile.read(size) or b'{}')
   if not isinstance(body,dict):raise ValueError('Invalid request')
   if self.path=='/api/workspaces':result={'id':create_workspace(body.get('name'))}
   elif self.path=='/api/workspace/repositories':set_repositories(body.get('workspace_id'),body.get('repos'));result={'ok':True}
   elif self.path=='/api/notes':result={'id':add_note(body.get('workspace_id'),body.get('repo'),body.get('note'))}
   elif self.path=='/api/notes/delete':delete_note(body.get('workspace_id'),body.get('id'));result={'ok':True}
   else:return self.send_body('{"error":"Not found"}',status=404)
   return self.send_body(json.dumps(result))
  except (ValueError,TypeError,json.JSONDecodeError) as exc:return self.send_body(json.dumps({'error':str(exc)}),status=400)

def main():
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8092);a=p.parse_args();print(f'StackWatch: http://127.0.0.1:{a.port}',flush=True);ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
if __name__=='__main__':main()
