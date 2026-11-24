-- Shares are percentages expressed as 0-1. Anything outside means a join fan-out bug.

select 'mart_skill_demand' as model, country, role_family, skill_name, share_of_postings as share
from {{ ref('mart_skill_demand') }}
where share_of_postings not between 0 and 1

union all

select 'mart_fresher_skills', country, role_family, skill_name, share_of_fresher_postings
from {{ ref('mart_fresher_skills') }}
where share_of_fresher_postings not between 0 and 1
