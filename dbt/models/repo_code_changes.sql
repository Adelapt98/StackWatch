select repo, week, additions, deletions, additions - deletions as net_lines, fetched_at
from {{ source('raw', 'code_changes') }}
