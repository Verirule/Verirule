create table if not exists public.audit_exports (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.orgs(id) on delete cascade,
  requested_by_user_id uuid,
  format text not null check (format in ('pdf','csv')),
  scope jsonb not null default '{}'::jsonb, -- { from, to, include: [...] }
  status text not null check (status in ('queued','running','succeeded','failed')) default 'queued',
  file_path text,         -- storage path in exports bucket
  file_sha256 text,
  error_text text,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

create index if not exists audit_exports_org_id_idx on public.audit_exports(org_id);
create index if not exists audit_exports_created_at_idx on public.audit_exports(created_at);

alter table public.audit_exports enable row level security;

drop policy if exists "audit_exports_select_member" on public.audit_exports;
create policy "audit_exports_select_member"
on public.audit_exports for select
using (
  exists (select 1 from public.org_members m where m.org_id = audit_exports.org_id and m.user_id = auth.uid())
);

-- No direct write policies for authenticated. Exports are created via RPC.
create or replace function public.create_audit_export(
  p_org_id uuid,
  p_format text,
  p_scope jsonb
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

  insert into public.audit_exports(org_id, requested_by_user_id, format, scope, status)
  values (p_org_id, v_user_id, p_format, coalesce(p_scope,'{}'::jsonb), 'queued')
  returning id into v_id;

  return v_id;
end;
$$;

revoke all on function public.create_audit_export(uuid,text,jsonb) from public;
grant execute on function public.create_audit_export(uuid,text,jsonb) to authenticated;
