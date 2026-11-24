-- Fails if any posting has a lower bound above its upper bound
-- (would mean the salary parser read the numbers wrongly).

select job_id, salary_raw, salary_min_yearly, salary_max_yearly
from {{ ref('stg_job_postings') }}
where salary_min_yearly > salary_max_yearly
