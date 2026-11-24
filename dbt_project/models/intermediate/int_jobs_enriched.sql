/*
    int_jobs_enriched
    -----------------
    Job postings + how many / which skills each one asks for.
*/

with jobs as (

    select * from {{ ref('stg_job_postings') }}

),

skills_per_job as (

    select
        job_id,
        count(*)                                                as skill_count,
        listagg(skill_name, ', ') within group (order by skill_name) as skills_list
    from {{ ref('int_job_skills') }}
    group by job_id

)

select
    jobs.*,
    coalesce(s.skill_count, 0)  as skill_count,
    s.skills_list
from jobs
left join skills_per_job s
    on jobs.job_id = s.job_id
