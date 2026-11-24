/*
    mart_salary_by_skill
    --------------------
    "Which skills pay more?"
    For each (country, role), compares the average salary of postings that mention
    a skill with postings (same country + role) that do not. Only uses postings with
    a disclosed salary. Skills with fewer than 20 salaried postings are dropped.

    Amounts are yearly, in the country's own currency.
    'All Countries' rows use EUR so different currencies can be averaged.
*/

with jobs as (

    select
        j.job_id,
        j.data_source,
        role_rollup.value::varchar                                   as role_family,
        country_rollup.value::varchar                                as country,
        iff(country_rollup.value::varchar = 'All Countries', 'EUR', j.currency) as currency,
        iff(country_rollup.value::varchar = 'All Countries', j.salary_mid_eur, j.salary_mid_yearly) as salary
    from {{ ref('fct_job_postings') }} j,
        {{ rollup_role_and_country('j') }}
    where j.is_salary_disclosed

),

group_stats as (

    select
        data_source,
        country,
        role_family,
        any_value(currency) as currency,
        count(*)            as n_all,
        sum(salary)         as sum_all,
        avg(salary)         as avg_all
    from jobs
    group by data_source, country, role_family

),

skill_stats as (

    select
        j.data_source,
        j.country,
        j.role_family,
        s.skill_name,
        s.skill_category,
        count(*)          as n_with,
        sum(j.salary)     as sum_with,
        avg(j.salary)     as avg_with,
        median(j.salary)  as median_with
    from jobs j
    inner join {{ ref('fct_job_skills') }} s
        on j.job_id = s.job_id
    group by j.data_source, j.country, j.role_family, s.skill_name, s.skill_category

)

select
    k.data_source,
    k.country,
    k.role_family,
    g.currency,
    k.skill_name,
    k.skill_category,
    k.n_with                                                                    as salaried_postings_with_skill,
    round(k.avg_with, 0)                                                        as avg_salary_with_skill,
    round(k.median_with, 0)                                                     as median_salary_with_skill,
    round((g.sum_all - k.sum_with) / nullif(g.n_all - k.n_with, 0), 0)         as avg_salary_without_skill,
    round(g.avg_all, 0)                                                         as group_avg_salary,
    round((k.avg_with / nullif((g.sum_all - k.sum_with) / nullif(g.n_all - k.n_with, 0), 0) - 1) * 100, 1)
                                                                                as salary_premium_pct
from skill_stats k
inner join group_stats g
    on k.data_source = g.data_source
   and k.country = g.country
   and k.role_family = g.role_family
where k.n_with >= 20
