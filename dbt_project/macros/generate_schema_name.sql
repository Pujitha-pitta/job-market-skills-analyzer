{#
    By default dbt names custom schemas "<target_schema>_<custom>" (e.g. ANALYTICS_MARTS).
    This override uses the custom name as-is (STAGING, INTERMEDIATE, MARTS, SEEDS),
    which keeps the warehouse tidy for a single-developer project.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
