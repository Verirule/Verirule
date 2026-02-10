-- monitor_runs: one per scan execution
create table if not exists public.monitor_runs (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.orgs(id) on delete cascade,
  source_id uuid not null references public.sources(id) on delete cascade,
  status text not null check (status in ('queued','running','succeeded','failed')),
  started_at timestamptz,
  finished_at timestamptz,
  error text,
  created_at timestamptz not null default now()
);

create index if not exists monitor_runs_org_id_idx on public.monitor_runs(org_id);
create index if not exists monitor_runs_source_id_idx on public.monitor_runs(source_id);

alter table public.monitor_runs enable row level security;

drop policy if exists "monitor_runs_select_member" on public.monitor_runs;
create policy "monitor_runs_select_member"
on public.monitor_runs for select
using (
  exists (
    select 1 from public.org_members m
    where m.org_id = monitor_runs.org_id
      and m.user_id = auth.uid()
  )
);

-- snapshots: source content observed during a run
create table if not exists public.snapshots (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.orgs(id) on delete cascade,
  source_id uuid not null references public.sources(id) on delete cascade,
  run_id uuid not null references public.monitor_runs(id) on delete cascade,
  fetched_url text not null,
  content_hash text not null,
  content_type text,
  content_len bigint not null,
  fetched_at timestamptz not null default now()
);

create index if not exists snapshots_org_id_idx on public.snapshots(org_id);
create index if not exists snapshots_source_id_idx on public.snapshots(source_id);
create index if not exists snapshots_run_id_idx on public.snapshots(run_id);
create index if not exists snapshots_source_fetched_at_idx on public.snapshots(source_id, fetched_at desc);

alter table public.snapshots enable row level security;

drop policy if exists "snapshots_select_member" on public.snapshots;
create policy "snapshots_select_member"
on public.snapshots for select
using (
  exists (
    select 1 from public.org_members m
    where m.org_id = snapshots.org_id
      and m.user_id = auth.uid()
  )
);

-- findings: normalized "changes"
create table if not exists public.findings (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.orgs(id) on delete cascade,
  source_id uuid not null references public.sources(id) on delete cascade,
  run_id uuid not null references public.monitor_runs(id) on delete cascade,
  title text not null,
  summary text not null,
  severity text not null check (severity in ('low','medium','high','critical')),
  detected_at timestamptz not null default now(),
  fingerprint text not null,
  raw_url text,
  raw_hash text,
  unique (org_id, fingerprint)
);

create index if not exists findings_org_id_idx on public.findings(org_id);
create index if not exists findings_source_id_idx on public.findings(source_id);

alter table public.findings enable row level security;

drop policy if exists "findings_select_member" on public.findings;
create policy "findings_select_member"
on public.findings for select
using (
  exists (
    select 1 from public.org_members m
    where m.org_id = findings.org_id
      and m.user_id = auth.uid()
  )
);

-- alerts: routed notifications
create table if not exists public.alerts (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.orgs(id) on delete cascade,
  finding_id uuid not null references public.findings(id) on delete cascade,
  status text not null check (status in ('open','acknowledged','resolved')),
  owner_user_id uuid,
  created_at timestamptz not null default now(),
  resolved_at timestamptz
);

create index if not exists alerts_org_id_idx on public.alerts(org_id);

alter table public.alerts enable row level security;

drop policy if exists "alerts_select_member" on public.alerts;
create policy "alerts_select_member"
on public.alerts for select
using (
  exists (
    select 1 from public.org_members m
    where m.org_id = alerts.org_id
      and m.user_id = auth.uid()
  )
);

