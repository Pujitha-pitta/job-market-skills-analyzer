/*
    mart_city_overview
    ------------------
    "Where are the jobs, and where do they pay best?"
    One row per (country, city, role_family), including 'All Roles'.
    Salaries are yearly: in the local currency, and in EUR for comparing countries.
*/

with jobs as (

    select j.*, role_rollup.value::varchar as role_group
    from {{ ref('fct_job_postings') }} j,
        lateral flatten(input => array_construct(j.role_family, 'All Roles')) role_rollup

)

select
    data_source,
    country,
    city,
    role_group                                                      as role_family,
    any_value(currency)                                             as currency,
    count(*)                                                        as total_postings,
    count_if(is_salary_disclosed)                                   as salaried_postings,
    round(median(salary_mid_yearly), 0)                             as median_salary_yearly,
    round(median(salary_mid_eur), 0)                                as median_salary_eur,
    count_if(experience_band = 'Fresher (0-1 yrs)')                 as fresher_postings,
    round(count_if(work_mode in ('Remote', 'Hybrid')) / count(*), 4) as share_remote_or_hybrid
from jobs
group by data_source, country, city, role_group
