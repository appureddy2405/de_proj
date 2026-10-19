select
    champion_id,
    champion_name,
    string_to_array(nullif(champion_roles, ''), ',') as roles
from {{ source('raw', 'champions') }}
