-- Org roles + invite flow

-- Ensure org_members has required role constraints and metadata.
alter table if exists public.org_members
  add column if not exists role text not null default 'member',
  add column if not exists created_at timestamptz not null default now();

-- Enforce role domain for org membership.
do $$
begin
  if exists (
    select 1
    from information_schema.tables
    where table_schema = 'public' and table_name = 'org_members'
  ) and not exists (
    select 1
    from pg_constraint c
    join pg_class t on t.oid = c.conrelid
    join pg_namespace n on n.oid = t.relnamespace
    where n.nspname = 'public'
      and t.relname = 'org_members'
      and c.conname = 'org_members_role_check'
  ) then
    alter table public.org_members
      add constraint org_members_role_check
      check (role in ('owner', 'admin', 'member', 'viewer'));
  end if;
end
$$;

-- Ensure unique(org_id, user_id) even if primary key was not present in older setups.
do $$
begin
  if exists (
    select 1
    from information_schema.tables
    where table_schema = 'public' and table_name = 'org_members'
  ) and not exists (
    select 1
    from pg_constraint c
    join pg_class t on t.oid = c.conrelid
    join pg_namespace n on n.oid = t.relnamespace
    where n.nspname = 'public'
      and t.relname = 'org_members'
      and c.contype in ('p', 'u')
      and c.conkey::int[] = array[
        (select a.attnum from pg_attribute a where a.attrelid = t.oid and a.attname = 'org_id' and not a.attisdropped),
        (select a.attnum from pg_attribute a where a.attrelid = t.oid and a.attname = 'user_id' and not a.attisdropped)
      ]::int[]
  ) then
    alter table public.org_members
      add constraint org_members_org_id_user_id_key unique (org_id, user_id);
  end if;
end
$$;

alter table if exists public.org_members enable row level security;

drop policy if exists "org_members_select_self" on public.org_members;
drop policy if exists "org_members_select_member" on public.org_members;
create policy "org_members_select_member"
on public.org_members for select
using (
  exists (
    select 1
    from public.org_members m
    where m.org_id = org_members.org_id
      and m.user_id = auth.uid()
  )
);

drop policy if exists "org_members_insert_owner_admin" on public.org_members;
create policy "org_members_insert_owner_admin"
on public.org_members for insert
to authenticated
with check (
  exists (
    select 1
    from public.org_members m
    where m.org_id = org_members.org_id
      and m.user_id = auth.uid()
      and m.role in ('owner', 'admin')
  )
);

drop policy if exists "org_members_update_owner_admin" on public.org_members;
create policy "org_members_update_owner_admin"
on public.org_members for update
to authenticated
using (
  exists (
    select 1
    from public.org_members m
    where m.org_id = org_members.org_id
      and m.user_id = auth.uid()
      and m.role in ('owner', 'admin')
  )
)
with check (
  exists (
    select 1
    from public.org_members m
    where m.org_id = org_members.org_id
      and m.user_id = auth.uid()
      and m.role in ('owner', 'admin')
  )
);

drop policy if exists "org_members_delete_owner_admin" on public.org_members;
create policy "org_members_delete_owner_admin"
on public.org_members for delete
to authenticated
using (
  exists (
    select 1
    from public.org_members m
    where m.org_id = org_members.org_id
      and m.user_id = auth.uid()
      and m.role in ('owner', 'admin')
  )
);

create table if not exists public.org_invites (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.orgs(id) on delete cascade,
  email text not null,
  role text not null default 'member' check (role in ('admin', 'member', 'viewer')),
  token_hash text not null unique,
  invited_by uuid,
  expires_at timestamptz not null,
  accepted_at timestamptz,
  created_at timestamptz not null default now()
);

create unique index if not exists org_invites_pending_email_uniq
  on public.org_invites (org_id, email)
  where accepted_at is null;

create index if not exists org_invites_org_id_idx on public.org_invites(org_id);
create index if not exists org_invites_pending_idx on public.org_invites(org_id, expires_at)
  where accepted_at is null;

alter table public.org_invites enable row level security;

drop policy if exists "org_invites_select_member" on public.org_invites;
create policy "org_invites_select_member"
on public.org_invites for select
using (
  exists (
    select 1
    from public.org_members m
    where m.org_id = org_invites.org_id
      and m.user_id = auth.uid()
  )
);

drop policy if exists "org_invites_insert_admin" on public.org_invites;
create policy "org_invites_insert_admin"
on public.org_invites for insert
to authenticated
with check (
  exists (
    select 1
    from public.org_members m
    where m.org_id = org_invites.org_id
      and m.user_id = auth.uid()
      and m.role in ('owner', 'admin')
  )
);

