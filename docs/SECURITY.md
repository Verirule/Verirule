# Verirule Security Baseline

## Secrets Management
- Keep secrets only in environment variables.
- Commit only `.env.example` templates.
- Never hardcode API keys, service-role credentials, or signing secrets in source.
- `SUPABASE_SERVICE_ROLE_KEY` is server-only (Fly secrets for API/worker) and must never be exposed to browsers.

## Web Environment Guardrail
- Never set `POSTGRES_URL`, `DATABASE_URL`, or any DB credentials in the web (`apps/web`) environment.
- Only use public Supabase URL + publishable/anon keys in web.
- Never set `SUPABASE_SERVICE_ROLE_KEY` in Vercel or any `NEXT_PUBLIC_*` variable.

## Storage
- Create a Supabase Storage bucket named `evidence` and keep it private.
- Bucket public access must remain `OFF`.
- File evidence paths must follow: `org/<org_id>/tasks/<task_id>/<uuid>-<filename>`.
- Signed upload/download URLs must be short-lived and generated only by the API.
- `SUPABASE_SERVICE_ROLE_KEY` for storage signing must live only in Fly secrets for the API.

Checklist:
- Supabase dashboard -> `Storage` -> `Create bucket`
- Name: `evidence`
- Public bucket: `OFF`

## Authentication and Token Verification
- Frontend may hold Supabase session state, but backend must never trust session cookies directly.
- Backend verifies Supabase JWTs with Supabase JWKS (issuer, audience, signature, expiry checks).
- Reject tokens that fail verification or org-level authorization checks.

## Tenant Isolation
- Use Supabase Row Level Security (RLS) to isolate tenant data by organization.
- Enforce org scoping in both database policies and backend service-layer checks.
- Keep privileged operations behind explicit role checks.

## API and Platform Hardening
- Apply per-IP and per-user rate limiting on authentication and ingestion endpoints.
- Maintain audit logs for login events, role changes, source edits, and alert-delivery actions.
- Add SSRF protections for URL fetching: allowlist schemes, block private CIDRs, validate DNS/redirects.
- Use safe file handling: strict type/size limits, malware scanning hooks, and no unsafe path joins.

## Recommended Web Security Headers
- `Content-Security-Policy`
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy`
- `Strict-Transport-Security`
- `Permissions-Policy`

## Domain and OAuth Redirects
- Custom domains are configured via Vercel.
- No domain is hardcoded in source; site origin is resolved dynamically.
- OAuth callback redirects are validated against allowed same-origin targets only.
