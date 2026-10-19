select match_id, sum(is_win::int) as winners
from {{ ref('stg_teams') }}
group by match_id
having sum(is_win::int) <> 1
