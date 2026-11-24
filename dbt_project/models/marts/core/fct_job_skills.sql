-- Fact table: one row per (job, skill). Carries job attributes so dashboards
-- can filter by role / country / city / experience without extra joins.

select
    js.job_skill_id,
    js.job_id,
    js.skill_name,
    js.skill_category,
    j.data_source,
    j.role_family,
    j.country,
    j.city,
    j.work_mode,
    j.experience_band,
    j.salary_mid_eur,
    j.is_salary_disclosed,
    j.posted_date,
    j.posted_month
from {{ ref('int_job_skills') }} js
inner join {{ ref('fct_job_postings') }} j
    on js.job_id = j.job_id
