create table if not exists public.controls (
  id uuid primary key default gen_random_uuid(),
  framework_slug text not null,
  control_key text not null,
  title text not null,
  description text not null,
  severity_default text not null default 'medium'
    check (severity_default in ('low', 'medium', 'high')),
  tags text[] not null default '{}'::text[],
  created_at timestamptz not null default now(),
  unique (framework_slug, control_key)
);

create table if not exists public.control_evidence_items (
  id uuid primary key default gen_random_uuid(),
  control_id uuid not null references public.controls(id) on delete cascade,
  label text not null,
  description text not null,
  evidence_type text not null default 'document'
    check (evidence_type in ('document', 'screenshot', 'log', 'config', 'ticket', 'attestation')),
  required boolean not null default true,
  sort_order int not null default 0,
  created_at timestamptz not null default now()
);

create table if not exists public.control_guidance (
  id uuid primary key default gen_random_uuid(),
  control_id uuid not null references public.controls(id) on delete cascade,
  guidance_markdown text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.org_controls (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.orgs(id) on delete cascade,
  control_id uuid not null references public.controls(id) on delete cascade,
  status text not null default 'not_started'
    check (status in ('not_started', 'in_progress', 'implemented', 'needs_review')),
  owner_user_id uuid,
  notes text,
  created_at timestamptz not null default now(),
  unique (org_id, control_id)
);

create table if not exists public.finding_controls (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.orgs(id) on delete cascade,
  finding_id uuid not null references public.findings(id) on delete cascade,
  control_id uuid not null references public.controls(id) on delete cascade,
  confidence text not null default 'medium'
    check (confidence in ('low', 'medium', 'high')),
  created_at timestamptz not null default now(),
  unique (org_id, finding_id, control_id)
);

create index if not exists controls_framework_slug_idx on public.controls(framework_slug);
create index if not exists controls_framework_key_idx on public.controls(framework_slug, control_key);
create unique index if not exists control_evidence_items_control_label_idx
  on public.control_evidence_items(control_id, label);
create unique index if not exists control_guidance_control_id_idx on public.control_guidance(control_id);
create index if not exists org_controls_org_id_idx on public.org_controls(org_id);
create index if not exists org_controls_control_id_idx on public.org_controls(control_id);
create index if not exists finding_controls_org_id_idx on public.finding_controls(org_id);
create index if not exists finding_controls_finding_id_idx on public.finding_controls(finding_id);
create index if not exists finding_controls_control_id_idx on public.finding_controls(control_id);

alter table public.controls enable row level security;
alter table public.control_evidence_items enable row level security;
alter table public.control_guidance enable row level security;
alter table public.org_controls enable row level security;
alter table public.finding_controls enable row level security;

drop policy if exists "controls_select_authenticated" on public.controls;
create policy "controls_select_authenticated"
on public.controls for select
using (auth.role() = 'authenticated');

drop policy if exists "control_evidence_items_select_authenticated" on public.control_evidence_items;
create policy "control_evidence_items_select_authenticated"
on public.control_evidence_items for select
using (auth.role() = 'authenticated');

drop policy if exists "control_guidance_select_authenticated" on public.control_guidance;
create policy "control_guidance_select_authenticated"
on public.control_guidance for select
using (auth.role() = 'authenticated');

drop policy if exists "org_controls_select_member" on public.org_controls;
create policy "org_controls_select_member"
on public.org_controls for select
using (
  exists (
    select 1 from public.org_members m
    where m.org_id = org_controls.org_id
      and m.user_id = auth.uid()
  )
);

drop policy if exists "org_controls_insert_member" on public.org_controls;
create policy "org_controls_insert_member"
on public.org_controls for insert
with check (
  exists (
    select 1 from public.org_members m
    where m.org_id = org_controls.org_id
      and m.user_id = auth.uid()
  )
);

drop policy if exists "org_controls_update_member" on public.org_controls;
create policy "org_controls_update_member"
on public.org_controls for update
using (
  exists (
    select 1 from public.org_members m
    where m.org_id = org_controls.org_id
      and m.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1 from public.org_members m
    where m.org_id = org_controls.org_id
      and m.user_id = auth.uid()
  )
);

drop policy if exists "org_controls_delete_member" on public.org_controls;
create policy "org_controls_delete_member"
on public.org_controls for delete
using (
  exists (
    select 1 from public.org_members m
    where m.org_id = org_controls.org_id
      and m.user_id = auth.uid()
  )
);

drop policy if exists "finding_controls_select_member" on public.finding_controls;
create policy "finding_controls_select_member"
on public.finding_controls for select
using (
  exists (
    select 1 from public.org_members m
    where m.org_id = finding_controls.org_id
      and m.user_id = auth.uid()
  )
);

drop policy if exists "finding_controls_insert_member" on public.finding_controls;
create policy "finding_controls_insert_member"
on public.finding_controls for insert
with check (
  exists (
    select 1 from public.org_members m
    where m.org_id = finding_controls.org_id
      and m.user_id = auth.uid()
  )
);

drop policy if exists "finding_controls_update_member" on public.finding_controls;
create policy "finding_controls_update_member"
on public.finding_controls for update
using (
  exists (
    select 1 from public.org_members m
    where m.org_id = finding_controls.org_id
      and m.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1 from public.org_members m
    where m.org_id = finding_controls.org_id
      and m.user_id = auth.uid()
  )
);

drop policy if exists "finding_controls_delete_member" on public.finding_controls;
create policy "finding_controls_delete_member"
on public.finding_controls for delete
using (
  exists (
    select 1 from public.org_members m
    where m.org_id = finding_controls.org_id
      and m.user_id = auth.uid()
  )
);

create or replace function public.install_controls_for_template(
  p_org_id uuid,
  p_template_slug text
)
returns int
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_template_slug text;
  v_frameworks text[];
  v_inserted int := 0;
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

  v_template_slug := lower(coalesce(nullif(trim(p_template_slug), ''), ''));
  if v_template_slug = '' then
    raise exception 'template slug is required';
  end if;

  if not exists (select 1 from public.framework_templates t where t.slug = v_template_slug) then
    raise exception 'template not found';
  end if;

  v_frameworks := case v_template_slug
    when 'sec-us-markets' then array['soc2']::text[]
    when 'uk-legislation-tracker' then array['gdpr', 'eu-ai-act']::text[]
    else array[v_template_slug]::text[]
  end;

  insert into public.org_controls (org_id, control_id)
  select p_org_id, c.id
  from public.controls c
  where c.framework_slug = any(v_frameworks)
  on conflict (org_id, control_id) do nothing;

  get diagnostics v_inserted = row_count;
  return v_inserted;
end;
$$;

revoke all on function public.install_controls_for_template(uuid,text) from public;
grant execute on function public.install_controls_for_template(uuid,text) to authenticated;

create or replace function public.link_finding_to_control(
  p_org_id uuid,
  p_finding_id uuid,
  p_control_id uuid,
  p_confidence text
)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_confidence text;
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

  if not exists (
    select 1
    from public.findings f
    where f.id = p_finding_id and f.org_id = p_org_id
  ) then
    raise exception 'finding not found in org';
  end if;

  if not exists (
    select 1
    from public.controls c
    where c.id = p_control_id
  ) then
    raise exception 'control not found';
  end if;

  v_confidence := lower(coalesce(nullif(trim(p_confidence), ''), 'medium'));
  if v_confidence not in ('low', 'medium', 'high') then
    raise exception 'invalid confidence';
  end if;

  insert into public.finding_controls (org_id, finding_id, control_id, confidence)
  values (p_org_id, p_finding_id, p_control_id, v_confidence)
  on conflict (org_id, finding_id, control_id)
  do update set confidence = excluded.confidence;
end;
$$;

revoke all on function public.link_finding_to_control(uuid,uuid,uuid,text) from public;
grant execute on function public.link_finding_to_control(uuid,uuid,uuid,text) to authenticated;

with seed_controls(framework_slug, control_key, title, description, severity_default, tags) as (
  values
    ('soc2', 'CC1.2', 'Board and Management Oversight', 'The organization demonstrates independent oversight of internal control and risk management.', 'high', array['soc2', 'governance', 'oversight']::text[]),
    ('soc2', 'CC2.1', 'Integrity and Ethical Values', 'Standards of conduct are defined, communicated, and reinforced across the workforce.', 'medium', array['soc2', 'ethics', 'governance']::text[]),
    ('soc2', 'CC3.2', 'Risk Assessment Process', 'Risk identification and assessment are performed with defined ownership and cadence.', 'high', array['soc2', 'risk', 'security']::text[]),
    ('soc2', 'CC4.1', 'Monitoring Activities', 'Control performance is monitored and exceptions are escalated for remediation.', 'medium', array['soc2', 'monitoring', 'assurance']::text[]),
    ('soc2', 'CC5.2', 'Control Activities', 'Control activities are deployed and maintained to address prioritized risks.', 'medium', array['soc2', 'controls', 'operations']::text[]),
    ('soc2', 'CC6.1', 'Logical Access Security', 'Logical access to systems and data is restricted to authorized users and processes.', 'high', array['soc2', 'access', 'security']::text[]),
    ('soc2', 'CC6.6', 'Change Management', 'System changes are authorized, tested, approved, and tracked before deployment.', 'high', array['soc2', 'change-management', 'security']::text[]),
    ('soc2', 'CC7.2', 'Security Event Monitoring', 'Security events are detected, analyzed, and responded to in a timely manner.', 'high', array['soc2', 'incident-response', 'security']::text[]),
    ('soc2', 'CC8.1', 'Vendor and Business Partner Risk', 'Third-party service providers are assessed and monitored for control effectiveness.', 'medium', array['soc2', 'vendor-risk', 'security']::text[]),
    ('soc2', 'CC9.2', 'Business Continuity Readiness', 'Continuity and recovery capabilities are maintained and periodically validated.', 'medium', array['soc2', 'resilience', 'continuity']::text[]),

    ('iso27001', 'A.5.1', 'Information Security Policies', 'Information security policy objectives and directives are approved and communicated.', 'high', array['iso27001', 'policy', 'isms']::text[]),
    ('iso27001', 'A.5.7', 'Threat Intelligence', 'Threat intelligence is collected, analyzed, and used to inform defensive priorities.', 'medium', array['iso27001', 'threat-intelligence', 'isms']::text[]),
    ('iso27001', 'A.5.23', 'Information Security for Cloud Services', 'Cloud service security requirements are defined and monitored.', 'high', array['iso27001', 'cloud', 'isms']::text[]),
    ('iso27001', 'A.5.24', 'Incident Management Planning', 'Information security incident management processes are established and tested.', 'high', array['iso27001', 'incident-response', 'isms']::text[]),
    ('iso27001', 'A.5.30', 'ICT Readiness for Business Continuity', 'ICT continuity requirements are identified and integrated into continuity planning.', 'medium', array['iso27001', 'continuity', 'isms']::text[]),
    ('iso27001', 'A.8.8', 'Management of Technical Vulnerabilities', 'Vulnerabilities are identified, evaluated, prioritized, and remediated.', 'high', array['iso27001', 'vulnerability-management', 'security']::text[]),
    ('iso27001', 'A.8.9', 'Configuration Management', 'Configuration baselines are defined and enforced for critical assets.', 'high', array['iso27001', 'configuration', 'security']::text[]),
    ('iso27001', 'A.8.12', 'Data Leakage Prevention', 'Controls are implemented to prevent unauthorized disclosure of sensitive data.', 'high', array['iso27001', 'data-protection', 'isms']::text[]),
    ('iso27001', 'A.8.15', 'Logging', 'Security-relevant events are logged and retained for investigation and assurance.', 'medium', array['iso27001', 'logging', 'monitoring']::text[]),
    ('iso27001', 'A.8.16', 'Monitoring Activities', 'Networks, systems, and applications are monitored for anomalous behavior.', 'medium', array['iso27001', 'monitoring', 'security']::text[]),

    ('gdpr', 'GDPR-5', 'Principles for Processing', 'Personal data processing adheres to lawfulness, fairness, transparency, and minimization principles.', 'high', array['gdpr', 'privacy', 'governance']::text[]),
    ('gdpr', 'GDPR-6', 'Lawful Basis Management', 'A lawful basis is identified, documented, and maintained for each processing purpose.', 'high', array['gdpr', 'privacy', 'lawful-basis']::text[]),
    ('gdpr', 'GDPR-13', 'Privacy Notice Transparency', 'Data subjects receive clear and complete notices describing data processing activities.', 'medium', array['gdpr', 'privacy', 'transparency']::text[]),
    ('gdpr', 'GDPR-15', 'Data Subject Access', 'Processes exist to authenticate, track, and fulfill access requests within statutory timelines.', 'medium', array['gdpr', 'privacy', 'data-subject-rights']::text[]),
    ('gdpr', 'GDPR-17', 'Erasure and Retention', 'Erasure requests and retention rules are implemented and auditable.', 'medium', array['gdpr', 'privacy', 'retention']::text[]),
    ('gdpr', 'GDPR-25', 'Privacy by Design and Default', 'Privacy requirements are embedded in system design and default settings.', 'high', array['gdpr', 'privacy', 'engineering']::text[]),
    ('gdpr', 'GDPR-30', 'Records of Processing Activities', 'Comprehensive records of processing are maintained and kept current.', 'medium', array['gdpr', 'privacy', 'records']::text[]),
    ('gdpr', 'GDPR-32', 'Security of Processing', 'Appropriate technical and organizational safeguards protect personal data.', 'high', array['gdpr', 'privacy', 'security']::text[]),
    ('gdpr', 'GDPR-33', 'Breach Notification to Supervisory Authority', 'Breach assessment and supervisory authority notification process is documented and tested.', 'high', array['gdpr', 'privacy', 'incident-response']::text[]),
    ('gdpr', 'GDPR-35', 'Data Protection Impact Assessment', 'DPIAs are performed for high-risk processing and reviewed periodically.', 'high', array['gdpr', 'privacy', 'risk-assessment']::text[]),

    ('eu-ai-act', 'AIA-GOV-1', 'AI Governance Structure', 'Defined accountability and governance processes are established for AI systems.', 'high', array['eu-ai-act', 'ai-governance', 'governance']::text[]),
    ('eu-ai-act', 'AIA-QMS-1', 'Quality Management System', 'A quality management system covers AI lifecycle controls and recordkeeping.', 'high', array['eu-ai-act', 'ai-governance', 'qms']::text[]),
    ('eu-ai-act', 'AIA-RISK-1', 'AI Risk Management', 'A repeatable process identifies, evaluates, and mitigates AI-related risk.', 'high', array['eu-ai-act', 'ai-governance', 'risk-management']::text[]),
    ('eu-ai-act', 'AIA-RISK-2', 'Post-Market Monitoring', 'Post-market monitoring captures incidents, performance drift, and corrective actions.', 'medium', array['eu-ai-act', 'ai-governance', 'monitoring']::text[]),
    ('eu-ai-act', 'AIA-DATA-1', 'Training Data Governance', 'Training and validation data quality, lineage, and governance controls are enforced.', 'high', array['eu-ai-act', 'ai-governance', 'data-governance']::text[]),
    ('eu-ai-act', 'AIA-TECH-1', 'Technical Documentation', 'Technical documentation is complete, current, and available to regulators when required.', 'medium', array['eu-ai-act', 'ai-governance', 'documentation']::text[]),
    ('eu-ai-act', 'AIA-TRANS-1', 'Transparency to Deployers and Users', 'Required disclosures are provided to deployers and affected persons.', 'medium', array['eu-ai-act', 'ai-governance', 'transparency']::text[]),
    ('eu-ai-act', 'AIA-HUMAN-1', 'Human Oversight', 'Human oversight mechanisms are defined, trained, and operationalized.', 'high', array['eu-ai-act', 'ai-governance', 'human-oversight']::text[]),
    ('eu-ai-act', 'AIA-REG-1', 'Regulatory Cooperation and Recordkeeping', 'Required technical files and records are retained to support regulatory review.', 'medium', array['eu-ai-act', 'ai-governance', 'records']::text[]),
    ('eu-ai-act', 'AIA-INC-1', 'Serious Incident Handling', 'AI incidents are triaged, investigated, and escalated through formal response workflows.', 'high', array['eu-ai-act', 'ai-governance', 'incident-response']::text[])
)
insert into public.controls (framework_slug, control_key, title, description, severity_default, tags)
select framework_slug, control_key, title, description, severity_default, tags
from seed_controls
on conflict (framework_slug, control_key) do update
set
  title = excluded.title,
  description = excluded.description,
  severity_default = excluded.severity_default,
  tags = excluded.tags;

with target_controls as (
  select c.id
  from public.controls c
  where c.framework_slug in ('soc2', 'iso27001', 'gdpr', 'eu-ai-act')
),
evidence_templates(sort_order, label, description, evidence_type, required) as (
  values
    (10, 'Control design document', 'Documented control design, policy reference, and scope boundaries.', 'document', true),
    (20, 'Execution evidence', 'Operational evidence showing control execution for the latest review period.', 'log', true),
    (30, 'Remediation tracking', 'Ticket or attestation for outstanding gaps, exceptions, or compensating controls.', 'ticket', false)
)
insert into public.control_evidence_items (
  control_id,
  label,
  description,
  evidence_type,
  required,
  sort_order
)
select
  c.id,
  t.label,
  t.description,
  t.evidence_type,
  t.required,
  t.sort_order
from target_controls c
cross join evidence_templates t
on conflict (control_id, label) do update
set
  description = excluded.description,
  evidence_type = excluded.evidence_type,
  required = excluded.required,
  sort_order = excluded.sort_order;

insert into public.control_guidance (control_id, guidance_markdown)
select
  c.id,
  concat(
    '### Implementation Guidance', E'\n\n',
    '- Assign a named control owner and define the review cadence.', E'\n',
    '- Document the objective, scope, and evidence retention standard for this control.', E'\n',
    '- Capture periodic execution evidence and track open exceptions with target dates.', E'\n',
    '- Validate effectiveness through recurring review and update procedures as systems change.', E'\n\n',
    'Framework: **', c.framework_slug, '**', E'\n',
    'Control: **', c.control_key, ' - ', c.title, '**'
  )
from public.controls c
where c.framework_slug in ('soc2', 'iso27001', 'gdpr', 'eu-ai-act')
on conflict (control_id) do update
set guidance_markdown = excluded.guidance_markdown;
