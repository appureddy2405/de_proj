-- Player identifiers are pseudonymised here: marts never see puuid, summoner_id or name.
select
    match_id,
    participant_id,
    md5(puuid)                               as player_key,
    team_id,
    champion_id,
    champion_name,
    nullif(individual_position, '')          as position,
    nullif(rank_tier, '')                    as rank_tier,
    (win = 1)                                as is_win,
    kills,
    deaths,
    assists,
    gold_earned,
    champion_experience,
    total_damage_dealt_to_champions          as damage_to_champions,
    round((kills + assists)::numeric / greatest(deaths, 1), 2) as kda
from {{ source('raw', 'participants') }}
