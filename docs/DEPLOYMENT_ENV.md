# Deployment Environment (Security First)

This project is configured to keep secrets out of git. Never commit real keys.

## 1) Rotate Exposed Keys

If any key was ever pasted in chat/logs/screenshots, rotate it in the provider dashboard first:

- Stripe: secret key, webhook secret
- Supabase: service role key, secret key
- SMTP provider credentials

## 2) Vercel Variables (Web)

Set these as Vercel project env vars:

- `NEXT_PUBLIC_SITE_URL`
- `VERIRULE_API_URL`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` (optional compatibility)
- `NEXT_PUBLIC_SUPABASE_OAUTH_PROVIDERS`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`
- `STRIPE_PRICE_PRO`
- `STRIPE_PRICE_BUSINESS`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `VERIRULE_ENABLE_DEBUG_PAGES` (optional)

Webhook URL:

- `https://www.verirule.com/api/stripe/webhook`

Required Stripe webhook events:

- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`

## 3) Fly Variables (API + Worker)

Set these in Fly secrets for both API and Worker (plus mode-specific variables):

- `VERIRULE_ENV`
- `VERIRULE_MODE` (`api` for API app, `worker` for Worker app)
- `LOG_LEVEL`
- `NEXT_PUBLIC_SITE_URL`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_ISSUER`
- `SUPABASE_JWKS_URL`
- `EMAIL_FROM`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_USE_TLS`
- `SMTP_USE_SSL`
- `DIGEST_SEND_HOUR_UTC`
- `DIGEST_BATCH_LIMIT`
- `NOTIFY_JOB_BATCH_LIMIT`
- `NOTIFY_MAX_ATTEMPTS`
- `DIGEST_PROCESSOR_INTERVAL_SECONDS`

API-only:

- `API_HOST`
- `API_PORT`
- `API_CORS_ORIGINS`
- `SLACK_ALERT_NOTIFICATIONS_ENABLED`
- `INTEGRATIONS_ENCRYPTION_KEY`
- `VERIRULE_SECRETS_KEY`

Worker-only:

- `WORKER_POLL_INTERVAL_SECONDS`
- `WORKER_BATCH_LIMIT`
- `WORKER_FETCH_TIMEOUT_SECONDS`
- `WORKER_FETCH_MAX_BYTES`
- `READINESS_COMPUTE_INTERVAL_SECONDS`
- `EXPORTS_BUCKET_NAME`
- `EXPORT_SIGNED_URL_SECONDS`
- `EVIDENCE_BUCKET_NAME`
- `EVIDENCE_SIGNED_URL_SECONDS`
- `MAX_EVIDENCE_UPLOAD_BYTES`
- `AUDIT_PACKET_MAX_EVIDENCE_FILES`
- `AUDIT_PACKET_MAX_TOTAL_BYTES`
- `AUDIT_PACKET_MAX_FILE_BYTES`
- `WORKER_STALE_AFTER_SECONDS`

Optional:

- `WORKER_SUPABASE_ACCESS_TOKEN`

## 4) Safe Sync Scripts

Use these scripts after exporting secrets into your local shell environment:

- `scripts/deploy/sync-vercel-env.ps1`
- `scripts/deploy/sync-fly-secrets.ps1`

Examples:

```powershell
.\scripts\deploy\sync-vercel-env.ps1 -Target production
.\scripts\deploy\sync-fly-secrets.ps1 -ApiApp verirule-api -WorkerApp verirule-worker
```

The scripts sync only by variable name and do not store secrets in repository files.
