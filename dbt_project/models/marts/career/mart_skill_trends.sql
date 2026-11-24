/*
    mart_skill_trends
    -----------------
    "Which skills are growing?"  Monthly share of postings mentioning each skill.
    One row per (posted_month, country, role_family, skill).
    Includes 'All Roles' and 'All Countries'.
*/

with jobs as (

    select
        j.job_id,
        j.data_source,
        j.posted_month,
        role_rollup.value::varchar    as role_family,
        country_rollup.value::varchar as country
    from {{ ref('fct_job_postings') }} j,
        {{ rollup_role_and_country('j') }}

),

month_totals as (

    select data_source, posted_month, country, role_family, count(*) as month_postings
    from jobs
    group by data_source, posted_month, country, role_family

),

skill_month as (

    select j.data_source, j.posted_month, j.country, j.role_family, s.skill_name, count(*) as postings_with_skill
    from jobs j
    inner join {{ ref('fct_job_skills') }} s
        on j.job_id = s.job_id
    group by j.data_source, j.posted_month, j.country, j.role_family, s.skill_name

)

select
    s.data_source,
    s.posted_month,
    s.country,
    s.role_family,
    s.skill_name,
    s.postings_with_skill,
    t.month_postings,
    round(s.postings_with_skill / t.month_postings, 4) as share_of_postings
from skill_month s
inner join month_totals t
    on s.data_source = t.data_source
   and s.posted_month = t.posted_month
   and s.country = t.country
   and s.role_family = t.role_family
