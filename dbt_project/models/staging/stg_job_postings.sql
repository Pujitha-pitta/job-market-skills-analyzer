/*
    stg_job_postings
    ----------------
    One clean row per job posting.
      - removes duplicate scrapes of the same job
      - standardises city and country (via the city_mapping seed)
      - parses experience ("2-5 Yrs", "Fresher", "Graduate", "8+ years") into numbers
      - parses salary from many local formats ("6-10 LPA", "45 000 - 55 000 kr/mån",
        "60.000 - 75.000 € p.a.", "£50k - £65k" ...) into a YEARLY amount in the
        local currency, plus the same amount in EUR so countries can be compared
        (rates in the countries seed)
      - handles two date formats (YYYY-MM-DD and DD-MM-YYYY)
      - classifies the job title into a role family (English + Swedish titles)
      - marks each row as 'Real' (live ads from Arbetsförmedlingen's JobTech API)
        or 'Sample' (synthetic data for 8 countries)
*/

with source as (

    select * from {{ source('raw', 'job_postings') }}

),

deduplicated as (

    select *
    from source
    qualify row_number() over (partition by trim(job_id) order by _loaded_at desc) = 1

),

cleaned as (

    select
        trim(job_id)                                            as job_id,
        regexp_replace(trim(job_title), '\\s+', ' ')            as job_title,
        trim(company_name)                                      as company_name,
        trim(location)                                          as location_raw,
        lower(trim(location))                                   as location_clean,
        trim(experience_required)                               as experience_raw,
        trim(salary_range)                                      as salary_raw,
        trim(work_mode)                                         as work_mode_raw,
        coalesce(
            try_to_date(trim(posted_date), 'YYYY-MM-DD'),
            try_to_date(trim(posted_date), 'DD-MM-YYYY')
        )                                                       as posted_date,
        trim(job_description)                                   as job_description,
        lower(trim(source_site))                                as source_site,
        _loaded_at
    from deduplicated

),

parsed as (

    select
        cleaned.*,

        -- experience ("Fresher" in India, "Graduate" / "Entry level" elsewhere)
        case
            when experience_raw ilike any ('%fresher%', '%graduate%', '%entry level%') then 0
            else try_to_number(regexp_substr(experience_raw, '[0-9]+', 1, 1))
        end                                                     as min_experience_years,
        case
            when experience_raw ilike any ('%fresher%', '%graduate%', '%entry level%') then 1
            when experience_raw like '%+%'        then null      -- "8+ years" has no upper bound
            else try_to_number(regexp_substr(experience_raw, '[0-9]+', 1, 2))
        end                                                     as max_experience_years,

        -- salary, yearly, local currency
        {{ parse_salary_yearly('salary_raw', 1) }}              as salary_min_raw,
        {{ parse_salary_yearly('salary_raw', 2) }}              as salary_max_raw

    from cleaned

),

located as (

    -- known spellings come from the city_mapping seed; anything else written as
    -- "<city>, <country>" (e.g. real ads: "Solna, Sweden") is split on the comma
    select
        p.*,
        coalesce(cm.city, trim(split_part(p.location_raw, ',', 1)))  as mapped_city,
        coalesce(cm.country, sfx.country, 'Unknown')                 as country
    from parsed p
    left join {{ ref('city_mapping') }} cm
        on p.location_clean = cm.raw_location
    left join {{ ref('countries') }} sfx
        on cm.raw_location is null
       and endswith(p.location_clean, ', ' || lower(sfx.country))

),

priced as (

    select
        l.*,
        co.currency,
        co.eur_per_unit,
        co.salary_shown_as,
        -- a single number ("Från 40 000 kr/mån") counts as both ends of the range
        coalesce(l.salary_max_raw, l.salary_min_raw)            as salary_max_filled,
        -- drop amounts that cannot be a yearly salary (e.g. an hourly rate read as yearly)
        l.salary_min_raw is not null
            and l.salary_min_raw <= coalesce(l.salary_max_raw, l.salary_min_raw)
            and l.salary_min_raw * co.eur_per_unit >= 1500
            and coalesce(l.salary_max_raw, l.salary_min_raw) * co.eur_per_unit <= 400000
                                                                as salary_ok
    from located l
    left join {{ ref('countries') }} co
        on l.country = co.country

),

final as (

    select
        job_id,
        job_title,
        {{ classify_role('job_title') }}                        as role_family,
        case
            when job_title ilike any ('%senior%', '%sr.%', '%lead%', '%principal%') then 'Senior'
            when job_title ilike any ('%junior%', '%fresher%', '%intern%', '%trainee%') then 'Entry'
            else 'Mid'
        end                                                     as title_seniority,
        company_name,
        country,
        mapped_city                                             as city,
        case
            when work_mode_raw ilike any ('%remote%', '%home%', '%wfh%') or mapped_city = 'Remote' then 'Remote'
            when work_mode_raw ilike '%hybrid%'                                                then 'Hybrid'
            else 'On-site'
        end                                                     as work_mode,

        experience_raw,
        min_experience_years,
        max_experience_years,
        case
            when min_experience_years is null then 'Unknown'
            when min_experience_years <= 1    then 'Fresher (0-1 yrs)'
            when min_experience_years <= 3    then 'Junior (2-3 yrs)'
            when min_experience_years <= 6    then 'Mid (4-6 yrs)'
            else 'Senior (7+ yrs)'
        end                                                     as experience_band,

        salary_raw,
        currency,
        salary_shown_as,
        iff(salary_ok, salary_min_raw, null)::number(14, 0)                         as salary_min_yearly,
        iff(salary_ok, salary_max_filled, null)::number(14, 0)                      as salary_max_yearly,
        iff(salary_ok, (salary_min_raw + salary_max_filled) / 2, null)::number(14, 0) as salary_mid_yearly,
        iff(salary_ok, salary_min_raw * eur_per_unit, null)::number(12, 0)          as salary_min_eur,
        iff(salary_ok, salary_max_filled * eur_per_unit, null)::number(12, 0)       as salary_max_eur,
        iff(salary_ok, (salary_min_raw + salary_max_filled) / 2 * eur_per_unit, null)::number(12, 0)
                                                                                    as salary_mid_eur,
        coalesce(salary_ok, false)                                                  as is_salary_disclosed,

        posted_date,
        date_trunc('month', posted_date)                        as posted_month,
        job_description,
        source_site,
        iff(source_site = 'jobtech', 'Real', 'Sample')          as data_source,
        iff(source_site = 'jobtech',
            'https://arbetsformedlingen.se/platsbanken/annonser/' || replace(job_id, 'AF', ''),
            null)                                               as job_url,
        _loaded_at

    from priced

)

select * from final
