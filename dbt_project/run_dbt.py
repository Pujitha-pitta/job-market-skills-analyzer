"""
Run dbt and ask for your Snowflake login if it is not already set.

    ..\\.venv\\Scripts\\python.exe run_dbt.py build
    ..\\.venv\\Scripts\\python.exe run_dbt.py test --select mart_skill_demand

Works around two things on this PC: the account has no stored password in env
variables, and Windows Application Control blocks the dbt.exe launcher.
Nothing you type is written to disk.
"""

import getpass
import os
import sys

if not os.environ.get("SNOWFLAKE_ACCOUNT"):
    os.environ["SNOWFLAKE_ACCOUNT"] = input("Snowflake account identifier (e.g. ORGNAME-ACCOUNTNAME): ").strip()
# Turn off "dbt State" (an optional dbt cloud cache that asks for a separate login).
os.environ.setdefault("DBT_ENGINE_MANAGE_STATE", "false")
if not os.environ.get("SNOWFLAKE_USER"):
    os.environ["SNOWFLAKE_USER"] = input("Snowflake login name (your sign-up email): ").strip()
if not os.environ.get("SNOWFLAKE_PASSWORD"):
    os.environ["SNOWFLAKE_PASSWORD"] = getpass.getpass(f"Snowflake password for {os.environ['SNOWFLAKE_USER']}: ")

from dbt.cli.main import dbtRunner  # noqa: E402  (import after env is ready)

result = dbtRunner().invoke(sys.argv[1:] or ["build"])
sys.exit(0 if result.success else 1)
