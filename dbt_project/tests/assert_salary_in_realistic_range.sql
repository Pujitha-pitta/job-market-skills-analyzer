-- Fails if a disclosed salary is outside 1 500 - 400 000 EUR per year
-- (almost certainly a parsing bug, e.g. a monthly salary read as yearly).

select job_id, country, salary_raw, salary_min_eur, salary_max_eur
from {{ ref('stg_job_postings') }}
where is_salary_disclosed
  and (salary_min_eur < 1500 or salary_max_eur > 400000)
