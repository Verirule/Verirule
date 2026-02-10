-- tasks: actionable remediation workflow
create table if not exists public.tasks (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.orgs(id) on delete cascade,
  title text not null,
  description text,
  status text not null check (status in ('open','in_progress','blocked','done')),
  assignee_user_id uuid,
  alert_id uuid references public.alerts(id) on delete set null,
  finding_id uuid references public.findings(id) on delete set null,
  due_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists tasks_org_id_idx on public.tasks(org_id);
create index if not exists tasks_alert_id_idx on public.tasks(alert_id);

-- task comments (collaboration)
create table if not exists public.task_comments (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.orgs(id) on delete cascade,
  task_id uuid not null references public.tasks(id) on delete cascade,
  author_user_id uuid,
  body text not null,
  created_at timestamptz not null default now()
);

create index if not exists task_comments_task_id_idx on public.task_comments(task_id);

-- task evidence (audit-ready proof)
create table if not exists public.task_evidence (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.orgs(id) on delete cascade,
  task_id uuid not null references public.tasks(id) on delete cascade,
  type text not null check (type in ('link','file','log')),
  ref text not null,
  created_at timestamptz not null default now()
);

create index if not exists task_evidence_task_id_idx on public.task_evidence(task_id);

-- RLS
alter table public.tasks enable row level security;
alter table public.task_comments enable row level security;
alter table public.task_evidence enable row level security;

-- Members can read everything in their org
drop policy if exists "tasks_select_member" on public.tasks;
create policy "tasks_select_member"
on public.tasks for select
using (
  exists (select 1 from public.org_members m where m.org_id = tasks.org_id and m.user_id = auth.uid())
);

drop policy if exists "task_comments_select_member" on public.task_comments;
create policy "task_comments_select_member"
on public.task_comments for select
using (
  exists (select 1 from public.org_members m where m.org_id = task_comments.org_id and m.user_id = auth.uid())
);

drop policy if exists "task_evidence_select_member" on public.task_evidence;
create policy "task_evidence_select_member"
on public.task_evidence for select
using (
  exists (select 1 from public.org_members m where m.org_id = task_evidence.org_id and m.user_id = auth.uid())
);

-- Update trigger for updated_at
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_tasks_updated_at on public.tasks;
create trigger trg_tasks_updated_at
before update on public.tasks
for each row execute function public.set_updated_at();

-- RPC helpers (writes)
-- create_task
create or replace function public.create_task(
  p_org_id uuid,
  p_title text,
  p_description text,
  p_alert_id uuid,
  p_finding_id uuid,
  p_due_at timestamptz
) returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_task_id uuid;
begin
  v_user_id := auth.uid();
  if v_user_id is null then raise exception 'not authenticated'; end if;

  if not exists (select 1 from public.org_members m where m.org_id=p_org_id and m.user_id=v_user_id) then
    raise exception 'not a member of org';
  end if;

  insert into public.tasks(org_id, title, description, status, assignee_user_id, alert_id, finding_id, due_at)
  values (p_org_id, p_title, p_description, 'open', v_user_id, p_alert_id, p_finding_id, p_due_at)
  returning id into v_task_id;

  return v_task_id;
end;
$$;

revoke all on function public.create_task(uuid,text,text,uuid,uuid,timestamptz) from public;
grant execute on function public.create_task(uuid,text,text,uuid,uuid,timestamptz) to authenticated;

-- set_task_status
create or replace function public.set_task_status(p_task_id uuid, p_status text)
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
  if v_user_id is null then raise exception 'not authenticated'; end if;

  select org_id into v_org_id from public.tasks where id = p_task_id;
  if v_org_id is null then raise exception 'task not found'; end if;

  if not exists (select 1 from public.org_members m where m.org_id=v_org_id and m.user_id=v_user_id) then
    raise exception 'not a member of org';
  end if;

  update public.tasks set status = p_status where id = p_task_id;
end;
$$;

revoke all on function public.set_task_status(uuid,text) from public;
grant execute on function public.set_task_status(uuid,text) to authenticated;

-- add_task_comment
create or replace function public.add_task_comment(p_task_id uuid, p_body text)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_org_id uuid;
  v_comment_id uuid;
begin
  v_user_id := auth.uid();
  if v_user_id is null then raise exception 'not authenticated'; end if;

  select org_id into v_org_id from public.tasks where id = p_task_id;
  if v_org_id is null then raise exception 'task not found'; end if;

  if not exists (select 1 from public.org_members m where m.org_id=v_org_id and m.user_id=v_user_id) then
    raise exception 'not a member of org';
  end if;

  insert into public.task_comments(org_id, task_id, author_user_id, body)
  values (v_org_id, p_task_id, v_user_id, p_body)
  returning id into v_comment_id;

  return v_comment_id;
end;
$$;

revoke all on function public.add_task_comment(uuid,text) from public;
grant execute on function public.add_task_comment(uuid,text) to authenticated;

-- add_task_evidence
create or replace function public.add_task_evidence(p_task_id uuid, p_type text, p_ref text)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_org_id uuid;
  v_evidence_id uuid;
begin
  v_user_id := auth.uid();
  if v_user_id is null then raise exception 'not authenticated'; end if;

  select org_id into v_org_id from public.tasks where id = p_task_id;
  if v_org_id is null then raise exception 'task not found'; end if;

  if not exists (select 1 from public.org_members m where m.org_id=v_org_id and m.user_id=v_user_id) then
    raise exception 'not a member of org';
  end if;

  insert into public.task_evidence(org_id, task_id, type, ref)
  values (v_org_id, p_task_id, p_type, p_ref)
  returning id into v_evidence_id;

  return v_evidence_id;
end;
$$;

revoke all on function public.add_task_evidence(uuid,text,text) from public;
grant execute on function public.add_task_evidence(uuid,text,text) to authenticated;

