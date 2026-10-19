select
    match_id,
    team_id,
    (win = 1)       as is_win,
    dragon_kills,
    baron_kills,
    tower_kills,
    inhibitor_kills,
    champion_kills,
    atakhan_kills,
    horde_kills,
    total_gold,
    total_experience
from {{ source('raw', 'teams') }}
