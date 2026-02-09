create table if not exists public.tasks (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.orgs(id) on delete cascade,
  title text not null,
  status text not null check (status in ('open','in_progress','resolved','blocked')),
  assignee_user_id uuid,
  alert_id uuid references public.alerts(id) on delete set null,
  finding_id uuid references public.findings(id) on delete set null,
  due_at timestamptz,
  created_by_user_id uuid not null,
  created_at timestamptz not null default now()
);

create index if not exists tasks_org_id_idx on public.tasks(org_id);
create index if not exists tasks_alert_id_idx on public.tasks(alert_id);
create index if not exists tasks_finding_id_idx on public.tasks(finding_id);
create index if not exists tasks_assignee_user_id_idx on public.tasks(assignee_user_id);

alter table public.tasks enable row level security;

drop policy if exists "tasks_select_member" on public.tasks;
create policy "tasks_select_member"
on public.tasks for select
using (
  exists (
    select 1 from public.org_members m
    where m.org_id = tasks.org_id
      and m.user_id = auth.uid()
  )
);

create table if not exists public.task_evidence (
  id uuid primary key default gen_random_uuid(),
  task_id uuid not null references public.tasks(id) on delete cascade,
  type text not null check (type in ('link','file','log')),
  ref text not null,
  created_by_user_id uuid not null,
  created_at timestamptz not null default now()
);

create index if not exists task_evidence_task_id_idx on public.task_evidence(task_id);

alter table public.task_evidence enable row level security;

drop policy if exists "task_evidence_select_member" on public.task_evidence;
create policy "task_evidence_select_member"
on public.task_evidence for select
using (
  exists (
    select 1
    from public.tasks t
    join public.org_members m on m.org_id = t.org_id
    where t.id = task_evidence.task_id
      and m.user_id = auth.uid()
  )
);

create table if not exists public.task_comments (
  id uuid primary key default gen_random_uuid(),
  task_id uuid not null references public.tasks(id) on delete cascade,
  author_user_id uuid not null,
  body text not null,
  created_at timestamptz not null default now()
);

create index if not exists task_comments_task_id_idx on public.task_comments(task_id);

alter table public.task_comments enable row level security;

drop policy if exists "task_comments_select_member" on public.task_comments;
create policy "task_comments_select_member"
on public.task_comments for select
using (
  exists (
    select 1
    from public.tasks t
    join public.org_members m on m.org_id = t.org_id
    where t.id = task_comments.task_id
      and m.user_id = auth.uid()
  )
);

