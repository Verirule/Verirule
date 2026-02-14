param(
  [Parameter(Mandatory = $true)]
  [string]$ApiApp,

  [Parameter(Mandatory = $true)]
  [string]$WorkerApp
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

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

function Build-SecretsLines(
  [string[]]$requiredNames,
  [string[]]$optionalNames,
  [hashtable]$fixedValues
) {
  $lines = New-Object System.Collections.Generic.List[string]

  foreach ($name in $requiredNames) {
    $value = Get-SecretEnv -name $name -required $true
    $lines.Add("$name=$value")
  }

  foreach ($name in $optionalNames) {
    $value = Get-SecretEnv -name $name -required $false
    if ($null -ne $value) {
      $lines.Add("$name=$value")
    }
  }

  foreach ($key in $fixedValues.Keys) {
    $lines.Add("$key=$($fixedValues[$key])")
  }

  return $lines
}

function Import-FlySecrets([string]$app, [System.Collections.Generic.List[string]]$lines) {
  $tempFile = New-TemporaryFile
  try {
    Set-Content -Path $tempFile -Value ($lines -join [Environment]::NewLine)
    Get-Content -Path $tempFile | flyctl secrets import -a $app *> $null
  }
  finally {
    Remove-Item -Path $tempFile -Force -ErrorAction SilentlyContinue
  }
  Write-Host "Synced Fly secrets for app: $app"
}

Require-Cli "flyctl"

$sharedRequired = @(
  "VERIRULE_ENV",
  "LOG_LEVEL",
  "NEXT_PUBLIC_SITE_URL",
  "SUPABASE_URL",
  "SUPABASE_ANON_KEY",
  "SUPABASE_SERVICE_ROLE_KEY",
  "SUPABASE_ISSUER",
  "SUPABASE_JWKS_URL",
  "EMAIL_FROM",
  "SMTP_HOST",
  "SMTP_PORT",
  "SMTP_USERNAME",
  "SMTP_PASSWORD",
  "SMTP_USE_TLS",
  "SMTP_USE_SSL",
  "DIGEST_SEND_HOUR_UTC",
  "DIGEST_BATCH_LIMIT",
  "NOTIFY_JOB_BATCH_LIMIT",
  "NOTIFY_MAX_ATTEMPTS",
  "DIGEST_PROCESSOR_INTERVAL_SECONDS"
)

$apiRequired = @(
  "API_HOST",
  "API_PORT",
  "API_CORS_ORIGINS",
  "SLACK_ALERT_NOTIFICATIONS_ENABLED",
  "INTEGRATIONS_ENCRYPTION_KEY",
  "VERIRULE_SECRETS_KEY"
)

$workerRequired = @(
  "WORKER_POLL_INTERVAL_SECONDS",
  "WORKER_BATCH_LIMIT",
  "WORKER_FETCH_TIMEOUT_SECONDS",
  "WORKER_FETCH_MAX_BYTES",
  "READINESS_COMPUTE_INTERVAL_SECONDS",
  "EXPORTS_BUCKET_NAME",
  "EXPORT_SIGNED_URL_SECONDS",
  "EVIDENCE_BUCKET_NAME",
  "EVIDENCE_SIGNED_URL_SECONDS",
  "MAX_EVIDENCE_UPLOAD_BYTES",
  "AUDIT_PACKET_MAX_EVIDENCE_FILES",
  "AUDIT_PACKET_MAX_TOTAL_BYTES",
  "AUDIT_PACKET_MAX_FILE_BYTES",
  "WORKER_STALE_AFTER_SECONDS"
)

$optionalBoth = @("WORKER_SUPABASE_ACCESS_TOKEN")

$apiLines = Build-SecretsLines `
  -requiredNames ($sharedRequired + $apiRequired) `
  -optionalNames $optionalBoth `
  -fixedValues @{ VERIRULE_MODE = "api" }

$workerLines = Build-SecretsLines `
  -requiredNames ($sharedRequired + $workerRequired) `
  -optionalNames $optionalBoth `
  -fixedValues @{ VERIRULE_MODE = "worker" }

Import-FlySecrets -app $ApiApp -lines $apiLines
Import-FlySecrets -app $WorkerApp -lines $workerLines

Write-Host "Fly secrets sync complete."
