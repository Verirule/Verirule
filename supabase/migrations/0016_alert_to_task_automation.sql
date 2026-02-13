create table if not exists public.alert_task_rules (
  org_id uuid primary key references public.orgs(id) on delete cascade,
  enabled boolean not null default true,
  auto_create_task_on_alert boolean not null default true,
  min_severity text not null default 'medium'
    check (min_severity in ('low', 'medium', 'high')),
  auto_link_suggested_controls boolean not null default true,
  auto_add_evidence_checklist boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

drop trigger if exists set_alert_task_rules_updated_at on public.alert_task_rules;
create trigger set_alert_task_rules_updated_at
before update on public.alert_task_rules
for each row execute function public.set_updated_at();

alter table public.alert_task_rules enable row level security;

drop policy if exists "alert_task_rules_select_member" on public.alert_task_rules;
create policy "alert_task_rules_select_member"
on public.alert_task_rules for select
using (
  exists (
    select 1 from public.org_members m
    where m.org_id = alert_task_rules.org_id
      and m.user_id = auth.uid()
  )
);

drop policy if exists "alert_task_rules_insert_member" on public.alert_task_rules;
create policy "alert_task_rules_insert_member"
on public.alert_task_rules for insert
with check (
  exists (
    select 1 from public.org_members m
    where m.org_id = alert_task_rules.org_id
      and m.user_id = auth.uid()
  )
);

drop policy if exists "alert_task_rules_update_member" on public.alert_task_rules;
create policy "alert_task_rules_update_member"
on public.alert_task_rules for update
using (
  exists (
    select 1 from public.org_members m
    where m.org_id = alert_task_rules.org_id
      and m.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1 from public.org_members m
    where m.org_id = alert_task_rules.org_id
      and m.user_id = auth.uid()
  )
);

alter table public.alerts
  add column if not exists task_id uuid;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'alerts_task_id_fkey'
      and conrelid = 'public.alerts'::regclass
  ) then
    alter table public.alerts
      add constraint alerts_task_id_fkey
      foreign key (task_id) references public.tasks(id) on delete set null;
  end if;
end;
$$;

create index if not exists alerts_org_task_id_idx
  on public.alerts(org_id, task_id)
  where task_id is not null;

create table if not exists public.task_controls (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.orgs(id) on delete cascade,
  task_id uuid not null references public.tasks(id) on delete cascade,
  control_id uuid not null references public.controls(id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (org_id, task_id, control_id)
);

create index if not exists task_controls_org_id_idx on public.task_controls(org_id);
create index if not exists task_controls_task_id_idx on public.task_controls(task_id);
create index if not exists task_controls_control_id_idx on public.task_controls(control_id);

alter table public.task_controls enable row level security;

drop policy if exists "task_controls_select_member" on public.task_controls;
create policy "task_controls_select_member"
on public.task_controls for select
using (
  exists (
    select 1 from public.org_members m
    where m.org_id = task_controls.org_id
      and m.user_id = auth.uid()
  )
);

drop policy if exists "task_controls_insert_member" on public.task_controls;
create policy "task_controls_insert_member"
on public.task_controls for insert
with check (
  exists (
    select 1 from public.org_members m
    where m.org_id = task_controls.org_id
      and m.user_id = auth.uid()
  )
);

drop policy if exists "task_controls_delete_member" on public.task_controls;
create policy "task_controls_delete_member"
on public.task_controls for delete
using (
  exists (
    select 1 from public.org_members m
    where m.org_id = task_controls.org_id
      and m.user_id = auth.uid()
  )
);

create or replace function public.ensure_alert_task_rules(p_org_id uuid)
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
      where m.org_id = p_org_id and m.user_id = v_user_id
    ) then
      raise exception 'not a member of org';
    end if;
  end if;

  insert into public.alert_task_rules(org_id)
  values (p_org_id)
  on conflict (org_id) do nothing;
end;
$$;

revoke all on function public.ensure_alert_task_rules(uuid) from public;
grant execute on function public.ensure_alert_task_rules(uuid) to authenticated;
grant execute on function public.ensure_alert_task_rules(uuid) to service_role;

create or replace function public.link_alert_task(
  p_org_id uuid,
  p_alert_id uuid,
  p_task_id uuid
)
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
      where m.org_id = p_org_id and m.user_id = v_user_id
    ) then
      raise exception 'not a member of org';
    end if;
  end if;

  if not exists (
    select 1
    from public.tasks t
    where t.id = p_task_id and t.org_id = p_org_id
  ) then
    raise exception 'task not found';
  end if;

  update public.alerts
  set task_id = p_task_id
  where id = p_alert_id
    and org_id = p_org_id;

  if not found then
    raise exception 'alert not found';
  end if;
end;
$$;

revoke all on function public.link_alert_task(uuid,uuid,uuid) from public;
grant execute on function public.link_alert_task(uuid,uuid,uuid) to authenticated;
grant execute on function public.link_alert_task(uuid,uuid,uuid) to service_role;
