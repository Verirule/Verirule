alter table public.sources
  add column if not exists cadence text not null default 'manual',
  add column if not exists next_run_at timestamptz,
  add column if not exists last_run_at timestamptz;

alter table public.sources drop constraint if exists sources_cadence_check;
alter table public.sources
  add constraint sources_cadence_check
  check (cadence in ('manual', 'hourly', 'daily', 'weekly'));

create index if not exists sources_next_run_at_idx
  on public.sources(next_run_at)
  where cadence <> 'manual' and is_enabled = true;

create or replace function public.schedule_next_run(p_source_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_org_id uuid;
  v_cadence text;
  v_now timestamptz := now();
  v_next_run_at timestamptz;
begin
  v_user_id := auth.uid();

  select s.org_id, s.cadence
  into v_org_id, v_cadence
  from public.sources s
  where s.id = p_source_id;

  if v_org_id is null then
    raise exception 'source not found';
  end if;

  if v_user_id is null then
    raise exception 'not authenticated';
  end if;

  if not exists (
    select 1 from public.org_members m
    where m.org_id = v_org_id and m.user_id = v_user_id
  ) then
    raise exception 'not a member of org';
  end if;

  v_next_run_at := case v_cadence
    when 'hourly' then v_now + interval '1 hour'
    when 'daily' then v_now + interval '1 day'
    when 'weekly' then v_now + interval '1 week'
    else null
  end;

  update public.sources
  set
    next_run_at = v_next_run_at,
    last_run_at = v_now
  where id = p_source_id;
end;
$$;

revoke all on function public.schedule_next_run(uuid) from public;
grant execute on function public.schedule_next_run(uuid) to authenticated;

create or replace function public.set_source_cadence(p_source_id uuid, p_cadence text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_org_id uuid;
begin
  if p_cadence not in ('manual', 'hourly', 'daily', 'weekly') then
    raise exception 'invalid cadence';
  end if;

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
    cadence = p_cadence,
    next_run_at = case when p_cadence = 'manual' then null else coalesce(next_run_at, now()) end
  where id = p_source_id;
end;
$$;

revoke all on function public.set_source_cadence(uuid,text) from public;
grant execute on function public.set_source_cadence(uuid,text) to authenticated;