-- audit_log: immutable actions
create table if not exists public.audit_log (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.orgs(id) on delete cascade,
  actor_user_id uuid,
  action text not null,
  entity_type text not null,
  entity_id uuid,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists audit_log_org_id_idx on public.audit_log(org_id);

alter table public.audit_log enable row level security;

drop policy if exists "audit_log_select_member" on public.audit_log;
create policy "audit_log_select_member"
on public.audit_log for select
using (
  exists (
    select 1 from public.org_members m
    where m.org_id = audit_log.org_id
      and m.user_id = auth.uid()
  )
);

-- RPC: insert audit event (server-side)
create or replace function public.append_audit(p_org_id uuid, p_action text, p_entity_type text, p_entity_id uuid, p_metadata jsonb)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare v_user_id uuid;
begin
  v_user_id := auth.uid();
  if v_user_id is null then raise exception 'not authenticated'; end if;

  if not exists (select 1 from public.org_members m where m.org_id=p_org_id and m.user_id=v_user_id) then
    raise exception 'not a member of org';
  end if;

  insert into public.audit_log(org_id, actor_user_id, action, entity_type, entity_id, metadata)
  values (p_org_id, v_user_id, p_action, p_entity_type, p_entity_id, coalesce(p_metadata,'{}'::jsonb));
end;
$$;

revoke all on function public.append_audit(uuid,text,text,uuid,jsonb) from public;
grant execute on function public.append_audit(uuid,text,text,uuid,jsonb) to authenticated;

-- RPC: update monitor run state from worker
create or replace function public.set_monitor_run_state(
  p_run_id uuid,
  p_status text,
  p_error text default null
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
  if p_status not in ('running', 'succeeded', 'failed') then
    raise exception 'invalid monitor run status';
  end if;

  v_user_id := auth.uid();
  if v_user_id is null then
    raise exception 'not authenticated';
  end if;

  select r.org_id into v_org_id
  from public.monitor_runs r
  where r.id = p_run_id;

  if v_org_id is null then
    raise exception 'monitor run not found';
  end if;

  if not exists (
    select 1 from public.org_members m
    where m.org_id = v_org_id and m.user_id = v_user_id
  ) then
    raise exception 'not a member of org';
  end if;

  update public.monitor_runs
  set
    status = p_status,
    started_at = case
      when p_status = 'running' and started_at is null then now()
      else started_at
    end,
    finished_at = case
      when p_status in ('succeeded', 'failed') then now()
      else null
    end,
    error = case
      when p_status = 'failed' then p_error
      else null
    end
  where id = p_run_id;
end;
$$;

revoke all on function public.set_monitor_run_state(uuid,text,text) from public;
grant execute on function public.set_monitor_run_state(uuid,text,text) to authenticated;

-- RPC: insert snapshot from worker
create or replace function public.insert_snapshot(
  p_org_id uuid,
  p_source_id uuid,
  p_run_id uuid,
  p_fetched_url text,
  p_content_hash text,
  p_content_type text,
  p_content_len bigint
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
    content_len
  )
  values (
    p_org_id,
    p_source_id,
    p_run_id,
    p_fetched_url,
    p_content_hash,
    p_content_type,
    p_content_len
  )
  returning id into v_snapshot_id;

  return v_snapshot_id;
end;
$$;

revoke all on function public.insert_snapshot(uuid,uuid,uuid,text,text,text,bigint) from public;
grant execute on function public.insert_snapshot(uuid,uuid,uuid,text,text,text,bigint) to authenticated;

-- RPC: queue a monitor run
create or replace function public.create_monitor_run(p_org_id uuid, p_source_id uuid)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_run_id uuid;
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
    select 1 from public.sources s
    where s.id = p_source_id and s.org_id = p_org_id
  ) then
    raise exception 'source not found in org';
  end if;

  insert into public.monitor_runs (org_id, source_id, status)
  values (p_org_id, p_source_id, 'queued')
  returning id into v_run_id;

  return v_run_id;
end;
$$;

revoke all on function public.create_monitor_run(uuid,uuid) from public;
grant execute on function public.create_monitor_run(uuid,uuid) to authenticated;

-- RPC: upsert a finding from monitoring pipeline
create or replace function public.upsert_finding(
  p_org_id uuid,
  p_source_id uuid,
  p_run_id uuid,
  p_title text,
  p_summary text,
  p_severity text,
  p_fingerprint text,
  p_raw_url text,
  p_raw_hash text
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_finding_id uuid;
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

  insert into public.findings (
    org_id,
    source_id,
    run_id,
    title,
    summary,
    severity,
    fingerprint,
    raw_url,
    raw_hash
  )
  values (
    p_org_id,
    p_source_id,
    p_run_id,
    p_title,
    p_summary,
    p_severity,
    p_fingerprint,
    p_raw_url,
    p_raw_hash
  )
  on conflict (org_id, fingerprint)
  do update set
    source_id = excluded.source_id,
    run_id = excluded.run_id,
    title = excluded.title,
    summary = excluded.summary,
    severity = excluded.severity,
    detected_at = now(),
    raw_url = excluded.raw_url,
    raw_hash = excluded.raw_hash
  returning id into v_finding_id;

  return v_finding_id;
end;
$$;

revoke all on function public.upsert_finding(uuid,uuid,uuid,text,text,text,text,text,text) from public;
grant execute on function public.upsert_finding(uuid,uuid,uuid,text,text,text,text,text,text) to authenticated;

-- RPC: update alert state
create or replace function public.set_alert_status(p_alert_id uuid, p_status text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_org_id uuid;
begin
  if p_status not in ('acknowledged', 'resolved') then
    raise exception 'invalid alert status';
  end if;

  v_user_id := auth.uid();
  if v_user_id is null then
    raise exception 'not authenticated';
  end if;

  select a.org_id into v_org_id
  from public.alerts a
  where a.id = p_alert_id;

  if v_org_id is null then
    raise exception 'alert not found';
  end if;

  if not exists (
    select 1 from public.org_members m
    where m.org_id = v_org_id and m.user_id = v_user_id
  ) then
    raise exception 'not a member of org';
  end if;

  update public.alerts
  set
    status = p_status,
    owner_user_id = case when p_status = 'acknowledged' then v_user_id else owner_user_id end,
    resolved_at = case when p_status = 'resolved' then now() else null end
  where id = p_alert_id;
end;
$$;

revoke all on function public.set_alert_status(uuid,text) from public;
grant execute on function public.set_alert_status(uuid,text) to authenticated;
