create or replace function public.create_org(p_name text)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_org_id uuid;
  v_user_id uuid;
  v_name text;
  v_lock_key bigint;
begin
  v_user_id := auth.uid();
  if v_user_id is null then
    raise exception 'not authenticated';
  end if;

  v_name := nullif(trim(p_name), '');
  if v_name is null then
    raise exception 'org name is required';
  end if;

  if char_length(v_name) < 2 or char_length(v_name) > 64 then
    raise exception 'org name must be between 2 and 64 characters';
  end if;

  v_lock_key := hashtext(v_user_id::text || ':' || lower(v_name))::bigint;
  perform pg_advisory_xact_lock(v_lock_key);

  select o.id
    into v_org_id
    from public.orgs o
    inner join public.org_members m
      on m.org_id = o.id
   where m.user_id = v_user_id
     and lower(trim(o.name)) = lower(v_name)
   order by o.created_at asc
   limit 1;

  if v_org_id is not null then
    return v_org_id;
  end if;

  insert into public.orgs (name)
  values (v_name)
  returning id into v_org_id;

  insert into public.org_members (org_id, user_id, role)
  values (v_org_id, v_user_id, 'owner')
  on conflict (org_id, user_id) do nothing;

  insert into public.alert_task_rules (org_id)
  values (v_org_id)
  on conflict (org_id) do nothing;

  return v_org_id;
end;
$$;

revoke all on function public.create_org(text) from public;
grant execute on function public.create_org(text) to authenticated;
