-- How often each item is finished in a build, and the win rate of builds containing it.
-- Counts a player once per item even if they hold duplicates.
with builds as (
    select distinct i.match_id, i.participant_id, i.item_id, i.item_name
    from {{ ref('stg_participant_items') }} i
)

select
    f.patch_version,
    f.queue_type,
    b.item_id,
    b.item_name,
    count(*)                         as builds,
    round(avg(f.is_win::int), 4)     as win_rate
from builds b
join {{ ref('fct_participant_match') }} f using (match_id, participant_id)
where not f.is_remake
group by 1, 2, 3, 4
