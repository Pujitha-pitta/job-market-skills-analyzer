"""
Start the dashboard and ask for your Snowflake login in the terminal.

    ..\\.venv\\Scripts\\python.exe run_dashboard.py

The login is only kept in memory for this run (nothing is written to disk).
Runs Streamlit through Python because Windows Application Control blocks
the streamlit.exe launcher on this PC.
"""

import getpass
import os
import subprocess
import sys
from pathlib import Path

if not os.environ.get("SNOWFLAKE_ACCOUNT"):
    os.environ["SNOWFLAKE_ACCOUNT"] = input("Snowflake account identifier (e.g. ORGNAME-ACCOUNTNAME): ").strip()
if not os.environ.get("SNOWFLAKE_USER"):
    os.environ["SNOWFLAKE_USER"] = input("Snowflake login name (your sign-up email): ").strip()
if not os.environ.get("SNOWFLAKE_PASSWORD"):
    os.environ["SNOWFLAKE_PASSWORD"] = getpass.getpass(f"Snowflake password for {os.environ['SNOWFLAKE_USER']}: ")

app = Path(__file__).resolve().parent / "streamlit_app.py"
sys.exit(subprocess.call([
    sys.executable, "-m", "streamlit", "run", str(app),
    "--server.port", "8501", "--browser.gatherUsageStats", "false",
]))
