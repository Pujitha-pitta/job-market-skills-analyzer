/*
    mart_official_salary
    --------------------
    Official Swedish monthly salaries (Statistics Sweden, SCB) for each role,
    used by the dashboard for REAL Swedish ads — they almost never publish pay.

    One row per role_family, plus 'All Roles' = the SCB figures weighted by how
    many real ads each role has (so it reflects today's Data/IT job mix).
*/

with roles as (

    select
        r.role_family,
        s.ssyk_code,
        s.occupation,
        s.year,
        s.avg_monthly_sek,
        s.median_monthly_sek,
        s.p10_monthly_sek,
        s.p25_monthly_sek,
        s.p75_monthly_sek,
        s.p90_monthly_sek
    from {{ ref('role_occupation') }} r
    join {{ ref('scb_salaries') }} s
        on s.ssyk_code = r.ssyk_code

),

real_ads as (

    select role_family, count(*) as ads
    from {{ ref('fct_job_postings') }}
    where data_source = 'Real'
    group by role_family

),

all_roles as (

    -- weight each role's SCB figures by its number of live ads
    select
        'All Roles'                                                          as role_family,
        'mix'                                                                as ssyk_code,
        'All Data/IT occupations, weighted by live ads'                      as occupation,
        max(r.year)                                                          as year,
        round(sum(r.avg_monthly_sek    * a.ads) / sum(a.ads), -2)            as avg_monthly_sek,
        round(sum(r.median_monthly_sek * a.ads) / sum(a.ads), -2)            as median_monthly_sek,
        null                                                                 as p10_monthly_sek,
        round(sum(r.p25_monthly_sek    * a.ads) / sum(a.ads), -2)            as p25_monthly_sek,
        round(sum(r.p75_monthly_sek    * a.ads) / sum(a.ads), -2)            as p75_monthly_sek,
        null                                                                 as p90_monthly_sek
    from roles r
    join real_ads a
        on a.role_family = r.role_family

)

select * from roles
union all
select * from all_roles
