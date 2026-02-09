create table if not exists public.sources (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.orgs(id) on delete cascade,
  name text not null,
  type text not null check (type in ('rss','url')),
  url text not null,
  is_enabled boolean not null default true,
  created_at timestamptz not null default now()
);

create index if not exists sources_org_id_idx on public.sources(org_id);

alter table public.sources enable row level security;

-- Members can read sources in their orgs
drop policy if exists "sources_select_member" on public.sources;
create policy "sources_select_member"
on public.sources for select
using (
  exists (
    select 1 from public.org_members m
    where m.org_id = sources.org_id
      and m.user_id = auth.uid()
  )
);

-- No direct writes; use RPC
-- RPC: create_source
create or replace function public.create_source(p_org_id uuid, p_name text, p_type text, p_url text)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_source_id uuid;
begin
  v_user_id := auth.uid();
  if v_user_id is null then
    raise exception 'not authenticated';
  end if;

  if not exists (
    select 1 from public.org_members m
    where m.org_id = p_org_id and m.user_id = v_user_id
  ) then
    raise exception 'not a member of org';
  end if;

  insert into public.sources (org_id, name, type, url)
  values (p_org_id, p_name, p_type, p_url)
  returning id into v_source_id;

  return v_source_id;
end;
$$;

revoke all on function public.create_source(uuid,text,text,text) from public;
grant execute on function public.create_source(uuid,text,text,text) to authenticated;

-- RPC: toggle_source
create or replace function public.toggle_source(p_source_id uuid, p_is_enabled boolean)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_org_id uuid;
begin
  v_user_id := auth.uid();
  if v_user_id is null then
    raise exception 'not authenticated';
  end if;

  select org_id into v_org_id from public.sources where id = p_source_id;
  if v_org_id is null then
    raise exception 'source not found';
  end if;

  if not exists (
    select 1 from public.org_members m
    where m.org_id = v_org_id and m.user_id = v_user_id
  ) then
    raise exception 'not a member of org';
  end if;

  update public.sources
  set is_enabled = p_is_enabled
  where id = p_source_id;
end;
$$;

revoke all on function public.toggle_source(uuid,boolean) from public;
grant execute on function public.toggle_source(uuid,boolean) to authenticated;
