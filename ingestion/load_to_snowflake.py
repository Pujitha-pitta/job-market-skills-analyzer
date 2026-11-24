"""
Upload data/job_postings.csv to a Snowflake internal stage and COPY it into
JOB_MARKET_DB.RAW.JOB_POSTINGS.

Run snowflake/01_setup.sql once before using this script.

Credentials come from environment variables, or are asked for when missing
(never hard-code them):
    SNOWFLAKE_ACCOUNT    e.g. abc12345.ap-south-1   (or orgname-accountname)
    SNOWFLAKE_USER
    SNOWFLAKE_PASSWORD   your password, or a Programmatic Access Token (PAT)

Usage:
    python ingestion/load_to_snowflake.py
    python ingestion/load_to_snowflake.py --truncate   # reload from scratch
"""

import argparse
import getpass
import os
import sys
from pathlib import Path

import snowflake.connector

DEFAULT_FILE = Path(__file__).resolve().parent.parent / "data" / "job_postings.csv"

COPY_SQL = """
COPY INTO RAW.JOB_POSTINGS (
    job_id, job_title, company_name, location, experience_required,
    salary_range, work_mode, posted_date, job_description, source_site,
    _file_name
)
FROM (
    SELECT $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, METADATA$FILENAME
    FROM @RAW.JOB_POSTINGS_STAGE
)
FILES = ({files})
FILE_FORMAT = (FORMAT_NAME = 'RAW.CSV_FORMAT')
ON_ERROR = 'ABORT_STATEMENT'
{force}
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, nargs="+", default=[DEFAULT_FILE],
                        help="one or more CSV files (e.g. sample data + real JobTech ads)")
    parser.add_argument("--truncate", action="store_true",
                        help="empty the raw table first and force a full reload")
    args = parser.parse_args()

    for f in args.file:
        if not f.exists():
            sys.exit(f"File not found: {f}\nRun data_generator/generate_job_postings.py "
                     "(and ingestion/fetch_jobtech.py for real ads) first.")

    # Ask for anything not already in the environment (password is hidden).
    account = os.environ.get("SNOWFLAKE_ACCOUNT") or input("Snowflake account identifier (e.g. ORGNAME-ACCOUNTNAME): ").strip()
    user = os.environ.get("SNOWFLAKE_USER") or input("Snowflake login name (your sign-up email): ").strip()
    password = os.environ.get("SNOWFLAKE_PASSWORD") or getpass.getpass(f"Snowflake password for {user}: ")

    conn = snowflake.connector.connect(
        account=account,
        user=user,
        password=password,
        role="TRANSFORMER",
        warehouse="TRANSFORM_WH",
        database="JOB_MARKET_DB",
        schema="RAW",
    )
    try:
        cur = conn.cursor()
        if args.truncate:
            cur.execute("TRUNCATE TABLE RAW.JOB_POSTINGS")
            print("Truncated RAW.JOB_POSTINGS")

        staged = []
        for f in args.file:
            file_uri = "file://" + f.resolve().as_posix()
            print(f"Uploading {f.name} to stage ...")
            cur.execute(f"PUT '{file_uri}' @RAW.JOB_POSTINGS_STAGE AUTO_COMPRESS=TRUE OVERWRITE=TRUE")
            staged.append(f"'{f.name}.gz'")

        # only load the files we just uploaded (older files may still sit in the stage)
        print("Copying into RAW.JOB_POSTINGS ...")
        cur.execute(COPY_SQL.format(files=", ".join(staged),
                                    force="FORCE = TRUE" if args.truncate else ""))
        for row in cur.fetchall():
            print("  ", row[:4])

        count = cur.execute("SELECT COUNT(*) FROM RAW.JOB_POSTINGS").fetchone()[0]
        print(f"Done. RAW.JOB_POSTINGS now has {count:,} rows.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
