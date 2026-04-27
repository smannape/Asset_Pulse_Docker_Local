@echo off
REM Asset Pulse — fallback Windows launcher (no .exe required).
REM Double-click this file from the project folder, or run from cmd.
REM Requires: Docker Desktop running, plus Python 3.10+ on PATH.

setlocal
cd /d "%~dp0\.."

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python is not on PATH. Install Python 3.10+ from https://www.python.org/
    echo         or run AssetPulseLauncher.exe instead.
    pause
    exit /b 1
)

python "%~dp0asset_pulse_launcher.py"
set RC=%ERRORLEVEL%
endlocal & exit /b %RC%
