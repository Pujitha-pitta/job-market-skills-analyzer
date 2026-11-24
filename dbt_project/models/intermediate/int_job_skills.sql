/*
    int_job_skills
    --------------
    Bridge table: one row per (job, skill) mentioned in the job description.

    Incremental: on each run only postings from the last 3 days of loaded data
    (and anything newer) are re-scanned, so adding a new month of data is cheap.
    If you add or change skills in seeds/skills.csv, rebuild everything with:
        dbt build --full-refresh --select int_job_skills+
*/

{{
    config(
        materialized = 'incremental',
        unique_key = 'job_skill_id',
        incremental_strategy = 'merge',
        on_schema_change = 'sync_all_columns'
    )
}}

with jobs as (

    select job_id, job_description, posted_date
    from {{ ref('stg_job_postings') }}

    {% if is_incremental() %}
    where posted_date >= (select dateadd(day, -3, max(posted_date)) from {{ this }})
    {% endif %}

),

skills as (

    select skill_name, skill_category, search_pattern
    from {{ ref('skills') }}

)

select
    md5(jobs.job_id || '|' || skills.skill_name)   as job_skill_id,
    jobs.job_id,
    skills.skill_name,
    skills.skill_category,
    jobs.posted_date
from jobs
inner join skills
    on {{ text_contains_skill('jobs.job_description', 'skills.search_pattern') }}
