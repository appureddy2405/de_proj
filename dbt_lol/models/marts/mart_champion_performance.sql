-- Champion win/pick rates per patch, queue and role. Remakes are excluded.
with games as (
    select * from {{ ref('fct_participant_match') }} where not is_remake
),

matches_in_scope as (
    select patch_version, queue_type, count(distinct match_id) as total_matches
    from games
    group by 1, 2
)

select
    g.patch_version,
    g.queue_type,
    g.champion_id,
    g.champion_name,
    g.position,
    count(*)                                         as games,
    sum(g.is_win::int)                               as wins,
    round(avg(g.is_win::int), 4)                     as win_rate,
    round(count(*)::numeric / s.total_matches, 4)    as pick_rate,
    round(avg(g.kda), 2)                             as avg_kda,
    round(avg(g.gold_per_min), 1)                    as avg_gold_per_min,
    round(avg(g.damage_per_min), 1)                  as avg_damage_per_min,
    round(avg(g.team_damage_share), 4)               as avg_team_damage_share,
    -- Small samples make win rates meaningless; consumers can filter on this.
    (count(*) >= 30)                                 as is_reliable_sample
from games g
join matches_in_scope s using (patch_version, queue_type)
group by g.patch_version, g.queue_type, g.champion_id, g.champion_name, g.position, s.total_matches
