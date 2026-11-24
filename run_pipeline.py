"""
Run the whole pipeline in one go, asking for your Snowflake login only once:

    1. generate data/job_postings.csv          (sample data, 8 countries)
    2. download data/jobtech_sweden.csv         (real live Swedish ads, JobTech API)
    3. reload both into Snowflake (RAW.JOB_POSTINGS is emptied first)
    4. dbt build --full-refresh   (seeds, all models, all tests)

    .\\.venv\\Scripts\\python.exe run_pipeline.py

Your login is only kept in memory while this runs (nothing is written to disk).
"""

import getpass
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable

env = os.environ.copy()
if not env.get("SNOWFLAKE_ACCOUNT"):
    env["SNOWFLAKE_ACCOUNT"] = input("Snowflake account identifier (e.g. ORGNAME-ACCOUNTNAME): ").strip()
if not env.get("SNOWFLAKE_USER"):
    env["SNOWFLAKE_USER"] = input("Snowflake login name (your sign-up email): ").strip()
if not env.get("SNOWFLAKE_PASSWORD"):
    env["SNOWFLAKE_PASSWORD"] = getpass.getpass(f"Snowflake password for {env['SNOWFLAKE_USER']}: ")
env.setdefault("DBT_ENGINE_MANAGE_STATE", "false")   # keep dbt's optional cloud "State" feature off

steps = [
    ("Generate sample job postings (8 countries)", [PY, "data_generator/generate_job_postings.py"], ROOT),
    ("Download real Swedish job ads (JobTech)", [PY, "ingestion/fetch_jobtech.py"], ROOT),
    ("Load into Snowflake", [PY, "ingestion/load_to_snowflake.py", "--truncate", "--file",
                             "data/job_postings.csv", "data/jobtech_sweden.csv"], ROOT),
    ("dbt build", [PY, "run_dbt.py", "build", "--full-refresh"], ROOT / "dbt_project"),
]
for i, (name, cmd, cwd) in enumerate(steps, start=1):
    print(f"\n=== Step {i}/{len(steps)}: {name} ===", flush=True)
    if subprocess.call(cmd, cwd=cwd, env=env) != 0:
        sys.exit(f"\nStopped: step '{name}' failed (see the messages above).")

print("\nAll done. Start the dashboard with:  cd dashboard; ..\\.venv\\Scripts\\python.exe run_dashboard.py")
