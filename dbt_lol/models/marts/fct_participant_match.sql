-- One row per player per match, enriched with match context and per-minute / share metrics.
select
    p.match_id,
    p.participant_id,
    p.player_key,
    m.region,
    m.region_group,
    m.queue_type,
    m.patch_version,
    m.game_created_at,
    m.duration_minutes,
    m.is_remake,
    p.team_id,
    p.champion_id,
    p.champion_name,
    p.position,
    p.is_win,
    p.kills,
    p.deaths,
    p.assists,
    p.kda,
    p.gold_earned,
    p.damage_to_champions,
    round(p.gold_earned / nullif(m.duration_minutes, 0), 1)         as gold_per_min,
    round(p.damage_to_champions / nullif(m.duration_minutes, 0), 1) as damage_per_min,
    round(
        p.damage_to_champions::numeric
        / nullif(sum(p.damage_to_champions) over (partition by p.match_id, p.team_id), 0),
        4
    )                                                                as team_damage_share
from {{ ref('stg_participants') }} p
join {{ ref('stg_matches') }} m using (match_id)
