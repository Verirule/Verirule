create table if not exists public.billing_events (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.orgs(id) on delete cascade,
  stripe_event_id text not null,
  event_type text not null,
  created_at timestamptz not null default now(),
  processed_at timestamptz,
  status text not null default 'received',
  error text,
  constraint billing_events_status_check check (status in ('received', 'processed', 'failed')),
  constraint billing_events_org_event_unique unique (org_id, stripe_event_id)
);

alter table public.billing_events enable row level security;

drop policy if exists "billing_events_select_member" on public.billing_events;
create policy "billing_events_select_member"
on public.billing_events for select
using (
  exists (
    select 1
    from public.org_members m
    where m.org_id = billing_events.org_id
      and m.user_id = auth.uid()
  )
);

drop policy if exists "billing_events_insert_service_role" on public.billing_events;
create policy "billing_events_insert_service_role"
on public.billing_events for insert
with check (auth.role() = 'service_role');

drop policy if exists "billing_events_update_service_role" on public.billing_events;
create policy "billing_events_update_service_role"
on public.billing_events for update
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

alter table public.orgs
  add column if not exists stripe_customer_id text,
  add column if not exists stripe_subscription_id text,
  add column if not exists plan text not null default 'free',
  add column if not exists plan_status text not null default 'active',
  add column if not exists current_period_end timestamptz;

alter table public.orgs
  drop constraint if exists orgs_plan_check;

alter table public.orgs
  add constraint orgs_plan_check check (plan in ('free', 'pro', 'business'));

alter table public.orgs
  drop constraint if exists orgs_plan_status_check;

alter table public.orgs
  add constraint orgs_plan_status_check check (plan_status in ('active', 'past_due', 'canceled', 'trialing'));

update public.orgs o
set
  stripe_customer_id = coalesce(o.stripe_customer_id, b.stripe_customer_id),
  stripe_subscription_id = coalesce(o.stripe_subscription_id, b.stripe_subscription_id),
  plan = case
    when b.plan in ('free', 'pro', 'business') then b.plan
    else o.plan
  end,
  plan_status = case
    when b.subscription_status in ('active', 'past_due', 'canceled', 'trialing') then b.subscription_status
    else o.plan_status
  end,
  current_period_end = coalesce(o.current_period_end, b.current_period_end)
from public.org_billing b
where b.org_id = o.id;
