select repo, day, commits, fetched_at from {{ source('raw', 'daily_activity') }}
