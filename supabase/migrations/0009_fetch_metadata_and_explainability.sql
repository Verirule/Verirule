alter table public.sources
  add column if not exists etag text,
  add column if not exists last_modified text,
  add column if not exists content_type text;

alter table public.snapshots
  add column if not exists http_status int,
  add column if not exists etag text,
  add column if not exists last_modified text,
  add column if not exists text_preview text,
  add column if not exists text_fingerprint text;

alter table public.snapshots
  alter column fetched_at set default now();

create table if not exists public.finding_explanations (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.orgs(id) on delete cascade,
  finding_id uuid not null references public.findings(id) on delete cascade,
  summary text not null,
  diff_preview text,
  citations jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists finding_explanations_org_id_idx
  on public.finding_explanations(org_id);
create index if not exists finding_explanations_finding_id_idx
  on public.finding_explanations(finding_id);
create index if not exists finding_explanations_created_at_idx
  on public.finding_explanations(created_at desc);

alter table public.finding_explanations enable row level security;

drop policy if exists "finding_explanations_select_member" on public.finding_explanations;
create policy "finding_explanations_select_member"
on public.finding_explanations for select
using (
  exists (
    select 1
    from public.org_members m
    where m.org_id = finding_explanations.org_id
      and m.user_id = auth.uid()
  )
);

create or replace function public.insert_snapshot_v2(
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
  p_text_fingerprint text
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
    text_fingerprint
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
    p_text_fingerprint
  )
  returning id into v_snapshot_id;

  return v_snapshot_id;
end;
$$;

revoke all on function public.insert_snapshot_v2(uuid,uuid,uuid,text,text,text,bigint,int,text,text,text,text) from public;
grant execute on function public.insert_snapshot_v2(uuid,uuid,uuid,text,text,text,bigint,int,text,text,text,text) to authenticated;

create or replace function public.insert_finding_explanation(
  p_org_id uuid,
  p_finding_id uuid,
  p_summary text,
  p_diff_preview text,
  p_citations jsonb
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_explanation_id uuid;
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
    select 1 from public.findings f
    where f.id = p_finding_id and f.org_id = p_org_id
  ) then
    raise exception 'finding not found in org';
  end if;

  insert into public.finding_explanations (
    org_id,
    finding_id,
    summary,
    diff_preview,
    citations
  )
  values (
    p_org_id,
    p_finding_id,
    p_summary,
    p_diff_preview,
    coalesce(p_citations, '[]'::jsonb)
  )
  returning id into v_explanation_id;

  return v_explanation_id;
end;
$$;

revoke all on function public.insert_finding_explanation(uuid,uuid,text,text,jsonb) from public;
grant execute on function public.insert_finding_explanation(uuid,uuid,text,text,jsonb) to authenticated;

create or replace function public.set_source_fetch_metadata(
  p_source_id uuid,
  p_etag text,
  p_last_modified text,
  p_content_type text
)
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

  select s.org_id into v_org_id
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

  update public.sources
  set
    etag = nullif(p_etag, ''),
    last_modified = nullif(p_last_modified, ''),
    content_type = nullif(p_content_type, '')
  where id = p_source_id;
end;
$$;

revoke all on function public.set_source_fetch_metadata(uuid,text,text,text) from public;
grant execute on function public.set_source_fetch_metadata(uuid,text,text,text) to authenticated;
