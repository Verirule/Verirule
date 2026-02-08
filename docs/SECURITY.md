# Verirule Security Baseline

## Secrets Management
- Keep secrets only in environment variables.
- Commit only `.env.example` templates.
- Never hardcode API keys, service-role credentials, or signing secrets in source.

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
