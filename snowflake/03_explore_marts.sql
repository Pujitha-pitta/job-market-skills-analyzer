/* =========================================================================
   03_explore_marts.sql  —  questions you can answer after `dbt build`
   ========================================================================= */

USE ROLE REPORTER;
USE WAREHOUSE TRANSFORM_WH;
USE SCHEMA JOB_MARKET_DB.MARTS;

-- Every mart has a country column ('All Countries' = totals) and a role_family
-- column ('All Roles' = totals). Salaries are yearly in the local currency;
-- 'All Countries' rows and *_eur columns use EUR.

-- 1. Top 10 skills for Data Engineers in Sweden
SELECT skill_name, postings_with_skill, ROUND(share_of_postings * 100, 1) AS pct_of_jobs
FROM mart_skill_demand
WHERE country = 'Sweden' AND role_family = 'Data Engineer'
ORDER BY demand_rank
LIMIT 10;

-- 2. Which skills pay more for Data Analysts in Sweden? (SEK per month)
SELECT skill_name,
       ROUND(avg_salary_with_skill / 12)    AS sek_per_month_with,
       ROUND(avg_salary_without_skill / 12) AS sek_per_month_without,
       salary_premium_pct
FROM mart_salary_by_skill
WHERE country = 'Sweden' AND role_family = 'Data Analyst'
ORDER BY salary_premium_pct DESC
LIMIT 10;

-- 3. What do entry-level / graduate jobs ask for, everywhere?
SELECT role_family, skill_name, ROUND(share_of_fresher_postings * 100, 1) AS pct
FROM mart_fresher_skills
WHERE country = 'All Countries' AND role_family <> 'All Roles' AND demand_rank <= 5
ORDER BY role_family, demand_rank;

-- 4. Is GenAI growing? (monthly share of all postings, all countries)
SELECT posted_month, ROUND(share_of_postings * 100, 1) AS pct
FROM mart_skill_trends
WHERE country = 'All Countries' AND role_family = 'All Roles' AND skill_name = 'LLM / GenAI'
ORDER BY posted_month;

-- 5. Skills that are asked together for Data Engineers in Sweden
SELECT skill_a, skill_b, pair_count, lift
FROM mart_skill_pairs
WHERE country = 'Sweden' AND role_family = 'Data Engineer'
ORDER BY pair_count DESC
LIMIT 10;

-- 6. Best Swedish cities for Data Analysts
SELECT city, total_postings, ROUND(median_salary_yearly / 12) AS median_sek_per_month
FROM mart_city_overview
WHERE country = 'Sweden' AND role_family = 'Data Analyst'
ORDER BY total_postings DESC;

-- 7. Compare countries: median Data Engineer salary in EUR per year
SELECT country, SUM(total_postings) AS postings, ROUND(MEDIAN(median_salary_eur)) AS median_eur_per_year
FROM mart_city_overview
WHERE role_family = 'Data Engineer'
GROUP BY country
ORDER BY median_eur_per_year DESC;
