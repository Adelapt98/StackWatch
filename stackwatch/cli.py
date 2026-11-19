import argparse,json
from .ingest import collect,quality

def main():
 p=argparse.ArgumentParser(description='StackWatch data operations');commands=p.add_subparsers(dest='command',required=True)
 commands.add_parser('sync');s3=commands.add_parser('archive-s3');s3.add_argument('--bucket',required=True);s3.add_argument('--key',required=True)
 a=p.parse_args()
 if a.command=='sync':result=collect();result['quality']=quality(result['id'])
 else:
  from .archive import export_to_s3
  result=export_to_s3(a.bucket,a.key)
 print(json.dumps(result,indent=2));return 1 if result.get('status')=='failed' else 0
if __name__=='__main__':raise SystemExit(main())
