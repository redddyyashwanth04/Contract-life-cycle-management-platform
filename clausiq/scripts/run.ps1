# One-command launcher: creates a venv on first run, installs deps, starts the server.
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
}
$py = ".venv\Scripts\python.exe"
& $py -m pip install -q -r requirements.txt
& $py run.py
