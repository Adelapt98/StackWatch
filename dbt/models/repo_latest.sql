select repo, max(week) as latest_week, count(*) as recorded_weeks
from {{ ref('stg_weekly_activity') }} group by repo
