import os,tempfile,unittest
from unittest.mock import patch
from stackwatch import ingest,product
from stackwatch.db import connection,execute
from stackwatch.archive import export_to_s3
from stackwatch.code_frequency import collect_code_frequency,validate as validate_code,Unsupported

CATALOG=[{'id':'example/alpha','name':'Alpha','category':'Data'}]
WEEK=7*86400

class WorkflowTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.patches=[patch.dict(os.environ,{'DATABASE_URL':'sqlite:///'+self.temp.name+'/test.db'}),patch('stackwatch.ingest.catalog',return_value=CATALOG),patch('stackwatch.product.catalog',return_value=CATALOG)]
  for p in self.patches:p.start()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.temp.cleanup()
 def payload(self,repo):return [{'week':1000000+i*WEEK,'total':10 if i<4 else 20,'days':[1]*7} for i in range(5)]
 def test_idempotent_and_product_comparison(self):
  ingest.collect(self.payload);result=ingest.collect(self.payload);ingest.quality(result['id']);w=product.create_workspace('Team');product.set_repositories(w,['example/alpha']);overview=product.overview(w,1000000+5*WEEK+1);r=overview['repositories'][0]
  self.assertEqual(r['signal'],'increased');self.assertEqual(r['change_pct'],100.0)
  with connection() as db:self.assertEqual(execute(db,'SELECT COUNT(*) FROM weekly_activity').fetchone()[0],5)
 def test_pending_preserves_existing_data(self):
  ingest.collect(self.payload)
  def pending(repo):raise ingest.Pending('not ready')
  self.assertEqual(ingest.collect(pending)['status'],'pending')
  with connection() as db:self.assertEqual(execute(db,'SELECT COUNT(*) FROM weekly_activity').fetchone()[0],5)
 def test_rate_limit_stops_remaining_calls(self):
  with patch('stackwatch.ingest.catalog',return_value=CATALOG+ [{'id':'example/beta'}]):
   calls=[]
   def limited(repo):calls.append(repo);raise ingest.RateLimited('limit')
   r=ingest.collect(limited);self.assertEqual(len(calls),1);self.assertEqual(r['failed'],2)
 def test_missing_week_is_not_a_comparison(self):
  ingest.collect(lambda r:self.payload(r)[1:]);w=product.create_workspace('Team');product.set_repositories(w,['example/alpha']);item=product.overview(w,1000000+5*WEEK+1)['repositories'][0];self.assertIsNone(item['change_pct'])
 def test_in_progress_week_is_excluded(self):
  ingest.collect(self.payload);w=product.create_workspace('Team');product.set_repositories(w,['example/alpha']);item=product.overview(w,1000000+4*WEEK+5)['repositories'][0];self.assertEqual(item['latest_count'],10);self.assertIsNone(item['change_pct'])
 def test_workspace_notes_and_catalog_restrictions(self):
  w=product.create_workspace('Team')
  with self.assertRaises(ValueError):product.set_repositories(w,['someone/private'])
  product.set_repositories(w,['example/alpha']);i=product.add_note(w,'example/alpha','Check changes');self.assertEqual(product.workspaces()[0]['notes'][0]['note'],'Check changes');product.delete_note(w,i);self.assertFalse(product.workspaces()[0]['notes'])
 def test_validation_rejects_negative_or_duplicate(self):
  with self.assertRaises(ValueError):ingest.validate([{'week':1,'total':-1}])
  with self.assertRaises(ValueError):ingest.validate([{'week':1,'total':1},{'week':1,'total':2}])
 def test_s3_export_uses_only_aggregates(self):
  ingest.collect(self.payload)
  class Stub:
   def put_object(self,**kwargs):self.args=kwargs
  stub=Stub();result=export_to_s3('test','weekly.csv',stub);self.assertEqual(result['rows'],5);self.assertIn(b'example/alpha',stub.args['Body'])
 def test_daily_counts_persist_and_update(self):
  ingest.collect(self.payload);ingest.collect(self.payload)
  with connection() as db:
   self.assertEqual(execute(db,'SELECT COUNT(*) FROM daily_activity').fetchone()[0],35)
 def test_code_frequency_records_additions_and_deletions(self):
  with patch('stackwatch.code_frequency.catalog',return_value=CATALOG):
   result=collect_code_frequency(lambda repo:[[1000000,42,-7]])
  self.assertEqual(result['success'],1)
  with connection() as db:self.assertEqual(execute(db,'SELECT additions,deletions FROM code_changes').fetchone(),(42,7))
 def test_code_frequency_unsupported_and_validation(self):
  def unsupported(repo):raise Unsupported('not available')
  with patch('stackwatch.code_frequency.catalog',return_value=CATALOG):self.assertEqual(collect_code_frequency(unsupported)['unsupported'],1)
  with self.assertRaises(ValueError):validate_code([[10,1,2]])
  with self.assertRaises(ValueError):validate_code([[10,1,-2],[10,4,-1]])
 def test_daily_details_and_matching_code_week(self):
  ingest.collect(self.payload)
  with patch('stackwatch.code_frequency.catalog',return_value=CATALOG):collect_code_frequency(lambda repo:[[1000000+4*WEEK,20,-5]])
  w=product.create_workspace('Team');product.set_repositories(w,['example/alpha']);item=product.overview(w,1000000+5*WEEK+1)['repositories'][0]
  self.assertEqual(len(item['daily']),7);self.assertEqual(item['daily'][0]['commits'],1);self.assertEqual(item['code_change'],{'additions':20,'deletions':5})

if __name__=='__main__':unittest.main()
