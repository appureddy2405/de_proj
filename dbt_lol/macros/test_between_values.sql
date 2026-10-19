{# Generic test: fails for any value outside [min_value, max_value]. No external packages needed. #}
{% test between_values(model, column_name, min_value, max_value) %}
select {{ column_name }} from {{ model }}
where {{ column_name }} < {{ min_value }} or {{ column_name }} > {{ max_value }}
{% endtest %}
