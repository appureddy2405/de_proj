-- Match-level view built from ALL scraped matches (not only those with participant detail).
with detail as (
    select distinct match_id from {{ ref('stg_participants') }}
)

select
    m.patch_version,
    m.region,
    m.region_group,
    m.queue_type,
    count(*)                                                        as matches,
    round(avg(m.duration_minutes), 2)                               as avg_duration_minutes,
    round((percentile_cont(0.5) within group (order by m.duration_minutes))::numeric, 2)
                                                                    as median_duration_minutes,
    sum(m.is_remake::int)                                           as remakes,
    count(d.match_id)                                               as matches_with_detail,
    round(count(d.match_id)::numeric / count(*), 4)                 as detail_coverage
from {{ ref('stg_matches') }} m
left join detail d using (match_id)
group by 1, 2, 3, 4
