# Build AssetPulseLauncher.exe with PyInstaller.
#
# Run from a Windows PowerShell prompt with Python 3.10+ on PATH:
#   cd <repo>\launcher
#   .\build_windows_exe.ps1
#
# Output: launcher\dist\AssetPulseLauncher.exe (single-file executable).

$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

Write-Host "[build] Using Python:" -NoNewline
python --version

Write-Host "[build] Installing PyInstaller (user scope)..."
python -m pip install --upgrade pip | Out-Null
python -m pip install --upgrade pyinstaller | Out-Null

Write-Host "[build] Cleaning previous build artefacts..."
Remove-Item -Recurse -Force build, dist, AssetPulseLauncher.spec -ErrorAction SilentlyContinue

Write-Host "[build] Running PyInstaller..."
python -m PyInstaller `
    --onefile `
    --console `
    --name AssetPulseLauncher `
    --icon NONE `
    asset_pulse_launcher.py

if (-not (Test-Path "dist\AssetPulseLauncher.exe")) {
    throw "Build failed: dist\AssetPulseLauncher.exe was not produced."
}

Write-Host ""
Write-Host "[build] Success: $here\dist\AssetPulseLauncher.exe"
Write-Host "[build] Copy this .exe to the Asset Pulse project folder (next to docker-compose.yml)"
Write-Host "        before distributing."
