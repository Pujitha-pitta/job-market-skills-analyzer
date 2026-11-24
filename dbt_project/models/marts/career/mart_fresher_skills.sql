/*
    mart_fresher_skills
    -------------------
    "I'm a student / fresher — what do entry-level jobs actually ask for?"
    Same as mart_skill_demand but only for postings needing 0-1 years.
    One row per (country, role_family, skill), with 'All Roles' / 'All Countries'.
*/

with fresher_jobs as (

    select
        j.job_id,
        j.data_source,
        role_rollup.value::varchar    as role_family,
        country_rollup.value::varchar as country
    from {{ ref('fct_job_postings') }} j,
        {{ rollup_role_and_country('j') }}
    where j.experience_band = 'Fresher (0-1 yrs)'

),

totals as (

    select data_source, country, role_family, count(*) as fresher_postings
    from fresher_jobs
    group by data_source, country, role_family

),

skill_counts as (

    select f.data_source, f.country, f.role_family, s.skill_name, s.skill_category, count(*) as postings_with_skill
    from fresher_jobs f
    inner join {{ ref('fct_job_skills') }} s
        on f.job_id = s.job_id
    group by f.data_source, f.country, f.role_family, s.skill_name, s.skill_category

)

select
    s.data_source,
    s.country,
    s.role_family,
    s.skill_name,
    s.skill_category,
    s.postings_with_skill,
    t.fresher_postings,
    round(s.postings_with_skill / t.fresher_postings, 4)                                      as share_of_fresher_postings,
    rank() over (partition by s.data_source, s.country, s.role_family order by s.postings_with_skill desc)    as demand_rank
from skill_counts s
inner join totals t
    on s.data_source = t.data_source
   and s.country = t.country
   and s.role_family = t.role_family
