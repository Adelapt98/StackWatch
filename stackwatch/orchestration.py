from dagster import Definitions,asset,define_asset_job,AssetSelection,ScheduleDefinition
from .ingest import collect,quality
from .product import workspaces,overview

@asset(group_name='collection')
def repository_activity(context):
 result=collect();context.log.info('Collection: %s',result)
 if result['status']=='failed':raise RuntimeError('All collection requests failed')
 return result

@asset(group_name='quality')
def data_quality(repository_activity):return quality(repository_activity['id'])

@asset(group_name='reporting')
def workspace_reports(context,data_quality):
 spaces=workspaces();count=sum(len(overview(w['id'])['repositories']) for w in spaces)
 context.log.info('Prepared %s workspace repository views',count)
 return {'workspaces':len(spaces),'repository_views':count,'run_id':data_quality['run_id']}

collection=define_asset_job('collect_repository_activity',selection=AssetSelection.assets(repository_activity))
quality_job=define_asset_job('check_data_quality',selection=AssetSelection.assets(data_quality))
reports=define_asset_job('prepare_workspace_reports',selection=AssetSelection.assets(workspace_reports))
daily=define_asset_job('daily_stackwatch',selection=AssetSelection.all())
defs=Definitions(assets=[repository_activity,data_quality,workspace_reports],jobs=[collection,quality_job,reports,daily],schedules=[ScheduleDefinition(job=daily,cron_schedule='15 6 * * *',execution_timezone='UTC')])
