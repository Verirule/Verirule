create table if not exists public.org_sla_rules (
  org_id uuid primary key references public.orgs(id) on delete cascade,
  enabled boolean not null default true,
  due_hours_low int not null default 168,
  due_hours_medium int not null default 72,
  due_hours_high int not null default 24,
  due_soon_threshold_hours int not null default 12,
  overdue_remind_every_hours int not null default 24,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint org_sla_rules_due_hours_low_check check (due_hours_low between 1 and 24 * 365),
  constraint org_sla_rules_due_hours_medium_check check (due_hours_medium between 1 and 24 * 365),
  constraint org_sla_rules_due_hours_high_check check (due_hours_high between 1 and 24 * 365),
  constraint org_sla_rules_due_soon_threshold_hours_check check (due_soon_threshold_hours between 1 and 24 * 30),
  constraint org_sla_rules_overdue_remind_every_hours_check check (overdue_remind_every_hours between 1 and 24 * 30)
);

drop trigger if exists set_org_sla_rules_updated_at on public.org_sla_rules;
create trigger set_org_sla_rules_updated_at
before update on public.org_sla_rules
for each row execute function public.set_updated_at();

alter table public.org_sla_rules enable row level security;

drop policy if exists "org_sla_rules_select_member" on public.org_sla_rules;
create policy "org_sla_rules_select_member"
on public.org_sla_rules for select
using (
  exists (
    select 1
    from public.org_members m
    where m.org_id = org_sla_rules.org_id
      and m.user_id = auth.uid()
  )
);

drop policy if exists "org_sla_rules_insert_admin_owner" on public.org_sla_rules;
create policy "org_sla_rules_insert_admin_owner"
on public.org_sla_rules for insert
with check (
  exists (
    select 1
    from public.org_members m
    where m.org_id = org_sla_rules.org_id
      and m.user_id = auth.uid()
      and m.role in ('owner', 'admin')
  )
);

drop policy if exists "org_sla_rules_update_admin_owner" on public.org_sla_rules;
create policy "org_sla_rules_update_admin_owner"
on public.org_sla_rules for update
using (
  exists (
    select 1
    from public.org_members m
    where m.org_id = org_sla_rules.org_id
      and m.user_id = auth.uid()
      and m.role in ('owner', 'admin')
  )
)
with check (
  exists (
    select 1
    from public.org_members m
    where m.org_id = org_sla_rules.org_id
      and m.user_id = auth.uid()
      and m.role in ('owner', 'admin')
  )
);

alter table public.tasks
  add column if not exists due_at timestamptz,
  add column if not exists severity text,
  add column if not exists sla_state text;

alter table public.tasks
  alter column sla_state set default 'none';

update public.tasks
set sla_state = 'none'
where sla_state is null;

alter table public.tasks
  alter column sla_state set not null;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'tasks_sla_state_check'
      and conrelid = 'public.tasks'::regclass
  ) then
    alter table public.tasks
      add constraint tasks_sla_state_check
      check (sla_state in ('none', 'on_track', 'due_soon', 'overdue'));
  end if;
end;
$$;

create table if not exists public.task_escalations (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.orgs(id) on delete cascade,
  task_id uuid not null references public.tasks(id) on delete cascade,
  kind text not null check (kind in ('due_soon', 'overdue')),
  window_start timestamptz not null,
  created_at timestamptz not null default now(),
  notified_at timestamptz,
  channel text not null default 'email' check (channel in ('email', 'slack', 'both')),
  notification_job_id uuid references public.notification_jobs(id)
);

create index if not exists task_escalations_org_created_idx
  on public.task_escalations (org_id, created_at desc);

create index if not exists task_escalations_task_created_idx
  on public.task_escalations (task_id, created_at desc);

create unique index if not exists task_escalations_task_kind_window_uniq
  on public.task_escalations (task_id, kind, window_start);

alter table public.task_escalations enable row level security;

drop policy if exists "task_escalations_select_member" on public.task_escalations;
create policy "task_escalations_select_member"
on public.task_escalations for select
using (
  exists (
    select 1
    from public.org_members m
    where m.org_id = task_escalations.org_id
      and m.user_id = auth.uid()
  )
);

drop policy if exists "task_escalations_insert_service_role" on public.task_escalations;
create policy "task_escalations_insert_service_role"
on public.task_escalations for insert
to service_role
with check (true);