create or replace function public.create_task(
  p_org_id uuid,
  p_title text,
  p_alert_id uuid,
  p_finding_id uuid,
  p_due_at timestamptz
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_task_id uuid;
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

  if p_alert_id is not null and not exists (
    select 1 from public.alerts a
    where a.id = p_alert_id and a.org_id = p_org_id
  ) then
    raise exception 'alert not found in org';
  end if;

  if p_finding_id is not null and not exists (
    select 1 from public.findings f
    where f.id = p_finding_id and f.org_id = p_org_id
  ) then
    raise exception 'finding not found in org';
  end if;

  insert into public.tasks (
    org_id,
    title,
    status,
    assignee_user_id,
    alert_id,
    finding_id,
    due_at,
    created_by_user_id
  )
  values (
    p_org_id,
    p_title,
    'open',
    null,
    p_alert_id,
    p_finding_id,
    p_due_at,
    v_user_id
  )
  returning id into v_task_id;

  perform public.append_audit(
    p_org_id,
    'task_created',
    'task',
    v_task_id,
    jsonb_build_object(
      'title', p_title,
      'alert_id', p_alert_id,
      'finding_id', p_finding_id
    )
  );

  return v_task_id;
end;
$$;

revoke all on function public.create_task(uuid,text,uuid,uuid,timestamptz) from public;
grant execute on function public.create_task(uuid,text,uuid,uuid,timestamptz) to authenticated;

create or replace function public.assign_task(p_task_id uuid, p_user_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v_actor_user_id uuid;
  v_org_id uuid;
begin
  v_actor_user_id := auth.uid();
  if v_actor_user_id is null then
    raise exception 'not authenticated';
  end if;

  select t.org_id into v_org_id
  from public.tasks t
  where t.id = p_task_id;

  if v_org_id is null then
    raise exception 'task not found';
  end if;

  if not exists (
    select 1 from public.org_members m
    where m.org_id = v_org_id and m.user_id = v_actor_user_id
  ) then
    raise exception 'not a member of org';
  end if;

  if not exists (
    select 1 from public.org_members m
    where m.org_id = v_org_id and m.user_id = p_user_id
  ) then
    raise exception 'assignee must be org member';
  end if;

  update public.tasks
  set assignee_user_id = p_user_id
  where id = p_task_id;

  perform public.append_audit(
    v_org_id,
    'task_assigned',
    'task',
    p_task_id,
    jsonb_build_object('assignee_user_id', p_user_id)
  );
end;
$$;

revoke all on function public.assign_task(uuid,uuid) from public;
grant execute on function public.assign_task(uuid,uuid) to authenticated;

create or replace function public.set_task_status(p_task_id uuid, p_status text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v_actor_user_id uuid;
  v_org_id uuid;
begin
  if p_status not in ('open','in_progress','resolved','blocked') then
    raise exception 'invalid task status';
  end if;

  v_actor_user_id := auth.uid();
  if v_actor_user_id is null then
    raise exception 'not authenticated';
  end if;

  select t.org_id into v_org_id
  from public.tasks t
  where t.id = p_task_id;

  if v_org_id is null then
    raise exception 'task not found';
  end if;

  if not exists (
    select 1 from public.org_members m
    where m.org_id = v_org_id and m.user_id = v_actor_user_id
  ) then
    raise exception 'not a member of org';
  end if;

  update public.tasks
  set status = p_status
  where id = p_task_id;

  perform public.append_audit(
    v_org_id,
    'task_status_changed',
    'task',
    p_task_id,
    jsonb_build_object('status', p_status)
  );
end;
$$;

revoke all on function public.set_task_status(uuid,text) from public;
grant execute on function public.set_task_status(uuid,text) to authenticated;

create or replace function public.add_task_comment(p_task_id uuid, p_body text)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_author_user_id uuid;
  v_org_id uuid;
  v_comment_id uuid;
begin
  v_author_user_id := auth.uid();
  if v_author_user_id is null then
    raise exception 'not authenticated';
  end if;

  select t.org_id into v_org_id
  from public.tasks t
  where t.id = p_task_id;

  if v_org_id is null then
    raise exception 'task not found';
  end if;

  if not exists (
    select 1 from public.org_members m
    where m.org_id = v_org_id and m.user_id = v_author_user_id
  ) then
    raise exception 'not a member of org';
  end if;

  insert into public.task_comments (task_id, author_user_id, body)
  values (p_task_id, v_author_user_id, p_body)
  returning id into v_comment_id;

  perform public.append_audit(
    v_org_id,
    'task_comment_added',
    'task',
    p_task_id,
    jsonb_build_object('comment_id', v_comment_id)
  );

  return v_comment_id;
end;
$$;

revoke all on function public.add_task_comment(uuid,text) from public;
grant execute on function public.add_task_comment(uuid,text) to authenticated;

create or replace function public.add_task_evidence(p_task_id uuid, p_type text, p_ref text)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_actor_user_id uuid;
  v_org_id uuid;
  v_evidence_id uuid;
begin
  if p_type not in ('link','file','log') then
    raise exception 'invalid evidence type';
  end if;

  v_actor_user_id := auth.uid();
  if v_actor_user_id is null then
    raise exception 'not authenticated';
  end if;

  select t.org_id into v_org_id
  from public.tasks t
  where t.id = p_task_id;

  if v_org_id is null then
    raise exception 'task not found';
  end if;

  if not exists (
    select 1 from public.org_members m
    where m.org_id = v_org_id and m.user_id = v_actor_user_id
  ) then
    raise exception 'not a member of org';
  end if;

  insert into public.task_evidence (task_id, type, ref, created_by_user_id)
  values (p_task_id, p_type, p_ref, v_actor_user_id)
  returning id into v_evidence_id;

  perform public.append_audit(
    v_org_id,
    'task_evidence_added',
    'task',
    p_task_id,
    jsonb_build_object('evidence_id', v_evidence_id, 'type', p_type)
  );

  return v_evidence_id;
end;
$$;

revoke all on function public.add_task_evidence(uuid,text,text) from public;
grant execute on function public.add_task_evidence(uuid,text,text) to authenticated;
