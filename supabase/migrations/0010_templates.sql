create table if not exists public.templates (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  name text not null,
  description text not null,
  default_cadence text not null check (default_cadence in ('manual', 'hourly', 'daily', 'weekly')) default 'weekly',
  tags text[] not null default '{}'::text[],
  created_at timestamptz not null default now()
);

create table if not exists public.template_sources (
  id uuid primary key default gen_random_uuid(),
  template_id uuid not null references public.templates(id) on delete cascade,
  name text not null,
  url text not null,
  cadence text not null check (cadence in ('manual', 'hourly', 'daily', 'weekly')) default 'weekly',
  tags text[] not null default '{}'::text[],
  created_at timestamptz not null default now()
);

create index if not exists template_sources_template_id_idx on public.template_sources(template_id);
create unique index if not exists template_sources_template_url_idx on public.template_sources(template_id, url);

alter table public.templates enable row level security;
alter table public.template_sources enable row level security;

-- templates are public read-only catalog
drop policy if exists "templates_select_all" on public.templates;
create policy "templates_select_all" on public.templates for select using (true);

drop policy if exists "template_sources_select_all" on public.template_sources;
create policy "template_sources_select_all" on public.template_sources for select using (true);

-- keep source metadata for template installs
alter table public.sources
  add column if not exists tags text[] not null default '{}'::text[];

-- install RPC: create sources for org from template (member-only)
create or replace function public.install_template(p_org_id uuid, p_template_slug text)
returns int
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_template_id uuid;
  v_count int := 0;
begin
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

  select id into v_template_id
  from public.templates
  where slug = p_template_slug;

  if v_template_id is null then
    raise exception 'template not found';
  end if;

  insert into public.sources (org_id, name, type, url, is_enabled, cadence, next_run_at, tags)
  select
    p_org_id,
    ts.name,
    'url',
    ts.url,
    true,
    coalesce(ts.cadence, t.default_cadence),
    case coalesce(ts.cadence, t.default_cadence)
      when 'hourly' then now() + interval '1 hour'
      when 'daily' then now() + interval '1 day'
      when 'weekly' then now() + interval '1 week'
      else null
    end,
    array(
      select distinct merged_tag
      from unnest(coalesce(t.tags, '{}'::text[]) || coalesce(ts.tags, '{}'::text[])) as merged(merged_tag)
    )
  from public.template_sources ts
  join public.templates t on t.id = ts.template_id
  where ts.template_id = v_template_id
    and not exists (
      select 1
      from public.sources s
      where s.org_id = p_org_id and s.url = ts.url
    );

  get diagnostics v_count = row_count;
  return v_count;
end;
$$;

revoke all on function public.install_template(uuid,text) from public;
grant execute on function public.install_template(uuid,text) to authenticated;

insert into public.templates (slug, name, description, default_cadence, tags)
values
  (
    'soc2',
    'SOC 2',
    'Core security and availability monitoring aligned to SOC 2 trust services criteria.',
    'weekly',
    array['soc2', 'security', 'availability']::text[]
  ),
  (
    'iso27001',
    'ISO 27001',
    'ISMS-focused monitoring with ISO 27001 and Annex A-aligned reference sources.',
    'weekly',
    array['iso27001', 'isms', 'annex-a']::text[]
  ),
  (
    'gdpr',
    'GDPR',
    'EU privacy compliance monitoring using EDPB guidance and key EU legal sources.',
    'weekly',
    array['gdpr', 'privacy', 'eu']::text[]
  ),
  (
    'eu-ai-act',
    'EU AI Act',
    'Monitoring of official EU AI Act legal text, AI Office updates, and policy guidance.',
    'weekly',
    array['eu-ai-act', 'ai-governance', 'eu']::text[]
  )
on conflict (slug) do update
set
  name = excluded.name,
  description = excluded.description,
  default_cadence = excluded.default_cadence,
  tags = excluded.tags;

