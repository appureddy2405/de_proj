select
    match_id,
    region,
    platform_id,
    region_group,
    queue_id,
    queue_type,
    game_version,
    patch_version,
    to_timestamp(game_creation / 1000.0)      as game_created_at,
    to_timestamp(game_end_timestamp / 1000.0) as game_ended_at,
    game_duration                             as duration_seconds,
    round(game_duration / 60.0, 2)            as duration_minutes,
    -- Remakes (early surrenders) distort averages; flag rather than silently drop.
    (game_duration < 180)                     as is_remake
from {{ source('raw', 'matches') }}
