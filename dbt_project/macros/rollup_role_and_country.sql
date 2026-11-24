{#
    Repeats every job row for its own role + 'All Roles' and its own country +
    'All Countries', so a mart can answer "Data Engineer in Sweden" and
    "all roles, all countries" from the same table.
    Use after a FROM:   from fct_job_postings j, {{ rollup_role_and_country('j') }}
    Then select:        role_rollup.value::varchar, country_rollup.value::varchar
#}
{% macro rollup_role_and_country(alias) %}
    lateral flatten(input => array_construct({{ alias }}.role_family, 'All Roles')) role_rollup,
    lateral flatten(input => array_construct({{ alias }}.country, 'All Countries')) country_rollup
{% endmacro %}
