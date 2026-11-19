select repo, week, commits, fetched_at,
       avg(commits) over (partition by repo order by week rows between 4 preceding and 1 preceding) as previous_four_observation_average,
       count(*) over (partition by repo order by week rows between 4 preceding and 1 preceding) as previous_observation_count
from {{ ref('stg_weekly_activity') }}