drop policy if exists "org_invites_update_admin" on public.org_invites;
create policy "org_invites_update_admin"
on public.org_invites for update
to authenticated
using (
  exists (
    select 1
    from public.org_members m
    where m.org_id = org_invites.org_id
      and m.user_id = auth.uid()
      and m.role in ('owner', 'admin')
  )
)
with check (
  exists (
    select 1
    from public.org_members m
    where m.org_id = org_invites.org_id
      and m.user_id = auth.uid()
      and m.role in ('owner', 'admin')
  )
);

drop policy if exists "org_invites_delete_admin" on public.org_invites;
create policy "org_invites_delete_admin"
on public.org_invites for delete
to authenticated
using (
  exists (
    select 1
    from public.org_members m
    where m.org_id = org_invites.org_id
      and m.user_id = auth.uid()
      and m.role in ('owner', 'admin')
  )
);

-- Prevent authenticated users from reading token hashes.
revoke select (token_hash) on public.org_invites from anon;
revoke select (token_hash) on public.org_invites from authenticated;
grant select (token_hash) on public.org_invites to service_role;

create or replace function public.require_org_role(p_org_id uuid, p_min_role text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_user_role text;
  v_user_rank int;
  v_min_rank int;
begin
  v_user_id := auth.uid();
  if v_user_id is null then
    raise exception 'not authenticated';
  end if;

  select m.role
    into v_user_role
  from public.org_members m
  where m.org_id = p_org_id
    and m.user_id = v_user_id
  limit 1;

  if v_user_role is null then
    raise exception 'not a member of org';
  end if;

  v_min_rank := case p_min_role
    when 'viewer' then 1
    when 'member' then 2
    when 'admin' then 3
    when 'owner' then 4
    else null
  end;

  if v_min_rank is null then
    raise exception 'invalid role';
  end if;

  v_user_rank := case v_user_role
    when 'viewer' then 1
    when 'member' then 2
    when 'admin' then 3
    when 'owner' then 4
    else 0
  end;

  if v_user_rank < v_min_rank then
    raise exception 'insufficient org role';
  end if;
end;
$$;

revoke all on function public.require_org_role(uuid, text) from public;
grant execute on function public.require_org_role(uuid, text) to authenticated;
grant execute on function public.require_org_role(uuid, text) to service_role;

create or replace function public.create_org_invite(
  p_org_id uuid,
  p_email text,
  p_role text default 'member',
  p_expires_hours int default 72
)
returns table(invite_id uuid, token text)
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_role text;
  v_email text;
  v_token text;
  v_token_hash text;
  v_expires_at timestamptz;
begin
  v_user_id := auth.uid();
  if v_user_id is null then
    raise exception 'not authenticated';
  end if;

  perform public.require_org_role(p_org_id, 'admin');

  v_role := lower(trim(coalesce(p_role, 'member')));
  if v_role not in ('admin', 'member', 'viewer') then
    raise exception 'invalid invite role';
  end if;

  v_email := lower(trim(coalesce(p_email, '')));
  if v_email = '' then
    raise exception 'email is required';
  end if;

  if p_expires_hours is null or p_expires_hours < 1 or p_expires_hours > 720 then
    raise exception 'invalid expires_hours';
  end if;

  v_token := encode(gen_random_bytes(32), 'hex');
  v_token_hash := encode(digest(v_token, 'sha256'), 'hex');
  v_expires_at := now() + make_interval(hours => p_expires_hours);

  update public.org_invites
  set
    role = v_role,
    token_hash = v_token_hash,
    invited_by = v_user_id,
    expires_at = v_expires_at,
    accepted_at = null,
    created_at = now()
  where org_id = p_org_id
    and email = v_email
    and accepted_at is null
  returning id into invite_id;

  if invite_id is null then
    insert into public.org_invites (
      org_id,
      email,
      role,
      token_hash,
      invited_by,
      expires_at
    )
    values (
      p_org_id,
      v_email,
      v_role,
      v_token_hash,
      v_user_id,
      v_expires_at
    )
    returning id into invite_id;
  end if;

  token := v_token;
  return next;
end;
$$;

revoke all on function public.create_org_invite(uuid, text, text, int) from public;
grant execute on function public.create_org_invite(uuid, text, text, int) to authenticated;
grant execute on function public.create_org_invite(uuid, text, text, int) to service_role;

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
begin
  v_user_id := auth.uid();
  if v_user_id is null then
    raise exception 'not authenticated';
  end if;

  if p_token is null or trim(p_token) = '' then
    raise exception 'token is required';
  end if;

  v_token_hash := encode(digest(trim(p_token), 'sha256'), 'hex');

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

  insert into public.org_members (org_id, user_id, role)
  values (v_invite.org_id, v_user_id, v_invite.role)
  on conflict (org_id, user_id)
  do update
    set role = excluded.role;

  update public.org_invites
  set accepted_at = now()
  where id = v_invite.id;

  return v_invite.org_id;
end;
$$;

revoke all on function public.accept_org_invite(text) from public;
grant execute on function public.accept_org_invite(text) to authenticated;
grant execute on function public.accept_org_invite(text) to service_role;
