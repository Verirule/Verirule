# Verirule

Verirule is an AI compliance monitoring platform that tracks regulatory change and alerts teams before requirements drift.

## What it does

- Monitors policy and regulatory updates
- Surfaces risk and change impact in plain language
- Sends auditable alerts for review and action

## Tech stack

- `apps/web`: Next.js + TypeScript + Tailwind CSS
- `apps/api`: FastAPI (Python)
- Supabase for auth and data services

## OAuth Setup (Web)

Set these variables for `apps/web`:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (or `NEXT_PUBLIC_SUPABASE_ANON_KEY`)
- `NEXT_PUBLIC_SUPABASE_OAUTH_PROVIDERS` (example: `google,github,apple,azure`)
- `NEXT_PUBLIC_SITE_URL` (your public app URL, required in production)

Supabase dashboard checklist:

- `Authentication` -> `Providers`: enable the same providers listed in `NEXT_PUBLIC_SUPABASE_OAUTH_PROVIDERS`
- `Authentication` -> `URL Configuration`: add callback URL `https://YOUR_DOMAIN/auth/callback`

Deployment env and secrets guidance:

- `docs/DEPLOYMENT_ENV.md`

## Socials

- Discord: https://discord.gg/
- X: https://x.com/verirule

License: GNU AGPLv3 (see LICENSE)
