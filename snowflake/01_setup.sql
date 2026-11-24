/* =========================================================================
   01_setup.sql  —  run ONCE in a Snowsight worksheet (as ACCOUNTADMIN)

   Creates:
     roles      TRANSFORMER (loads + transforms data, used by dbt)
                REPORTER    (read-only, used by the dashboard)
     warehouse  TRANSFORM_WH (X-Small, auto-suspends after 60s to save credits)
     database   JOB_MARKET_DB with schema RAW (dbt creates the other schemas)
     objects    CSV file format, internal stage, raw landing table
   ========================================================================= */

USE ROLE ACCOUNTADMIN;

-- ---------- Roles --------------------------------------------------------
CREATE ROLE IF NOT EXISTS TRANSFORMER COMMENT = 'Loads raw data and runs dbt';
CREATE ROLE IF NOT EXISTS REPORTER    COMMENT = 'Read-only access to MARTS for dashboards';

GRANT ROLE TRANSFORMER TO ROLE SYSADMIN;
GRANT ROLE REPORTER    TO ROLE SYSADMIN;

-- give both roles to yourself
-- (quoted, because trial sign-ups often create a lower-case username)
SET my_user = '"' || CURRENT_USER() || '"';
GRANT ROLE TRANSFORMER TO USER IDENTIFIER($my_user);
GRANT ROLE REPORTER    TO USER IDENTIFIER($my_user);

-- ---------- Warehouse ----------------------------------------------------
CREATE WAREHOUSE IF NOT EXISTS TRANSFORM_WH
    WAREHOUSE_SIZE      = 'XSMALL'
    AUTO_SUSPEND        = 60
    AUTO_RESUME         = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT             = 'Compute for loading, dbt and dashboard';

GRANT USAGE, OPERATE ON WAREHOUSE TRANSFORM_WH TO ROLE TRANSFORMER;
GRANT USAGE          ON WAREHOUSE TRANSFORM_WH TO ROLE REPORTER;

-- ---------- Database -----------------------------------------------------
CREATE DATABASE IF NOT EXISTS JOB_MARKET_DB COMMENT = 'Job market skills analyzer';
GRANT OWNERSHIP ON DATABASE JOB_MARKET_DB TO ROLE TRANSFORMER COPY CURRENT GRANTS;
GRANT USAGE ON DATABASE JOB_MARKET_DB TO ROLE REPORTER;

-- ---------- Raw layer (owned by TRANSFORMER) -----------------------------
USE ROLE TRANSFORMER;
USE WAREHOUSE TRANSFORM_WH;
USE DATABASE JOB_MARKET_DB;

CREATE SCHEMA IF NOT EXISTS RAW COMMENT = 'Data exactly as it arrives — never edited';
USE SCHEMA RAW;

CREATE FILE FORMAT IF NOT EXISTS CSV_FORMAT
    TYPE                         = CSV
    FIELD_DELIMITER              = ','
    SKIP_HEADER                  = 1
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    NULL_IF                      = ('', 'NULL', 'null')
    EMPTY_FIELD_AS_NULL          = TRUE
    TRIM_SPACE                   = FALSE      -- keep raw as-is, clean in dbt
    ENCODING                     = 'UTF8';

CREATE STAGE IF NOT EXISTS JOB_POSTINGS_STAGE
    FILE_FORMAT = CSV_FORMAT
    COMMENT     = 'Landing zone for job posting CSV files';

-- Everything lands as VARCHAR: raw data is messy, dbt does the typing.
CREATE TABLE IF NOT EXISTS JOB_POSTINGS (
    job_id               VARCHAR,
    job_title            VARCHAR,
    company_name         VARCHAR,
    location             VARCHAR,
    experience_required  VARCHAR,
    salary_range         VARCHAR,
    work_mode            VARCHAR,
    posted_date          VARCHAR,
    job_description      VARCHAR,
    source_site          VARCHAR,
    _file_name           VARCHAR,
    _loaded_at           TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Quick check
SHOW TABLES IN SCHEMA JOB_MARKET_DB.RAW;
