@echo off
REM Apply db\001_init.sql to your local PostgreSQL 17 instance on port 5433.
REM
REM Usage (from repo root):
REM   scripts\init_db.bat
REM
REM Override the host, port, user, or database with environment variables, e.g.:
REM   set PGUSER=asset_pulse
REM   set PGDATABASE=asset_pulse
REM   scripts\init_db.bat

setlocal

if "%PGHOST%"=="" set "PGHOST=localhost"
if "%PGPORT%"=="" set "PGPORT=5433"
if "%PGUSER%"=="" set "PGUSER=asset_pulse"
if "%PGDATABASE%"=="" set "PGDATABASE=asset_pulse"

set "SCRIPT_DIR=%~dp0"
set "SQL_FILE=%SCRIPT_DIR%..\db\001_init.sql"

if not exist "%SQL_FILE%" (
    echo [init_db] Could not find %SQL_FILE%
    exit /b 1
)

echo [init_db] Applying %SQL_FILE% to %PGHOST%:%PGPORT%/%PGDATABASE% as %PGUSER%
echo [init_db] You will be prompted for the database password.

psql "host=%PGHOST% port=%PGPORT% user=%PGUSER% dbname=%PGDATABASE%" -f "%SQL_FILE%"
exit /b %ERRORLEVEL%
