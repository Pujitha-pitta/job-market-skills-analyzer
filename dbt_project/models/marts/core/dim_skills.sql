-- Dimension: one row per skill in the dictionary, with overall popularity.

with mentions as (

    select skill_name, count(distinct job_id) as total_postings
    from {{ ref('int_job_skills') }}
    group by skill_name

),

all_jobs as (

    select count(*) as n from {{ ref('fct_job_postings') }}

)

select
    s.skill_name,
    s.skill_category,
    s.search_pattern,
    coalesce(m.total_postings, 0)                                   as total_postings,
    round(coalesce(m.total_postings, 0) / nullif(a.n, 0), 4)        as share_of_all_postings,
    rank() over (order by coalesce(m.total_postings, 0) desc)       as overall_rank
from {{ ref('skills') }} s
cross join all_jobs a
left join mentions m
    on s.skill_name = m.skill_name
