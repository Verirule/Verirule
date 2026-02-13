create table if not exists public.evidence_files (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.orgs(id) on delete cascade,
  task_id uuid not null references public.tasks(id) on delete cascade,
  filename text not null,
  storage_bucket text not null default 'evidence',
  storage_path text not null,
  content_type text,
  byte_size bigint,
  sha256 text,
  uploaded_by uuid,
  created_at timestamptz not null default now(),
  unique (org_id, storage_path)
);

create index if not exists evidence_files_org_id_idx on public.evidence_files(org_id);
create index if not exists evidence_files_task_id_idx on public.evidence_files(task_id);
create index if not exists evidence_files_created_at_idx on public.evidence_files(created_at desc);

alter table public.evidence_files enable row level security;

drop policy if exists "evidence_files_select_member" on public.evidence_files;
create policy "evidence_files_select_member"
on public.evidence_files for select
using (
  exists (
    select 1
    from public.org_members m
    where m.org_id = evidence_files.org_id
      and m.user_id = auth.uid()
  )
);

drop policy if exists "evidence_files_insert_member" on public.evidence_files;
create policy "evidence_files_insert_member"
on public.evidence_files for insert
with check (
  exists (
    select 1
    from public.org_members m
    where m.org_id = evidence_files.org_id
      and m.user_id = auth.uid()
  )
);

drop policy if exists "evidence_files_delete_member" on public.evidence_files;
create policy "evidence_files_delete_member"
on public.evidence_files for delete
using (
  exists (
    select 1
    from public.org_members m
    where m.org_id = evidence_files.org_id
      and m.user_id = auth.uid()
  )
);

create table if not exists public.audit_events (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.orgs(id) on delete cascade,
  actor_user_id uuid,
  actor_type text not null check (actor_type in ('user','system')),
  action text not null,
  entity_type text not null,
  entity_id uuid,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists audit_events_org_id_idx on public.audit_events(org_id);
create index if not exists audit_events_created_at_idx on public.audit_events(created_at desc);

do $$
begin
  if to_regclass('public.audit_log') is not null then
    insert into public.audit_events (
      id,
      org_id,
      actor_user_id,
      actor_type,
      action,
      entity_type,
      entity_id,
      metadata,
      created_at
    )
    select
      l.id,
      l.org_id,
      l.actor_user_id,
      case when l.actor_user_id is null then 'system' else 'user' end,
      l.action,
      l.entity_type,
      l.entity_id,
      coalesce(l.metadata, '{}'::jsonb),
      l.created_at
    from public.audit_log l
    on conflict (id) do nothing;
  end if;
end;
$$;

alter table public.audit_events enable row level security;

drop policy if exists "audit_events_select_member" on public.audit_events;
create policy "audit_events_select_member"
on public.audit_events for select
using (
  exists (
    select 1
    from public.org_members m
    where m.org_id = audit_events.org_id
      and m.user_id = auth.uid()
  )
);

drop policy if exists "audit_events_insert_member" on public.audit_events;
drop policy if exists "audit_events_insert_service_role" on public.audit_events;
create policy "audit_events_insert_service_role"
on public.audit_events for insert
to service_role
with check (true);

drop policy if exists "audit_events_update_member" on public.audit_events;
drop policy if exists "audit_events_delete_member" on public.audit_events;

revoke update, delete on table public.audit_events from authenticated;
revoke update, delete on table public.audit_events from anon;

create or replace function public.record_audit_event(
  p_org_id uuid,
  p_action text,
  p_entity_type text,
  p_entity_id uuid,
  p_metadata jsonb
)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_actor_type text;
begin
  v_user_id := auth.uid();

  if auth.role() = 'service_role' then
    v_actor_type := case when v_user_id is null then 'system' else 'user' end;
  else
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
    v_actor_type := 'user';
  end if;

  insert into public.audit_events(
    org_id,
    actor_user_id,
    actor_type,
    action,
    entity_type,
    entity_id,
    metadata
  )
  values (
    p_org_id,
    v_user_id,
    v_actor_type,
    p_action,
    p_entity_type,
    p_entity_id,
    coalesce(p_metadata, '{}'::jsonb)
  );
end;
$$;

revoke all on function public.record_audit_event(uuid,text,text,uuid,jsonb) from public;
grant execute on function public.record_audit_event(uuid,text,text,uuid,jsonb) to authenticated;
grant execute on function public.record_audit_event(uuid,text,text,uuid,jsonb) to service_role;

create or replace function public.append_audit(
  p_org_id uuid,
  p_action text,
  p_entity_type text,
  p_entity_id uuid,
  p_metadata jsonb
)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  perform public.record_audit_event(
    p_org_id,
    p_action,
    p_entity_type,
    p_entity_id,
    p_metadata
  );
end;
$$;

revoke all on function public.append_audit(uuid,text,text,uuid,jsonb) from public;
grant execute on function public.append_audit(uuid,text,text,uuid,jsonb) to authenticated;
grant execute on function public.append_audit(uuid,text,text,uuid,jsonb) to service_role;
