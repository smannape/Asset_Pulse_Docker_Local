@echo off
REM Start the Asset Pulse FastAPI backend locally on Windows.
REM Loads backend\.env (if present) and serves on http://localhost:8000.
REM
REM Usage (from repo root, in cmd.exe or PowerShell):
REM   scripts\start_backend.bat
REM
REM Prerequisites:
REM   - Python >= 3.10 on PATH
REM   - backend\.venv created and requirements installed (see local deployment guide)
REM   - backend\.env configured with DATABASE_URL for PostgreSQL 17 on localhost:5433

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."
pushd "%ROOT_DIR%\backend" || exit /b 1

if not exist ".venv\Scripts\activate.bat" (
    echo [start_backend] No virtualenv found at backend\.venv.
    echo [start_backend] Create it once with:
    echo     cd backend ^&^& python -m venv .venv ^&^& .venv\Scripts\activate ^&^& pip install -r requirements.txt
    popd
    exit /b 1
)

call .venv\Scripts\activate.bat

if exist ".env" (
    REM Load KEY=VALUE pairs from .env, ignoring comments and blanks.
    for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do (
        if not "%%A"=="" if not "%%B"=="" set "%%A=%%B"
    )
) else (
    echo [start_backend] WARNING: backend\.env not found - falling back to SQLite.
    echo [start_backend] Copy backend\.env.local.example to backend\.env to use PostgreSQL 17.
)

if "%PORT%"=="" set "PORT=8000"

uvicorn app.main:app --host 0.0.0.0 --port %PORT% --reload
set "EXITCODE=%ERRORLEVEL%"

popd
exit /b %EXITCODE%
