$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot "..\\apps\\api")
if (!(Test-Path ".venv")) { Write-Error "apps/api/.venv missing. Create it after API bootstrap." }
. .\\.venv\\Scripts\\Activate.ps1
ruff check .
