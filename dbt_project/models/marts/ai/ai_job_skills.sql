/*
    ai_job_skills  (optional — uses Snowflake Cortex AI, costs a few credits)
    -------------
    Asks an LLM running inside Snowflake to list the skills in a sample of REAL
    job ads, as a second opinion next to the regex dictionary (seeds/skills.csv).

    Off by default. Turn it on with:
        python run_dbt.py build --select ai_job_skills+ --vars "{enable_cortex: true}"
    Sample size:  --vars "{enable_cortex: true, cortex_sample_size: 300}"
*/

{{ config(enabled = var('enable_cortex', false)) }}

with ads as (

    select job_id, left(job_description, 4000) as description
    from {{ ref('stg_job_postings') }}
    where data_source = 'Real'
    order by posted_date desc, job_id
    limit {{ var('cortex_sample_size', 300) }}

),

answers as (

    select
        job_id,
        ai_complete(
            '{{ var("cortex_model", "llama3.1-8b") }}',
            'List the technical skills, tools, programming languages and spoken languages that this job ad asks for. '
            || 'Answer ONLY with a JSON array of short skill names in English, for example ["SQL", "Python", "Swedish"]. '
            || 'Job ad: ' || description
        ) as answer
    from ads

)

select
    a.job_id,
    initcap(trim(s.value::varchar)) as ai_skill
from answers a,
    lateral flatten(input => try_parse_json(regexp_substr(a.answer, '\\[.*\\]', 1, 1, 's'))) s
where trim(s.value::varchar) <> ''
qualify row_number() over (partition by a.job_id, lower(trim(s.value::varchar)) order by 1) = 1
