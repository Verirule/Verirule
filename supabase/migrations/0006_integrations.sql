create table if not exists public.integrations (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.orgs(id) on delete cascade,
  type text not null check (type in ('slack','jira')),
  status text not null check (status in ('connected','disabled')),
  config jsonb not null default '{}'::jsonb,
  secret_ciphertext text, -- encrypted blob, never plaintext
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
  exists (select 1 from public.org_members m where m.org_id = integrations.org_id and m.user_id = auth.uid())
);

-- updated_at trigger reuse
drop trigger if exists trg_integrations_updated_at on public.integrations;
create trigger trg_integrations_updated_at
before update on public.integrations
for each row execute function public.set_updated_at();

-- RPC: upsert integration (config + ciphertext). Only members.
create or replace function public.upsert_integration(
  p_org_id uuid,
  p_type text,
  p_status text,
  p_config jsonb,
  p_secret_ciphertext text
) returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_id uuid;
begin
  v_user_id := auth.uid();
  if v_user_id is null then raise exception 'not authenticated'; end if;

  if not exists (select 1 from public.org_members m where m.org_id=p_org_id and m.user_id=v_user_id) then
    raise exception 'not a member of org';
  end if;

  insert into public.integrations(org_id, type, status, config, secret_ciphertext)
  values (p_org_id, p_type, p_status, coalesce(p_config,'{}'::jsonb), p_secret_ciphertext)
  on conflict (org_id, type)
  do update set status=excluded.status, config=excluded.config, secret_ciphertext=excluded.secret_ciphertext, updated_at=now()
  returning id into v_id;

  return v_id;
end;
$$;

revoke all on function public.upsert_integration(uuid,text,text,jsonb,text) from public;
grant execute on function public.upsert_integration(uuid,text,text,jsonb,text) to authenticated;

-- RPC: disable integration
create or replace function public.disable_integration(p_org_id uuid, p_type text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare v_user_id uuid;
begin
  v_user_id := auth.uid();
  if v_user_id is null then raise exception 'not authenticated'; end if;

  if not exists (select 1 from public.org_members m where m.org_id=p_org_id and m.user_id=v_user_id) then
    raise exception 'not a member of org';
  end if;

  update public.integrations set status='disabled', updated_at=now()
  where org_id=p_org_id and type=p_type;
end;
$$;

revoke all on function public.disable_integration(uuid,text) from public;
grant execute on function public.disable_integration(uuid,text) to authenticated;
