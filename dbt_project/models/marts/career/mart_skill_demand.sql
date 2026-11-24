/*
    mart_skill_demand
    -----------------
    "Which skills should I learn for role X in country Y?"
    One row per (country, role_family, skill).
    Includes 'All Roles' and 'All Countries' totals.
*/

with jobs as (

    select
        j.job_id,
        j.data_source,
        role_rollup.value::varchar    as role_family,
        country_rollup.value::varchar as country
    from {{ ref('fct_job_postings') }} j,
        {{ rollup_role_and_country('j') }}

),

totals as (

    select data_source, country, role_family, count(*) as total_postings
    from jobs
    group by data_source, country, role_family

),

skill_counts as (

    select j.data_source, j.country, j.role_family, s.skill_name, s.skill_category, count(*) as postings_with_skill
    from jobs j
    inner join {{ ref('fct_job_skills') }} s
        on j.job_id = s.job_id
    group by j.data_source, j.country, j.role_family, s.skill_name, s.skill_category

)

select
    s.data_source,
    s.country,
    s.role_family,
    s.skill_name,
    s.skill_category,
    s.postings_with_skill,
    t.total_postings,
    round(s.postings_with_skill / t.total_postings, 4)                                         as share_of_postings,
    rank() over (partition by s.data_source, s.country, s.role_family order by s.postings_with_skill desc)     as demand_rank
from skill_counts s
inner join totals t
    on s.data_source = t.data_source
   and s.country = t.country
   and s.role_family = t.role_family
