select repo, week, commits, fetched_at from {{ source('raw', 'weekly_activity') }}
