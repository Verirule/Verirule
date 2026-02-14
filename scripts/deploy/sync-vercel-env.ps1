param(
  [ValidateSet("development", "preview", "production")]
  [string]$Target = "production"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
if (Get-Variable PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
  $PSNativeCommandUseErrorActionPreference = $false
}

$script:VercelBin = "vercel"

function Require-Cli([string]$name) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    throw "$name CLI is not installed or not in PATH."
  }
}

function Get-SecretEnv([string]$name, [bool]$required = $true) {
  $value = [Environment]::GetEnvironmentVariable($name)
  if ([string]::IsNullOrWhiteSpace($value)) {
    if ($required) {
      throw "Missing required environment variable in current shell: $name"
    }
    return $null
  }
  return $value
}

function Sync-VercelVar([string]$name, [string]$target, [bool]$required = $true) {
  $value = Get-SecretEnv -name $name -required $required
  if ($null -eq $value) {
    Write-Host "Skipping optional variable: $name"
    return
  }

  & $script:VercelBin env rm $name $target --yes *> $null
  $global:LASTEXITCODE = 0

  $tempFile = New-TemporaryFile
  try {
    Set-Content -Path $tempFile -Value $value -NoNewline
    Get-Content -Path $tempFile | & $script:VercelBin env add $name $target *> $null
    if ($LASTEXITCODE -ne 0) {
      throw "Failed to sync Vercel env variable: $name"
    }
    $global:LASTEXITCODE = 0
  }
  finally {
    Remove-Item -Path $tempFile -Force -ErrorAction SilentlyContinue
  }

  Write-Host "Synced: $name ($target)"
}

Require-Cli "vercel"
if (Get-Command "vercel.cmd" -ErrorAction SilentlyContinue) {
  $script:VercelBin = "vercel.cmd"
}

$requiredVars = @(
  "NEXT_PUBLIC_SITE_URL",
  "VERIRULE_API_URL",
  "NEXT_PUBLIC_SUPABASE_URL",
  "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
  "NEXT_PUBLIC_SUPABASE_OAUTH_PROVIDERS",
  "STRIPE_SECRET_KEY",
  "STRIPE_WEBHOOK_SECRET",
  "NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY",
  "STRIPE_PRICE_PRO",
  "STRIPE_PRICE_BUSINESS",
  "SUPABASE_URL",
  "SUPABASE_SERVICE_ROLE_KEY"
)

$optionalVars = @(
  "NEXT_PUBLIC_SUPABASE_ANON_KEY",
  "VERIRULE_ENABLE_DEBUG_PAGES"
)

foreach ($name in $requiredVars) {
  Sync-VercelVar -name $name -target $Target -required $true
}

foreach ($name in $optionalVars) {
  Sync-VercelVar -name $name -target $Target -required $false
}

Write-Host "Vercel environment sync complete for target: $Target"
$global:LASTEXITCODE = 0
