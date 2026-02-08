$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot "..\\apps\\api")
if (!(Test-Path ".venv")) {
  Write-Host "No apps/api/.venv found. Create it after API bootstrap."
}
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
