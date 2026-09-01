@echo off
REM Apply roster schema on Hostinger from Windows CMD. No phpMyAdmin.
REM Usage (from backend-api folder):
REM   scripts\apply_live_roster_schema.cmd YOUR_HOSTINGER_MYSQL_HOST YOUR_DB_USER YOUR_DB_NAME
REM
REM Hostinger hPanel: Databases -> MySQL hostname (not localhost on this PC).
REM Remote MySQL must be allowed for your office IP.

if "%~3"=="" (
  echo Usage: scripts\apply_live_roster_schema.cmd HOST USER DATABASE
  echo Example: scripts\apply_live_roster_schema.cmd srv123.hstgr.io u123456789 your_db_name
  exit /b 1
)

cd /d "%~dp0\.."

echo === 1 inspect (read-only) ===
python scripts\inspect_roster_schema.py --host %1 --user %2 --database %3
if errorlevel 1 exit /b 1

echo === 2 apply missing tables/columns (no DROP) ===
python scripts\sync_roster_schema.py --host %1 --user %2 --database %3
if errorlevel 1 exit /b 1

echo === 3 inspect again ===
python scripts\inspect_roster_schema.py --host %1 --user %2 --database %3
echo Done. tfs_user count must match step 1.
