/* =========================================================================
   02_load_raw_data.sql  —  load data/job_postings.csv into RAW.JOB_POSTINGS

   Easiest option: run  python ingestion/load_to_snowflake.py  (does all of this).

   Manual option:
     Step 1 - put the file in the stage, using ONE of:
       a) Snowsight UI: Data » Databases » JOB_MARKET_DB » RAW » Stages »
          JOB_POSTINGS_STAGE » "+ Files" » upload job_postings.csv
       b) SnowSQL / Snowflake CLI:
          PUT 'file://C:/path/to/job-market-skills-analyzer/data/job_postings.csv'
              @JOB_MARKET_DB.RAW.JOB_POSTINGS_STAGE AUTO_COMPRESS=TRUE OVERWRITE=TRUE;
     Step 2 - run the statements below in a worksheet.
   ========================================================================= */

USE ROLE TRANSFORMER;
USE WAREHOUSE TRANSFORM_WH;
USE SCHEMA JOB_MARKET_DB.RAW;

-- What is in the stage?
LIST @JOB_POSTINGS_STAGE;

-- Peek at the file before loading (schema-on-read)
SELECT $1 AS job_id, $2 AS job_title, $4 AS location, $6 AS salary_range, $8 AS posted_date
FROM @JOB_POSTINGS_STAGE (FILE_FORMAT => 'CSV_FORMAT')
LIMIT 10;

-- Load. COPY remembers loaded files, so re-running will not create duplicates.
COPY INTO JOB_POSTINGS (
    job_id, job_title, company_name, location, experience_required,
    salary_range, work_mode, posted_date, job_description, source_site,
    _file_name
)
FROM (
    SELECT $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, METADATA$FILENAME
    FROM @JOB_POSTINGS_STAGE
)
FILE_FORMAT = (FORMAT_NAME = 'CSV_FORMAT')
ON_ERROR = 'ABORT_STATEMENT';

-- Sanity checks
SELECT COUNT(*) AS total_rows, COUNT(DISTINCT job_id) AS distinct_jobs FROM JOB_POSTINGS;

SELECT location, COUNT(*) FROM JOB_POSTINGS GROUP BY 1 ORDER BY 2 DESC;   -- see the messy city names
SELECT salary_range FROM JOB_POSTINGS SAMPLE (20 ROWS);                   -- see mixed salary formats
