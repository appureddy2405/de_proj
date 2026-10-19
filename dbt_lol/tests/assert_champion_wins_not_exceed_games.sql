select * from {{ ref('mart_champion_performance') }} where wins > games
