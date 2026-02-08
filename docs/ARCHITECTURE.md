# Verirule Architecture

## Core Services
- `apps/web`: Next.js frontend (TypeScript/Tailwind) for dashboards, auth flows, and alert configuration.
- `apps/api`: FastAPI backend for orchestration, ingestion logic, policy evaluation, and notifications.
- Supabase: Auth + Postgres as the system of record for users, orgs, memberships, sources, rules, and alerts.
- Future worker: Celery + Redis for scheduled fetch/normalize/diff jobs and outbound notification fan-out.

## Auth Model
- Frontend uses Supabase Auth session for user login and token acquisition.
- Backend validates Supabase JWTs using Supabase JWKS and rejects unverifiable/expired tokens.
- API authorization is enforced with org membership checks and role-based permissions.

## Multi-Tenancy
- Tenant model is organization-centric: `orgs` + `memberships`.
- Data access is scoped to org context for all queries and write operations.
- Membership roles control capabilities (admin, analyst, viewer, etc.).

## Monitoring Pipeline
- `sources -> fetch -> normalize -> diff -> store -> notify`
- Fetchers collect raw updates from configured sources.
- Normalizers convert source data to canonical regulatory change events.
- Diffing compares new events against last known state.
- Storage persists events, diffs, and alert decisions.
- Notifiers dispatch channel-specific alerts (email, Slack, future integrations).