with seeded_template_sources(slug, name, url, cadence, tags) as (
  values
    ('soc2', 'AICPA SOC Suite of Services', 'https://www.aicpa-cima.com/topic/audit-assurance/service-organization-controls-soc-suite-of-services', 'weekly', array['soc2', 'aicpa']::text[]),
    ('soc2', 'NIST Cybersecurity Framework', 'https://www.nist.gov/cyberframework', 'weekly', array['soc2', 'security', 'framework']::text[]),
    ('soc2', 'NIST SP 800-53 Rev. 5', 'https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final', 'weekly', array['soc2', 'controls', 'security']::text[]),
    ('soc2', 'NIST SP 800-61 Rev. 2', 'https://csrc.nist.gov/publications/detail/sp/800-61/rev-2/final', 'weekly', array['soc2', 'incident-response']::text[]),
    ('soc2', 'CISA Cross-Sector CPGs', 'https://www.cisa.gov/cross-sector-cybersecurity-performance-goals', 'weekly', array['soc2', 'availability', 'cisa']::text[]),
    ('soc2', 'CISA KEV Catalog', 'https://www.cisa.gov/known-exploited-vulnerabilities-catalog', 'daily', array['soc2', 'vulnerability', 'threat-intel']::text[]),
    ('soc2', 'CISA Shields Up', 'https://www.cisa.gov/shields-up', 'daily', array['soc2', 'threat-intel']::text[]),
    ('soc2', 'CISA Secure Our World', 'https://www.cisa.gov/secure-our-world', 'weekly', array['soc2', 'awareness']::text[]),

    ('iso27001', 'ISO/IEC 27001 Standard', 'https://www.iso.org/standard/27001', 'weekly', array['iso27001', 'isms']::text[]),
    ('iso27001', 'ISO/IEC 27002:2022 Controls', 'https://www.iso.org/standard/75652.html', 'weekly', array['iso27001', 'annex-a', 'controls']::text[]),
    ('iso27001', 'ISO/IEC 27005 Risk Management', 'https://www.iso.org/standard/73906.html', 'weekly', array['iso27001', 'risk']::text[]),
    ('iso27001', 'ISO/IEC 27017 Cloud Security', 'https://www.iso.org/standard/76559.html', 'weekly', array['iso27001', 'cloud', 'annex-a']::text[]),
    ('iso27001', 'ISO/IEC 27018 PII Protection', 'https://www.iso.org/standard/76555.html', 'weekly', array['iso27001', 'privacy', 'cloud']::text[]),
    ('iso27001', 'ISO/IEC 27003 ISMS Implementation', 'https://www.iso.org/standard/80585.html', 'weekly', array['iso27001', 'isms', 'implementation']::text[]),
    ('iso27001', 'ISO Management System Standards', 'https://www.iso.org/management-system-standards.html', 'weekly', array['iso27001', 'management-system']::text[]),
    ('iso27001', 'NIST Privacy Framework', 'https://www.nist.gov/privacy-framework', 'weekly', array['iso27001', 'privacy', 'risk']::text[]),

    ('gdpr', 'GDPR Official Text (EU 2016/679)', 'https://eur-lex.europa.eu/eli/reg/2016/679/oj', 'weekly', array['gdpr', 'law', 'eur-lex']::text[]),
    ('gdpr', 'EDPB Guidelines and Recommendations', 'https://edpb.europa.eu/our-work-tools/our-documents/guidelines_en', 'weekly', array['gdpr', 'edpb', 'guidance']::text[]),
    ('gdpr', 'EDPB News', 'https://edpb.europa.eu/news/news_en', 'daily', array['gdpr', 'edpb', 'news']::text[]),
    ('gdpr', 'European Commission Data Protection', 'https://commission.europa.eu/law/law-topic/data-protection_en', 'weekly', array['gdpr', 'commission', 'policy']::text[]),
    ('gdpr', 'EU Data Protection for Organizations', 'https://commission.europa.eu/law/law-topic/data-protection/rules-business-and-organisations_en', 'weekly', array['gdpr', 'compliance', 'organizations']::text[]),
    ('gdpr', 'EDPS Data Protection Legislation', 'https://www.edps.europa.eu/data-protection/data-protection/legislation_en', 'weekly', array['gdpr', 'edps', 'law']::text[]),
    ('gdpr', 'Law Enforcement Directive (EU 2016/680)', 'https://eur-lex.europa.eu/eli/dir/2016/680/oj', 'weekly', array['gdpr', 'led', 'law-enforcement']::text[]),
    ('gdpr', 'European Commission Data Protection Explained', 'https://commission.europa.eu/law/law-topic/data-protection/data-protection-explained_en', 'weekly', array['gdpr', 'commission', 'explainer']::text[]),

    ('eu-ai-act', 'EU AI Act Official Text (EU 2024/1689)', 'https://eur-lex.europa.eu/eli/reg/2024/1689/oj', 'weekly', array['eu-ai-act', 'law', 'eur-lex']::text[]),
    ('eu-ai-act', 'EU Regulatory Framework for AI', 'https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai', 'weekly', array['eu-ai-act', 'commission', 'policy']::text[]),
    ('eu-ai-act', 'EU AI Office', 'https://digital-strategy.ec.europa.eu/en/policies/ai-office', 'weekly', array['eu-ai-act', 'ai-office', 'governance']::text[]),
    ('eu-ai-act', 'EU AI Pact', 'https://digital-strategy.ec.europa.eu/en/policies/ai-pact', 'weekly', array['eu-ai-act', 'ai-pact', 'guidance']::text[]),
    ('eu-ai-act', 'EU Digital Strategy News', 'https://digital-strategy.ec.europa.eu/en/news', 'daily', array['eu-ai-act', 'news', 'updates']::text[]),
    ('eu-ai-act', 'European Parliament AI Act Brief', 'https://www.europarl.europa.eu/topics/en/article/20230601STO93804/eu-ai-act-first-regulation-on-artificial-intelligence', 'weekly', array['eu-ai-act', 'parliament', 'overview']::text[]),
    ('eu-ai-act', 'European Commission Artificial Intelligence Topic', 'https://commission.europa.eu/topics/artificial-intelligence_en', 'weekly', array['eu-ai-act', 'commission', 'topic']::text[])
)
insert into public.template_sources (template_id, name, url, cadence, tags)
select
  t.id,
  s.name,
  s.url,
  s.cadence,
  s.tags
from seeded_template_sources s
join public.templates t on t.slug = s.slug
on conflict (template_id, url) do update
set
  name = excluded.name,
  cadence = excluded.cadence,
  tags = excluded.tags;
