-- Enable required extension
create extension if not exists "pgcrypto";

-- Orgs table
create table if not exists public.orgs (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz not null default now()
);

-- Org members table
create table if not exists public.org_members (
  org_id uuid not null references public.orgs(id) on delete cascade,
  user_id uuid not null,
  role text not null default 'member',
  created_at timestamptz not null default now(),
  primary key (org_id, user_id)
);

-- Helpful index
create index if not exists org_members_user_id_idx on public.org_members(user_id);

-- RLS
alter table public.orgs enable row level security;
alter table public.org_members enable row level security;

-- Policies: users can read orgs they belong to
drop policy if exists "orgs_select_member" on public.orgs;
create policy "orgs_select_member"
on public.orgs for select
using (
  exists (
    select 1 from public.org_members m
    where m.org_id = orgs.id
      and m.user_id = auth.uid()
  )
);

-- Users can insert orgs (creator becomes owner via a transaction in backend later)
drop policy if exists "orgs_insert_authenticated" on public.orgs;
create policy "orgs_insert_authenticated"
on public.orgs for insert
to authenticated
with check (true);

-- Org members: users can see their membership rows
drop policy if exists "org_members_select_self" on public.org_members;
create policy "org_members_select_self"
on public.org_members for select
using (user_id = auth.uid());

-- Org members insert/update/delete will be handled by backend with service role later.
-- For now, block by default (no policies for write).
