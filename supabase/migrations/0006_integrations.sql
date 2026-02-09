create table if not exists public.integrations (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.orgs(id) on delete cascade,
  type text not null check (type in ('slack','jira','github')),
  status text not null check (status in ('enabled','disabled')),
  config jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (org_id, type)
);

create index if not exists integrations_org_id_idx on public.integrations(org_id);

alter table public.integrations enable row level security;

drop policy if exists "integrations_select_member" on public.integrations;
create policy "integrations_select_member"
on public.integrations for select
using (
  exists (
    select 1 from public.org_members m
    where m.org_id = integrations.org_id
      and m.user_id = auth.uid()
  )
);

create or replace function public.upsert_integration(
  p_org_id uuid,
  p_type text,
  p_status text,
  p_config jsonb
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_integration_id uuid;
begin
  if p_type not in ('slack','jira','github') then
    raise exception 'invalid integration type';
  end if;
  if p_status not in ('enabled','disabled') then
    raise exception 'invalid integration status';
  end if;

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

  insert into public.integrations (org_id, type, status, config)
  values (p_org_id, p_type, p_status, coalesce(p_config, '{}'::jsonb))
  on conflict (org_id, type)
  do update set
    status = excluded.status,
    config = excluded.config,
    updated_at = now()
  returning id into v_integration_id;

  perform public.append_audit(
    p_org_id,
    'integration_upserted',
    'integration',
    v_integration_id,
    jsonb_build_object('type', p_type, 'status', p_status)
  );

  return v_integration_id;
end;
$$;

revoke all on function public.upsert_integration(uuid,text,text,jsonb) from public;
grant execute on function public.upsert_integration(uuid,text,text,jsonb) to authenticated;

create unique index if not exists alerts_finding_id_uq on public.alerts(finding_id);

create or replace function public.upsert_alert_for_finding(p_org_id uuid, p_finding_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_alert_id uuid;
  v_existing_id uuid;
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

  select a.id into v_existing_id
  from public.alerts a
  where a.finding_id = p_finding_id;

  if v_existing_id is not null then
    return jsonb_build_object('id', v_existing_id, 'created', false);
  end if;

  insert into public.alerts (org_id, finding_id, status)
  values (p_org_id, p_finding_id, 'open')
  returning id into v_alert_id;

  perform public.append_audit(
    p_org_id,
    'alert_created',
    'alert',
    v_alert_id,
    jsonb_build_object('finding_id', p_finding_id)
  );

  return jsonb_build_object('id', v_alert_id, 'created', true);
end;
$$;

revoke all on function public.upsert_alert_for_finding(uuid,uuid) from public;
grant execute on function public.upsert_alert_for_finding(uuid,uuid) to authenticated;
