import csv
import io
from .db import connection,execute,initialize

def export_to_s3(bucket,key,client=None):
 if not bucket or not key:raise ValueError('Bucket and object key are required')
 initialize()
 with connection() as db: rows=execute(db,'SELECT repo,week,commits FROM weekly_activity ORDER BY repo,week').fetchall()
 out=io.StringIO(newline='');writer=csv.writer(out);writer.writerow(['repository','week_start_unix','commits']);writer.writerows(rows)
 if client is None:
  import boto3
  client=boto3.client('s3')
 client.put_object(Bucket=bucket,Key=key,Body=out.getvalue().encode(),ContentType='text/csv; charset=utf-8')
 return {'bucket':bucket,'key':key,'rows':len(rows)}
