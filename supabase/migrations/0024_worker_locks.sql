create table if not exists public.worker_locks (
  key text primary key,
  holder text not null,
  locked_until timestamptz not null,
  updated_at timestamptz not null default now()
);

alter table public.worker_locks enable row level security;

drop policy if exists "worker_locks_service_role_all" on public.worker_locks;
create policy "worker_locks_service_role_all"
on public.worker_locks
for all
to service_role
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

create or replace function public.acquire_worker_lock(
  p_key text,
  p_holder text,
  p_ttl_seconds int
)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
declare
  v_ttl interval;
  v_key text;
  v_holder text;
  v_row_count int := 0;
begin
  if auth.role() <> 'service_role' then
    raise exception 'forbidden';
  end if;

  v_key := trim(coalesce(p_key, ''));
  v_holder := trim(coalesce(p_holder, ''));
  if v_key = '' or v_holder = '' then
    return false;
  end if;

  v_ttl := make_interval(secs => greatest(1, coalesce(p_ttl_seconds, 120)));

  insert into public.worker_locks as wl (key, holder, locked_until, updated_at)
  values (v_key, v_holder, now() + v_ttl, now())
  on conflict (key) do update
    set holder = excluded.holder,
        locked_until = excluded.locked_until,
        updated_at = now()
    where wl.locked_until < now();

  get diagnostics v_row_count = row_count;
  return v_row_count > 0;
end;
$$;

revoke all on function public.acquire_worker_lock(text, text, int) from public;
grant execute on function public.acquire_worker_lock(text, text, int) to service_role;
