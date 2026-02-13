create table if not exists public.org_readiness_snapshots (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.orgs(id) on delete cascade,
  computed_at timestamptz not null default now(),
  score integer not null check (score between 0 and 100),
  controls_total integer not null,
  controls_with_evidence integer not null,
  evidence_items_total integer not null,
  evidence_items_done integer not null,
  open_alerts_high integer not null,
  open_tasks integer not null,
  overdue_tasks integer not null,
  metadata jsonb not null default '{}'::jsonb
);

create index if not exists org_readiness_snapshots_org_id_computed_at_idx
  on public.org_readiness_snapshots(org_id, computed_at desc);

alter table public.org_readiness_snapshots enable row level security;

drop policy if exists "org_readiness_snapshots_select_member" on public.org_readiness_snapshots;
create policy "org_readiness_snapshots_select_member"
on public.org_readiness_snapshots for select
using (
  exists (
    select 1
    from public.org_members m
    where m.org_id = org_readiness_snapshots.org_id
      and m.user_id = auth.uid()
  )
);

drop policy if exists "org_readiness_snapshots_insert_service_role" on public.org_readiness_snapshots;
create policy "org_readiness_snapshots_insert_service_role"
on public.org_readiness_snapshots for insert
to service_role
with check (true);

revoke update, delete on table public.org_readiness_snapshots from authenticated;
revoke update, delete on table public.org_readiness_snapshots from anon;

create or replace function public.compute_org_readiness(p_org_id uuid)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_snapshot_id uuid;
  v_controls_total int := 0;
  v_controls_with_evidence int := 0;
  v_evidence_items_total int := 0;
  v_evidence_items_done int := 0;
  v_open_alerts_high int := 0;
  v_open_tasks int := 0;
  v_overdue_tasks int := 0;
  v_findings_total int := 0;
  v_alerts_total int := 0;
  v_linked_findings_count int := 0;
  v_linked_alerts_count int := 0;
  v_open_alerts_total int := 0;
  v_control_coverage_pct int := 0;
  v_evidence_completion_pct int := 0;
  v_findings_linked_pct int := 100;
  v_alerts_linked_pct int := 100;
  v_linkage_pct int := 100;
  v_tasks_health_pct int := 100;
  v_alerts_health_pct int := 100;
  v_score int := 0;
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

  with required_per_control as (
    select
      oc.control_id,
      count(cei.id)::int as required_count
    from public.org_controls oc
    left join public.control_evidence_items cei
      on cei.control_id = oc.control_id
     and cei.required is true
    where oc.org_id = p_org_id
    group by oc.control_id
  ),
  evidence_controls as (
    select distinct tc.control_id
    from public.task_controls tc
    join public.tasks t
      on t.id = tc.task_id
     and t.org_id = p_org_id
    where tc.org_id = p_org_id
      and (
        exists (
          select 1
          from public.task_evidence te
          where te.org_id = p_org_id
            and te.task_id = t.id
            and coalesce(te.ref, '') !~* '^\s*\[pending\]'
        )
        or exists (
          select 1
          from public.evidence_files ef
          where ef.org_id = p_org_id
            and ef.task_id = t.id
        )
      )
  )
  select
    count(r.control_id)::int,
    coalesce(sum(r.required_count), 0)::int,
    count(*) filter (where ec.control_id is not null)::int,
    coalesce(sum(case when ec.control_id is not null then r.required_count else 0 end), 0)::int
  into
    v_controls_total,
    v_evidence_items_total,
    v_controls_with_evidence,
    v_evidence_items_done
  from required_per_control r
  left join evidence_controls ec
    on ec.control_id = r.control_id;

  select count(*)::int
  into v_open_tasks
  from public.tasks t
  where t.org_id = p_org_id
    and t.status <> 'done';

  select count(*)::int
  into v_overdue_tasks
  from public.tasks t
  where t.org_id = p_org_id
    and t.status <> 'done'
    and t.due_at is not null
    and t.due_at < now();

  select count(*)::int
  into v_open_alerts_high
  from public.alerts a
  join public.findings f
    on f.id = a.finding_id
   and f.org_id = p_org_id
  where a.org_id = p_org_id
    and a.status = 'open'
    and f.severity in ('high', 'critical');

  select count(*)::int
  into v_open_alerts_total
  from public.alerts a
  where a.org_id = p_org_id
    and a.status = 'open';

  select count(*)::int
  into v_findings_total
  from public.findings f
  where f.org_id = p_org_id;

  select count(*)::int
  into v_alerts_total
  from public.alerts a
  where a.org_id = p_org_id;

  select count(distinct fc.finding_id)::int
  into v_linked_findings_count
  from public.finding_controls fc
  where fc.org_id = p_org_id;

  select count(distinct a.id)::int
  into v_linked_alerts_count
  from public.alerts a
  join public.finding_controls fc
    on fc.finding_id = a.finding_id
   and fc.org_id = p_org_id
  where a.org_id = p_org_id;

  v_control_coverage_pct := case
    when v_controls_total > 0 then round((100.0 * v_controls_with_evidence) / v_controls_total)::int
    else 0
  end;

  v_evidence_completion_pct := case
    when v_evidence_items_total > 0 then round((100.0 * v_evidence_items_done) / v_evidence_items_total)::int
    else 0
  end;

  v_findings_linked_pct := case
    when v_findings_total > 0 then round((100.0 * v_linked_findings_count) / v_findings_total)::int
    else 100
  end;

  v_alerts_linked_pct := case
    when v_alerts_total > 0 then round((100.0 * v_linked_alerts_count) / v_alerts_total)::int
    else 100
  end;

  v_linkage_pct := round((v_findings_linked_pct + v_alerts_linked_pct) / 2.0)::int;
  v_tasks_health_pct := greatest(0, 100 - least(100, v_open_tasks * 4 + v_overdue_tasks * 12));
  v_alerts_health_pct := greatest(0, 100 - least(100, v_open_alerts_high * 20 + v_open_alerts_total * 3));

  v_score := round(
    (0.30 * v_control_coverage_pct) +
    (0.30 * v_evidence_completion_pct) +
    (0.15 * v_tasks_health_pct) +
    (0.15 * v_alerts_health_pct) +
    (0.10 * v_linkage_pct)
  )::int;
  v_score := greatest(0, least(100, v_score));

  insert into public.org_readiness_snapshots (
    org_id,
    score,
    controls_total,
    controls_with_evidence,
    evidence_items_total,
    evidence_items_done,
    open_alerts_high,
    open_tasks,
    overdue_tasks,
    metadata
  )
  values (
    p_org_id,
    v_score,
    v_controls_total,
    v_controls_with_evidence,
    v_evidence_items_total,
    v_evidence_items_done,
    v_open_alerts_high,
    v_open_tasks,
    v_overdue_tasks,
    jsonb_build_object(
      'control_coverage_pct', v_control_coverage_pct,
      'evidence_completion_pct', v_evidence_completion_pct,
      'tasks_health_pct', v_tasks_health_pct,
      'alerts_health_pct', v_alerts_health_pct,
      'linkage_pct', v_linkage_pct,
      'linked_findings_count', v_linked_findings_count,
      'linked_alerts_count', v_linked_alerts_count,
      'findings_total', v_findings_total,
      'alerts_total', v_alerts_total,
      'open_alerts_total', v_open_alerts_total
    )
  )
  returning id into v_snapshot_id;

  return v_snapshot_id;
end;
$$;

revoke all on function public.compute_org_readiness(uuid) from public;
grant execute on function public.compute_org_readiness(uuid) to authenticated;
grant execute on function public.compute_org_readiness(uuid) to service_role;
