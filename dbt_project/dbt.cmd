@echo off
rem Shortcut for running dbt from this folder:  .\dbt build
rem Calls dbt through the project's Python, because Windows Application Control
rem blocks the dbt.exe launcher on this PC.
set DBT_ENGINE_MANAGE_STATE=false
"%~dp0..\.venv\Scripts\python.exe" -W ignore::RuntimeWarning -m dbt.cli.main %*
