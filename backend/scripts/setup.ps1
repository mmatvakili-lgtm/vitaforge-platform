# VitaForge local setup (Windows PowerShell). Run from the repository root:  powershell -ExecutionPolicy Bypass -File backend\scripts\setup.ps1
$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\.."
if (-not (Test-Path ..\.env)) { Copy-Item ..\.env.example ..\.env; Write-Host "Created .env from .env.example (edit DATABASE_URL if needed)" }
if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python ..\tools\django_preflight.py
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
Write-Host "Setup complete. Start the server with:  powershell -File backend\scripts\run.ps1"
