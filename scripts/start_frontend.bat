@echo off
REM Start the Asset Pulse Vite frontend locally on Windows.
REM Serves on http://localhost:5173.
REM
REM Usage (from repo root):
REM   scripts\start_frontend.bat
REM
REM Prerequisites:
REM   - Node.js >= 18 on PATH
REM   - frontend\node_modules installed (npm install in frontend\ first)

setlocal

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\frontend" || exit /b 1

if not exist "node_modules" (
    echo [start_frontend] node_modules missing - running 'npm install' first.
    call npm install
    if errorlevel 1 (
        popd
        exit /b 1
    )
)

call npm run dev
set "EXITCODE=%ERRORLEVEL%"

popd
exit /b %EXITCODE%
