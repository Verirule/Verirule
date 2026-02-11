create table if not exists public.org_billing (
  org_id uuid primary key references public.orgs(id) on delete cascade,
  plan text not null check (plan in ('free','pro','business')) default 'free',
  stripe_customer_id text,
  stripe_subscription_id text,
  stripe_price_id text,
  subscription_status text,
  current_period_end timestamptz,
  updated_at timestamptz not null default now()
);

alter table public.org_billing enable row level security;

drop policy if exists "org_billing_select_member" on public.org_billing;
create policy "org_billing_select_member"
on public.org_billing for select
using (
  exists (select 1 from public.org_members m where m.org_id = org_billing.org_id and m.user_id = auth.uid())
);

-- Only service role / webhook updates should write; no insert/update policies for authenticated.

create or replace function public.set_org_plan(
  p_org_id uuid,
  p_plan text,
  p_customer_id text,
  p_subscription_id text,
  p_price_id text,
  p_status text,
  p_current_period_end timestamptz
) returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.org_billing(org_id, plan, stripe_customer_id, stripe_subscription_id, stripe_price_id, subscription_status, current_period_end, updated_at)
  values (p_org_id, p_plan, p_customer_id, p_subscription_id, p_price_id, p_status, p_current_period_end, now())
  on conflict (org_id)
  do update set
    plan=excluded.plan,
    stripe_customer_id=excluded.stripe_customer_id,
    stripe_subscription_id=excluded.stripe_subscription_id,
    stripe_price_id=excluded.stripe_price_id,
    subscription_status=excluded.subscription_status,
    current_period_end=excluded.current_period_end,
    updated_at=now();
end;
$$;

-- Do NOT grant this to authenticated. Webhook will use service role via REST.
revoke all on function public.set_org_plan(uuid,text,text,text,text,text,timestamptz) from public;
grant execute on function public.set_org_plan(uuid,text,text,text,text,text,timestamptz) to service_role;