drop policy if exists "task_escalations_update_service_role" on public.task_escalations;
create policy "task_escalations_update_service_role"
on public.task_escalations for update
to service_role
using (true)
with check (true);

do $$
declare
  c record;
begin
  for c in
    select conname
    from pg_constraint
    where conrelid = 'public.notification_jobs'::regclass
      and contype = 'c'
      and pg_get_constraintdef(oid) ilike '%type%'
      and pg_get_constraintdef(oid) ilike '%digest%'
      and pg_get_constraintdef(oid) ilike '%immediate_alert%'
  loop
    execute format('alter table public.notification_jobs drop constraint %I', c.conname);
  end loop;

  if not exists (
    select 1
    from pg_constraint
    where conname = 'notification_jobs_type_check'
      and conrelid = 'public.notification_jobs'::regclass
  ) then
    alter table public.notification_jobs
      add constraint notification_jobs_type_check
      check (type in ('digest', 'immediate_alert', 'sla'));
  end if;
end;
$$;

do $$
declare
  c record;
begin
  for c in
    select conname
    from pg_constraint
    where conrelid = 'public.notification_events'::regclass
      and contype = 'c'
      and pg_get_constraintdef(oid) ilike '%type%'
      and pg_get_constraintdef(oid) ilike '%digest%'
      and pg_get_constraintdef(oid) ilike '%immediate_alert%'
  loop
    execute format('alter table public.notification_events drop constraint %I', c.conname);
  end loop;

  if not exists (
    select 1
    from pg_constraint
    where conname = 'notification_events_type_check'
      and conrelid = 'public.notification_events'::regclass
  ) then
    alter table public.notification_events
      add constraint notification_events_type_check
      check (type in ('digest', 'immediate_alert', 'sla'));
  end if;
end;
$$;

create or replace function public.ensure_org_sla_rules(p_org_id uuid)
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

  insert into public.org_sla_rules(org_id)
  values (p_org_id)
  on conflict (org_id) do nothing;
end;
$$;

revoke all on function public.ensure_org_sla_rules(uuid) from public;
grant execute on function public.ensure_org_sla_rules(uuid) to authenticated;
grant execute on function public.ensure_org_sla_rules(uuid) to service_role;

create or replace function public.compute_task_due_at(
  p_org_id uuid,
  p_severity text,
  p_created_at timestamptz
)
returns timestamptz
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_severity text;
  v_due_hours int;
  v_rules record;
  v_created_at timestamptz;
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

  perform public.ensure_org_sla_rules(p_org_id);

  select *
    into v_rules
  from public.org_sla_rules
  where org_id = p_org_id
  limit 1;

  v_created_at := coalesce(p_created_at, now());
  v_severity := lower(trim(coalesce(p_severity, 'medium')));

  if v_severity = 'high' then
    v_due_hours := coalesce(v_rules.due_hours_high, 24);
  elsif v_severity = 'low' then
    v_due_hours := coalesce(v_rules.due_hours_low, 168);
  else
    v_due_hours := coalesce(v_rules.due_hours_medium, 72);
  end if;

  return v_created_at + make_interval(hours => greatest(v_due_hours, 1));
end;
$$;

revoke all on function public.compute_task_due_at(uuid,text,timestamptz) from public;
grant execute on function public.compute_task_due_at(uuid,text,timestamptz) to authenticated;
grant execute on function public.compute_task_due_at(uuid,text,timestamptz) to service_role;

create or replace function public.set_task_due_at(
  p_task_id uuid,
  p_due_at timestamptz
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
  if p_due_at is null then
    raise exception 'due_at is required';
  end if;

  select t.org_id
    into v_org_id
  from public.tasks t
  where t.id = p_task_id
  limit 1;

  if v_org_id is null then
    raise exception 'task not found';
  end if;

  if auth.role() <> 'service_role' then
    v_user_id := auth.uid();
    if v_user_id is null then
      raise exception 'not authenticated';
    end if;

    if not exists (
      select 1
      from public.org_members m
      where m.org_id = v_org_id
        and m.user_id = v_user_id
        and m.role in ('owner', 'admin')
    ) then
      raise exception 'insufficient org role';
    end if;
  end if;

  update public.tasks
  set due_at = p_due_at
  where id = p_task_id;
end;
$$;

revoke all on function public.set_task_due_at(uuid,timestamptz) from public;
grant execute on function public.set_task_due_at(uuid,timestamptz) to authenticated;
grant execute on function public.set_task_due_at(uuid,timestamptz) to service_role;
