# Verirule

Monorepo for the Verirule AI SaaS project.

Structure:
- backend/ : FastAPI service (Python)
- frontend/ : Next.js app (TypeScript)
- scripts/ : automation and tooling

## Deployment

### Frontend (Vercel)
1. Push to GitHub.
2. Create a new Vercel project and import the repo.
3. Set the project root to rontend.
4. Add environment variables:
   - NEXT_PUBLIC_API_BASE_URL
   - NEXT_PUBLIC_SUPABASE_URL
   - NEXT_PUBLIC_SUPABASE_ANON_KEY
5. Deploy.

### Backend (Render)
1. Push to GitHub.
2. Create a new Render web service and connect the repo.
3. Set the root directory to ackend.
4. Set the start command:
   - python -m uvicorn app.main:app --host 0.0.0.0 --port 10000
5. Add environment variables:
   - SECRET_KEY
   - DATABASE_URL
   - SUPABASE_URL
   - SUPABASE_API_KEY
   - SUPABASE_SERVICE_ROLE_KEY
   - SUPABASE_JWT_SECRET
   - ALLOWED_HOSTS
   - JWT_ALGORITHM
   - INGESTION_FEED_URL
   - EMAIL_PROVIDER
   - SMTP_HOST
   - SMTP_PORT
   - SMTP_USER
   - SMTP_PASSWORD
   - SMTP_FROM
   - DASHBOARD_URL
   - ALERTS_MAX_PER_RUN
   - RATE_LIMIT_WINDOW_SECONDS
   - RATE_LIMIT_MAX_REQUESTS
6. Deploy.

### Supabase
- Enable RLS on all tables.
- Configure JWT secret in SUPABASE_JWT_SECRET.
- Service role key must never be exposed to frontend.
