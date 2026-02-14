alter table if exists public.org_members
  add column if not exists user_email text;

create index if not exists org_members_org_id_user_email_idx
  on public.org_members (org_id, user_email);

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

create table if not exists public.notification_jobs (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.orgs(id) on delete cascade,
  type text not null check (type in ('digest', 'immediate_alert')),
  payload jsonb not null,
  status text not null default 'queued'
    check (status in ('queued', 'running', 'sent', 'failed')),
  attempts int not null default 0,
  last_error text,
  run_after timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists notification_jobs_status_run_after_idx
  on public.notification_jobs (status, run_after);

drop trigger if exists set_notification_jobs_updated_at on public.notification_jobs;
create trigger set_notification_jobs_updated_at
before update on public.notification_jobs
for each row execute function public.set_updated_at();

alter table public.notification_jobs enable row level security;

drop policy if exists "notification_jobs_select_service_role" on public.notification_jobs;
create policy "notification_jobs_select_service_role"
on public.notification_jobs for select
to service_role
using (true);

drop policy if exists "notification_jobs_insert_service_role" on public.notification_jobs;
create policy "notification_jobs_insert_service_role"
on public.notification_jobs for insert
to service_role
with check (true);

drop policy if exists "notification_jobs_update_service_role" on public.notification_jobs;
create policy "notification_jobs_update_service_role"
on public.notification_jobs for update
to service_role
using (true)
with check (true);

drop policy if exists "notification_jobs_delete_service_role" on public.notification_jobs;
create policy "notification_jobs_delete_service_role"
on public.notification_jobs for delete
to service_role
using (true);

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
grant execute on function public.ensure_user_notification_prefs() to service_role;

create or replace function public.upsert_my_email(p_org_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_email text;
begin
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

  v_email := lower(trim(coalesce(auth.jwt() ->> 'email', '')));
  if v_email = '' then
    return;
  end if;

  update public.org_members
  set user_email = v_email
  where org_id = p_org_id
    and user_id = v_user_id
    and (user_email is null or trim(user_email) = '');
end;
$$;

revoke all on function public.upsert_my_email(uuid) from public;
grant execute on function public.upsert_my_email(uuid) to authenticated;
grant execute on function public.upsert_my_email(uuid) to service_role;

create or replace function public.accept_org_invite(p_token text)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_token_hash text;
  v_invite record;
  v_user_email text;
begin
  v_user_id := auth.uid();
  if v_user_id is null then
    raise exception 'not authenticated';
  end if;

  if p_token is null or trim(p_token) = '' then
    raise exception 'token is required';
  end if;

  v_token_hash := encode(digest(trim(p_token), 'sha256'), 'hex');
  v_user_email := lower(trim(coalesce(auth.jwt() ->> 'email', '')));
  if v_user_email = '' then
    v_user_email := null;
  end if;

  select i.*
    into v_invite
  from public.org_invites i
  where i.token_hash = v_token_hash
    and i.accepted_at is null
    and i.expires_at > now()
  for update;

  if not found then
    raise exception 'invite is invalid or expired';
  end if;

  insert into public.org_members (org_id, user_id, role, user_email)
  values (v_invite.org_id, v_user_id, v_invite.role, v_user_email)
  on conflict (org_id, user_id)
  do update
    set role = excluded.role,
        user_email = coalesce(org_members.user_email, excluded.user_email);

  update public.org_invites
  set accepted_at = now()
  where id = v_invite.id;

  return v_invite.org_id;
end;
$$;

revoke all on function public.accept_org_invite(text) from public;
grant execute on function public.accept_org_invite(text) to authenticated;
grant execute on function public.accept_org_invite(text) to service_role;

create or replace function public.create_org(p_name text)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_org_id uuid;
  v_user_id uuid;
  v_name text;
  v_lock_key bigint;
  v_user_email text;
begin
  v_user_id := auth.uid();
  if v_user_id is null then
    raise exception 'not authenticated';
  end if;

  v_name := nullif(trim(p_name), '');
  if v_name is null then
    raise exception 'org name is required';
  end if;

  if char_length(v_name) < 2 or char_length(v_name) > 64 then
    raise exception 'org name must be between 2 and 64 characters';
  end if;

  v_user_email := lower(trim(coalesce(auth.jwt() ->> 'email', '')));
  if v_user_email = '' then
    v_user_email := null;
  end if;

  v_lock_key := hashtext(v_user_id::text || ':' || lower(v_name))::bigint;
  perform pg_advisory_xact_lock(v_lock_key);

  select o.id
    into v_org_id
    from public.orgs o
    inner join public.org_members m
      on m.org_id = o.id
   where m.user_id = v_user_id
     and lower(trim(o.name)) = lower(v_name)
   order by o.created_at asc
   limit 1;

  if v_org_id is not null then
    update public.org_members
    set user_email = coalesce(user_email, v_user_email)
    where org_id = v_org_id
      and user_id = v_user_id;
    return v_org_id;
  end if;

  insert into public.orgs (name)
  values (v_name)
  returning id into v_org_id;

  insert into public.org_members (org_id, user_id, role, user_email)
  values (v_org_id, v_user_id, 'owner', v_user_email)
  on conflict (org_id, user_id)
  do update
    set user_email = coalesce(org_members.user_email, excluded.user_email);

  insert into public.alert_task_rules (org_id)
  values (v_org_id)
  on conflict (org_id) do nothing;

  return v_org_id;
end;
$$;

revoke all on function public.create_org(text) from public;
grant execute on function public.create_org(text) to authenticated;
