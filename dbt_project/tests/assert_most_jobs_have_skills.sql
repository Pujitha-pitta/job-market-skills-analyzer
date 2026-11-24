-- Data-quality guard for the skill extractor (e.g. a broken regex in seeds/skills.csv).
-- Fails if too many postings have zero skills detected:
--   sample data: more than 5%   (every synthetic posting names its skills)
--   real ads:    more than 25%  (some real IT ads, e.g. support or project roles,
--                                name no tool at all)

select data_source, share_without_skills
from (
    select data_source, avg(iff(skill_count = 0, 1, 0)) as share_without_skills
    from {{ ref('fct_job_postings') }}
    group by data_source
)
where share_without_skills > iff(data_source = 'Real', 0.25, 0.05)
