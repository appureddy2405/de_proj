select
    pi.match_id,
    pi.participant_id,
    pi.slot,
    pi.item_id,
    i.item_name
from {{ source('raw', 'participant_items') }} pi
left join {{ source('raw', 'items') }} i using (item_id)
where pi.item_id <> 0   -- 0 = empty slot
