create table if not exists public.notification_events (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.orgs(id) on delete cascade,
  user_id uuid references auth.users(id),
  job_id uuid not null references public.notification_jobs(id) on delete cascade,
  type text not null check (type in ('digest', 'immediate_alert')),
  entity_type text check (entity_type in ('alert', 'task', 'export', 'system')),
  entity_id uuid,
  subject text not null,
  status text not null check (status in ('queued', 'sent', 'failed')),
  attempts int not null default 0,
  last_error text,
  sent_at timestamptz,
  created_at timestamptz not null default now()
);

create unique index if not exists notification_events_job_user_idx
  on public.notification_events (job_id, user_id)
  where user_id is not null;

create index if not exists notification_events_org_created_idx
  on public.notification_events (org_id, created_at desc);

create index if not exists notification_events_user_created_idx
  on public.notification_events (user_id, created_at desc);

create index if not exists notification_events_job_idx
  on public.notification_events (job_id);

alter table public.notification_events enable row level security;

drop policy if exists "notification_events_select_org_member" on public.notification_events;
create policy "notification_events_select_org_member"
on public.notification_events for select
using (
  exists (
    select 1
    from public.org_members m
    where m.org_id = notification_events.org_id
      and m.user_id = auth.uid()
  )
);

drop policy if exists "notification_events_insert_service_role" on public.notification_events;
create policy "notification_events_insert_service_role"
on public.notification_events for insert
to service_role
with check (true);

drop policy if exists "notification_events_update_service_role" on public.notification_events;
create policy "notification_events_update_service_role"
on public.notification_events for update
to service_role
using (true)
with check (true);

create table if not exists public.notification_reads (
  user_id uuid not null,
  event_id uuid not null references public.notification_events(id) on delete cascade,
  read_at timestamptz not null default now(),
  primary key (user_id, event_id)
);

create index if not exists notification_reads_event_idx
  on public.notification_reads (event_id);

alter table public.notification_reads enable row level security;

drop policy if exists "notification_reads_select_self" on public.notification_reads;
create policy "notification_reads_select_self"
on public.notification_reads for select
using (user_id = auth.uid());

drop policy if exists "notification_reads_insert_self" on public.notification_reads;
create policy "notification_reads_insert_self"
on public.notification_reads for insert
with check (user_id = auth.uid());

drop policy if exists "notification_reads_delete_self" on public.notification_reads;
create policy "notification_reads_delete_self"
on public.notification_reads for delete
using (user_id = auth.uid());
