/*
    ai_skill_gaps  (optional — needs ai_job_skills, see that model)
    -------------
    Compares the AI's skill list with the regex dictionary:
      - in_dictionary = false  -> a skill the regex never looks for
                                  (candidate to add to seeds/skills.csv)
      - regex_agreement        -> for dictionary skills: in how many of the ads where
                                  the AI saw it did the regex find it too
*/

{{ config(enabled = var('enable_cortex', false)) }}

with ai as (

    select * from {{ ref('ai_job_skills') }}

),

dictionary_match as (

    -- which dictionary skill (if any) does the AI's wording correspond to?
    select
        ai.job_id,
        ai.ai_skill,
        min(d.skill_name) as dictionary_skill
    from ai
    left join {{ ref('skills') }} d
        on {{ text_contains_skill('ai.ai_skill', 'd.search_pattern') }}
    group by ai.job_id, ai.ai_skill

)

select
    m.ai_skill,
    m.dictionary_skill,
    m.dictionary_skill is not null                                          as in_dictionary,
    count(distinct m.job_id)                                                as ads_mentioning,
    round(count(distinct r.job_id) / nullif(count(distinct m.job_id), 0), 2) as regex_agreement
from dictionary_match m
left join {{ ref('int_job_skills') }} r
    on r.job_id = m.job_id
   and r.skill_name = m.dictionary_skill
group by m.ai_skill, m.dictionary_skill
order by ads_mentioning desc
