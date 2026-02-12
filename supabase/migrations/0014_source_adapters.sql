alter table public.sources
  add column if not exists kind text not null default 'html',
  add column if not exists config jsonb not null default '{}'::jsonb,
  add column if not exists title text;

update public.sources
set kind = 'rss'
where type = 'rss'
  and kind = 'html';

alter table public.sources drop constraint if exists sources_kind_check;
alter table public.sources
  add constraint sources_kind_check
  check (kind in ('html', 'rss', 'pdf', 'github_releases'));

alter table public.snapshots
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists canonical_title text,
  add column if not exists canonical_text text,
  add column if not exists item_id text,
  add column if not exists item_published_at timestamptz;

update public.snapshots
set created_at = fetched_at
where fetched_at is not null;

create index if not exists snapshots_org_source_created_at_idx
  on public.snapshots(org_id, source_id, created_at desc);

create index if not exists snapshots_source_item_id_idx
  on public.snapshots(source_id, item_id)
  where item_id is not null;

create or replace function public.create_source(
  p_org_id uuid,
  p_name text,
  p_type text,
  p_url text
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_kind text;
begin
  v_kind := case when p_type = 'rss' then 'rss' else 'html' end;
  return public.create_source_v2(
    p_org_id,
    p_name,
    p_type,
    p_url,
    v_kind,
    '{}'::jsonb,
    null
  );
end;
$$;

create or replace function public.create_source_v2(
  p_org_id uuid,
  p_name text,
  p_type text,
  p_url text,
  p_kind text default 'html',
  p_config jsonb default '{}'::jsonb,
  p_title text default null
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_source_id uuid;
  v_type text;
  v_kind text;
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

  v_kind := lower(coalesce(nullif(trim(p_kind), ''), 'html'));
  if v_kind not in ('html', 'rss', 'pdf', 'github_releases') then
    raise exception 'invalid source kind';
  end if;

  v_type := case
    when p_type in ('rss', 'url') then p_type
    when v_kind = 'rss' then 'rss'
    else 'url'
  end;

  insert into public.sources (org_id, name, type, url, kind, config, title)
  values (
    p_org_id,
    p_name,
    v_type,
    p_url,
    v_kind,
    coalesce(p_config, '{}'::jsonb),
    nullif(trim(coalesce(p_title, '')), '')
  )
  returning id into v_source_id;

  return v_source_id;
end;
$$;

revoke all on function public.create_source_v2(uuid,text,text,text,text,jsonb,text) from public;
grant execute on function public.create_source_v2(uuid,text,text,text,text,jsonb,text) to authenticated;

create or replace function public.update_source(
  p_source_id uuid,
  p_name text default null,
  p_url text default null,
  p_type text default null,
  p_kind text default null,
  p_config jsonb default null,
  p_title text default null,
  p_is_enabled boolean default null
)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_org_id uuid;
  v_kind text;
  v_type text;
begin
  v_user_id := auth.uid();
  if v_user_id is null then
    raise exception 'not authenticated';
  end if;

  select s.org_id, s.kind, s.type
  into v_org_id, v_kind, v_type
  from public.sources s
  where s.id = p_source_id;

  if v_org_id is null then
    raise exception 'source not found';
  end if;

  if not exists (
    select 1 from public.org_members m
    where m.org_id = v_org_id and m.user_id = v_user_id
  ) then
    raise exception 'not a member of org';
  end if;

  v_kind := lower(coalesce(nullif(trim(p_kind), ''), v_kind));
  if v_kind not in ('html', 'rss', 'pdf', 'github_releases') then
    raise exception 'invalid source kind';
  end if;

  v_type := case
    when p_type in ('rss', 'url') then p_type
    when v_kind = 'rss' then 'rss'
    else 'url'
  end;

  update public.sources
  set
    name = coalesce(nullif(trim(coalesce(p_name, '')), ''), name),
    url = coalesce(nullif(trim(coalesce(p_url, '')), ''), url),
    type = v_type,
    kind = v_kind,
    config = coalesce(p_config, config),
    title = case
      when p_title is null then title
      else nullif(trim(p_title), '')
    end,
    is_enabled = coalesce(p_is_enabled, is_enabled)
  where id = p_source_id;
end;
$$;

revoke all on function public.update_source(uuid,text,text,text,text,jsonb,text,boolean) from public;
grant execute on function public.update_source(uuid,text,text,text,text,jsonb,text,boolean) to authenticated;

create or replace function public.insert_snapshot_v3(
  p_org_id uuid,
  p_source_id uuid,
  p_run_id uuid,
  p_fetched_url text,
  p_content_hash text,
  p_content_type text,
  p_content_len bigint,
  p_http_status int,
  p_etag text,
  p_last_modified text,
  p_text_preview text,
  p_text_fingerprint text,
  p_canonical_title text,
  p_canonical_text text,
  p_item_id text,
  p_item_published_at timestamptz
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_snapshot_id uuid;
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

  if not exists (
    select 1 from public.monitor_runs r
    where r.id = p_run_id and r.org_id = p_org_id and r.source_id = p_source_id
  ) then
    raise exception 'run not found in org/source';
  end if;

  insert into public.snapshots (
    org_id,
    source_id,
    run_id,
    fetched_url,
    content_hash,
    content_type,
    content_len,
    http_status,
    etag,
    last_modified,
    text_preview,
    text_fingerprint,
    canonical_title,
    canonical_text,
    item_id,
    item_published_at
  )
  values (
    p_org_id,
    p_source_id,
    p_run_id,
    p_fetched_url,
    p_content_hash,
    p_content_type,
    p_content_len,
    p_http_status,
    p_etag,
    p_last_modified,
    p_text_preview,
    p_text_fingerprint,
    nullif(trim(coalesce(p_canonical_title, '')), ''),
    coalesce(p_canonical_text, ''),
    nullif(trim(coalesce(p_item_id, '')), ''),
    p_item_published_at
  )
  returning id into v_snapshot_id;

  return v_snapshot_id;
end;
$$;

revoke all on function public.insert_snapshot_v3(uuid,uuid,uuid,text,text,text,bigint,int,text,text,text,text,text,text,text,timestamptz) from public;
grant execute on function public.insert_snapshot_v3(uuid,uuid,uuid,text,text,text,bigint,int,text,text,text,text,text,text,text,timestamptz) to authenticated;
