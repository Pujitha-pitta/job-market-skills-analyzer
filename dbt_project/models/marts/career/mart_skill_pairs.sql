/*
    mart_skill_pairs
    ----------------
    "If I learn SQL, what should I learn with it?"
    Skills that appear together in the same posting, per (data_source, country, role),
    including 'All Roles' / 'All Countries'.

    lift > 1 means the pair shows up together more often than chance:
        lift = P(A and B) / (P(A) * P(B))
*/

with jobs as (

    select
        j.job_id,
        j.data_source,
        role_rollup.value::varchar    as role_family,
        country_rollup.value::varchar as country
    from {{ ref('fct_job_postings') }} j,
        {{ rollup_role_and_country('j') }}

),

js as (

    select j.job_id, j.data_source, j.country, j.role_family, s.skill_name
    from jobs j
    inner join {{ ref('fct_job_skills') }} s
        on j.job_id = s.job_id

),

totals as (

    select data_source, country, role_family, count(*) as total_postings
    from jobs
    group by data_source, country, role_family

),

skill_totals as (

    select data_source, country, role_family, skill_name, count(*) as skill_postings
    from js
    group by data_source, country, role_family, skill_name

),

pairs as (

    select
        a.data_source,
        a.country,
        a.role_family,
        a.skill_name as skill_a,
        b.skill_name as skill_b,
        count(*)     as pair_count
    from js a
    inner join js b
        on a.job_id = b.job_id
       and a.data_source = b.data_source
       and a.country = b.country
       and a.role_family = b.role_family
       and a.skill_name < b.skill_name      -- each pair once, no self-pairs
    group by a.data_source, a.country, a.role_family, a.skill_name, b.skill_name

)

select
    p.data_source,
    p.country,
    p.role_family,
    p.skill_a,
    p.skill_b,
    p.pair_count,
    round(p.pair_count / t.total_postings, 4) as share_of_postings,
    round(
        (p.pair_count / t.total_postings)
        / nullif((ta.skill_postings / t.total_postings) * (tb.skill_postings / t.total_postings), 0)
    , 2)                                       as lift
from pairs p
inner join totals t
    on p.data_source = t.data_source and p.country = t.country and p.role_family = t.role_family
inner join skill_totals ta
    on p.data_source = ta.data_source and p.country = ta.country and p.role_family = ta.role_family
   and p.skill_a = ta.skill_name
inner join skill_totals tb
    on p.data_source = tb.data_source and p.country = tb.country and p.role_family = tb.role_family
   and p.skill_b = tb.skill_name
where p.pair_count >= 5
