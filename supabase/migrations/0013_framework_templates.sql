create table if not exists public.framework_templates (
  id uuid primary key default gen_random_uuid(),
  slug text unique not null,
  name text not null,
  description text not null,
  category text not null,
  is_public boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.framework_template_sources (
  id uuid primary key default gen_random_uuid(),
  template_id uuid not null references public.framework_templates(id) on delete cascade,
  title text not null,
  url text not null,
  kind text not null default 'web' check (kind in ('rss', 'atom', 'web')),
  cadence text not null default 'daily' check (cadence in ('manual', 'hourly', 'daily', 'weekly')),
  tags text[] not null default '{}'::text[],
  enabled_by_default boolean not null default true,
  created_at timestamptz not null default now()
);

create unique index if not exists framework_template_sources_template_url_idx
  on public.framework_template_sources(template_id, url);
create index if not exists framework_templates_public_name_idx
  on public.framework_templates(is_public, name);
create index if not exists framework_template_sources_template_id_idx
  on public.framework_template_sources(template_id);

alter table public.framework_templates enable row level security;
alter table public.framework_template_sources enable row level security;

drop policy if exists "framework_templates_select_authenticated" on public.framework_templates;
create policy "framework_templates_select_authenticated"
on public.framework_templates for select
using (auth.role() = 'authenticated');

drop policy if exists "framework_template_sources_select_authenticated" on public.framework_template_sources;
create policy "framework_template_sources_select_authenticated"
on public.framework_template_sources for select
using (auth.role() = 'authenticated');

insert into public.framework_templates (slug, name, description, category, is_public)
values
  (
    'gdpr',
    'GDPR',
    'Monitoring set for EU data protection updates from supervisory authorities and primary legal text.',
    'Privacy',
    true
  ),
  (
    'eu-ai-act',
    'EU AI Act',
    'Monitoring set for implementation and governance updates linked to Regulation (EU) 2024/1689.',
    'AI Governance',
    true
  ),
  (
    'soc2',
    'SOC 2',
    'Monitoring set for control framework and cyber guidance updates relevant to SOC 2 programs.',
    'Security',
    true
  ),
  (
    'iso27001',
    'ISO 27001',
    'Monitoring set for ISMS standards and implementation guidance used in ISO 27001 programs.',
    'Security',
    true
  ),
  (
    'sec-us-markets',
    'SEC/US Markets',
    'Monitoring set for U.S. financial regulatory updates from the SEC and Federal Register sources.',
    'Financial',
    true
  ),
  (
    'uk-legislation-tracker',
    'UK Legislation Tracker',
    'Monitoring set for statutory publication changes and selected UK regulator policy updates.',
    'Legal',
    true
  )
on conflict (slug) do update
set
  name = excluded.name,
  description = excluded.description,
  category = excluded.category,
  is_public = excluded.is_public;

with seeded_sources(template_slug, title, url, kind, cadence, tags, enabled_by_default) as (
  values
    ('gdpr', 'EDPB News', 'https://www.edpb.europa.eu/feed/news_en', 'rss', 'hourly', array['gdpr','privacy','edpb']::text[], true),
    ('gdpr', 'EDPB Publications', 'https://www.edpb.europa.eu/feed/publications_en', 'rss', 'daily', array['gdpr','privacy','edpb']::text[], true),
    ('gdpr', 'EUR-Lex GDPR Official Text', 'https://eur-lex.europa.eu/eli/reg/2016/679/oj', 'web', 'weekly', array['gdpr','privacy','law']::text[], true),
    ('gdpr', 'European Commission Data Protection', 'https://commission.europa.eu/law/law-topic/data-protection_en', 'web', 'weekly', array['gdpr','privacy','commission']::text[], true),

    ('eu-ai-act', 'EUR-Lex EU AI Act Official Text', 'https://eur-lex.europa.eu/eli/reg/2024/1689/oj', 'web', 'weekly', array['ai-act','ai-governance','law']::text[], true),
    ('eu-ai-act', 'EU Regulatory Framework for AI', 'https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai', 'web', 'weekly', array['ai-act','ai-governance','policy']::text[], true),
    ('eu-ai-act', 'EU AI Office', 'https://digital-strategy.ec.europa.eu/en/policies/ai-office', 'web', 'daily', array['ai-act','ai-governance','ai-office']::text[], true),
    ('eu-ai-act', 'European Commission AI Topic', 'https://commission.europa.eu/topics/artificial-intelligence_en', 'web', 'weekly', array['ai-act','ai-governance','commission']::text[], true),

    ('soc2', 'AICPA SOC Suite of Services', 'https://www.aicpa-cima.com/topic/audit-assurance/service-organization-controls-soc-suite-of-services', 'web', 'weekly', array['soc2','security','aicpa']::text[], true),
    ('soc2', 'NIST Cybersecurity Framework', 'https://www.nist.gov/cyberframework', 'web', 'weekly', array['soc2','security','nist']::text[], true),
    ('soc2', 'NIST SP 800-53 Rev. 5', 'https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final', 'web', 'weekly', array['soc2','security','controls']::text[], true),
    ('soc2', 'CISA Known Exploited Vulnerabilities Catalog', 'https://www.cisa.gov/known-exploited-vulnerabilities-catalog', 'web', 'daily', array['soc2','security','vulnerabilities']::text[], true),

    ('iso27001', 'ISO/IEC 27001 Standard', 'https://www.iso.org/standard/27001', 'web', 'weekly', array['iso27001','isms','standard']::text[], true),
    ('iso27001', 'ISO/IEC 27002 Controls', 'https://www.iso.org/standard/75652.html', 'web', 'weekly', array['iso27001','isms','controls']::text[], true),
    ('iso27001', 'ISO Management System Standards', 'https://www.iso.org/management-system-standards.html', 'web', 'weekly', array['iso27001','isms','governance']::text[], true),
    ('iso27001', 'NIST Privacy Framework', 'https://www.nist.gov/privacy-framework', 'web', 'weekly', array['iso27001','isms','risk']::text[], true),

    ('sec-us-markets', 'SEC Press Releases', 'https://www.sec.gov/news/pressreleases.rss', 'rss', 'daily', array['sec','us-markets','enforcement']::text[], true),
    ('sec-us-markets', 'Federal Register (GovInfo)', 'https://www.govinfo.gov/rss/fr.xml', 'rss', 'daily', array['sec','us-markets','federal-register']::text[], true),
    ('sec-us-markets', 'Code of Federal Regulations (GovInfo)', 'https://www.govinfo.gov/rss/cfr.xml', 'rss', 'weekly', array['sec','us-markets','cfr']::text[], true),
    ('sec-us-markets', 'SEC Rulemaking Activity', 'https://www.sec.gov/rules/rulemaking-activity', 'web', 'daily', array['sec','us-markets','rulemaking']::text[], true),

    ('uk-legislation-tracker', 'UK Legislation Publication Log', 'https://www.legislation.gov.uk/update/data.feed', 'atom', 'hourly', array['uk','legislation','law']::text[], true),
    ('uk-legislation-tracker', 'UK Legislation Browse New Laws', 'https://www.legislation.gov.uk/new', 'web', 'daily', array['uk','legislation','updates']::text[], true),
    ('uk-legislation-tracker', 'FCA Policy Statements', 'https://www.fca.org.uk/publications/policy-statements', 'web', 'weekly', array['uk','financial-regulation','fca']::text[], true),
    ('uk-legislation-tracker', 'ICO News and Blogs', 'https://ico.org.uk/about-the-ico/media-centre/news-and-blogs/', 'web', 'weekly', array['uk','privacy','ico']::text[], true)
)
insert into public.framework_template_sources (template_id, title, url, kind, cadence, tags, enabled_by_default)
select
  t.id,
  s.title,
  s.url,
  s.kind,
  s.cadence,
  s.tags,
  s.enabled_by_default
from seeded_sources s
join public.framework_templates t
  on t.slug = s.template_slug
on conflict (template_id, url) do update
set
  title = excluded.title,
  kind = excluded.kind,
  cadence = excluded.cadence,
  tags = excluded.tags,
  enabled_by_default = excluded.enabled_by_default;

create or replace function public.create_source_v3(
  p_org_id uuid,
  p_name text,
  p_url text,
  p_kind text default 'html',
  p_cadence text default 'daily',
  p_tags text[] default '{}'::text[],
  p_is_enabled boolean default true,
  p_title text default null,
  p_config jsonb default '{}'::jsonb
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_source_id uuid;
  v_kind text;
  v_type text;
  v_cadence text;
  v_next_run_at timestamptz;
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

  v_kind := lower(coalesce(nullif(trim(p_kind), ''), 'html'));
  if v_kind not in ('html', 'rss', 'pdf', 'github_releases') then
    raise exception 'invalid source kind';
  end if;

  v_cadence := lower(coalesce(nullif(trim(p_cadence), ''), 'daily'));
  if v_cadence not in ('manual', 'hourly', 'daily', 'weekly') then
    raise exception 'invalid cadence';
  end if;

  v_type := case when v_kind = 'rss' then 'rss' else 'url' end;
  v_next_run_at := case v_cadence
    when 'hourly' then now() + interval '1 hour'
    when 'daily' then now() + interval '1 day'
    when 'weekly' then now() + interval '1 week'
    else null
  end;

  insert into public.sources (
    org_id,
    name,
    type,
    kind,
    config,
    title,
    url,
    is_enabled,
    cadence,
    next_run_at,
    tags
  )
  values (
    p_org_id,
    p_name,
    v_type,
    v_kind,
    coalesce(p_config, '{}'::jsonb),
    nullif(trim(coalesce(p_title, '')), ''),
    p_url,
    coalesce(p_is_enabled, true),
    v_cadence,
    v_next_run_at,
    coalesce(p_tags, '{}'::text[])
  )
  returning id into v_source_id;

  return v_source_id;
end;
$$;

revoke all on function public.create_source_v3(uuid,text,text,text,text,text[],boolean,text,jsonb) from public;
grant execute on function public.create_source_v3(uuid,text,text,text,text,text[],boolean,text,jsonb) to authenticated;
