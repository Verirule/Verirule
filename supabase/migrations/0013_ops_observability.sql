create table if not exists public.system_status (
  id text primary key, -- e.g. 'worker'
  updated_at timestamptz not null default now(),
  payload jsonb not null default '{}'::jsonb
);

alter table public.system_status enable row level security;

-- Only allow authenticated org members to read via a viewless endpoint:
-- We'll keep select policy open only for authenticated (safer than public).
drop policy if exists "system_status_select_authenticated" on public.system_status;
create policy "system_status_select_authenticated"
on public.system_status for select
using (auth.role() = 'authenticated');

-- no direct writes except service role via API

-- add retry/dead-letter fields to monitor_runs and audit_exports
alter table public.monitor_runs
  add column if not exists attempts int not null default 0,
  add column if not exists next_attempt_at timestamptz,
  add column if not exists last_error text;

alter table public.audit_exports
  add column if not exists attempts int not null default 0,
  add column if not exists next_attempt_at timestamptz,
  add column if not exists last_error text;
