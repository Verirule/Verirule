create table if not exists public.org_notification_rules (
  org_id uuid primary key references public.orgs(id) on delete cascade,
  enabled boolean not null default true,
  mode text not null default 'digest'
    check (mode in ('digest', 'immediate', 'both')),
  digest_cadence text not null default 'daily'
    check (digest_cadence in ('daily', 'weekly')),
  min_severity text not null default 'medium'
    check (min_severity in ('low', 'medium', 'high')),
  last_digest_sent_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

drop trigger if exists set_org_notification_rules_updated_at on public.org_notification_rules;
create trigger set_org_notification_rules_updated_at
before update on public.org_notification_rules
for each row execute function public.set_updated_at();

alter table public.org_notification_rules enable row level security;

drop policy if exists "org_notification_rules_select_member" on public.org_notification_rules;
create policy "org_notification_rules_select_member"
on public.org_notification_rules for select
using (
  exists (
    select 1
    from public.org_members m
    where m.org_id = org_notification_rules.org_id
      and m.user_id = auth.uid()
  )
);

drop policy if exists "org_notification_rules_insert_admin_owner" on public.org_notification_rules;
create policy "org_notification_rules_insert_admin_owner"
on public.org_notification_rules for insert
with check (
  exists (
    select 1
    from public.org_members m
    where m.org_id = org_notification_rules.org_id
      and m.user_id = auth.uid()
      and m.role in ('owner', 'admin')
  )
);

drop policy if exists "org_notification_rules_update_admin_owner" on public.org_notification_rules;
create policy "org_notification_rules_update_admin_owner"
on public.org_notification_rules for update
using (
  exists (
    select 1
    from public.org_members m
    where m.org_id = org_notification_rules.org_id
      and m.user_id = auth.uid()
      and m.role in ('owner', 'admin')
  )
)
with check (
  exists (
    select 1
    from public.org_members m
    where m.org_id = org_notification_rules.org_id
      and m.user_id = auth.uid()
      and m.role in ('owner', 'admin')
  )
);

create table if not exists public.user_notification_prefs (
  user_id uuid primary key,
  email_enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

drop trigger if exists set_user_notification_prefs_updated_at on public.user_notification_prefs;
create trigger set_user_notification_prefs_updated_at
before update on public.user_notification_prefs
for each row execute function public.set_updated_at();

alter table public.user_notification_prefs enable row level security;

drop policy if exists "user_notification_prefs_select_self" on public.user_notification_prefs;
create policy "user_notification_prefs_select_self"
on public.user_notification_prefs for select
using (user_id = auth.uid());

drop policy if exists "user_notification_prefs_insert_self" on public.user_notification_prefs;
create policy "user_notification_prefs_insert_self"
on public.user_notification_prefs for insert
with check (user_id = auth.uid());

drop policy if exists "user_notification_prefs_update_self" on public.user_notification_prefs;
create policy "user_notification_prefs_update_self"
on public.user_notification_prefs for update
using (user_id = auth.uid())
with check (user_id = auth.uid());

create or replace function public.ensure_org_notification_rules(p_org_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
begin
  if auth.role() <> 'service_role' then
    v_user_id := auth.uid();
    if v_user_id is null then
      raise exception 'not authenticated';
    end if;

    if not exists (
      select 1
      from public.org_members m
      where m.org_id = p_org_id
        and m.user_id = v_user_id
    ) then
      raise exception 'not a member of org';
    end if;
  end if;

  insert into public.org_notification_rules(org_id)
  values (p_org_id)
  on conflict (org_id) do nothing;
end;
$$;

revoke all on function public.ensure_org_notification_rules(uuid) from public;
grant execute on function public.ensure_org_notification_rules(uuid) to authenticated;
grant execute on function public.ensure_org_notification_rules(uuid) to service_role;

create or replace function public.ensure_user_notification_prefs()
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
begin
  v_user_id := auth.uid();
  if v_user_id is null then
    raise exception 'not authenticated';
  end if;

  insert into public.user_notification_prefs(user_id)
  values (v_user_id)
  on conflict (user_id) do nothing;
end;
$$;

revoke all on function public.ensure_user_notification_prefs() from public;
grant execute on function public.ensure_user_notification_prefs() to authenticated;
