# Verirule

Vertical AI SaaS for compliance monitoring: track regulatory changes and send automated alerts to businesses.

## Monorepo structure

- `apps/api` — FastAPI backend (Python)
- `apps/web` — Next.js frontend (TypeScript/Tailwind)
- `packages/shared` — shared types/utilities (optional)
- `supabase` — Supabase project config (local dev scaffolding)
- `docs` — documentation
- `scripts` — helper scripts

## Security

- **Never commit secrets**.
- Use `.env` files locally and commit only `.env.example` templates.

## Getting started (placeholder)

Scaffolding only (Task 1). Next tasks will:
- Bootstrap FastAPI + Next.js apps
- Add Supabase config + auth
- Add regulatory change monitoring pipeline
