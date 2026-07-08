-- ============================================================================
-- Legal AI OS — Regulatory Change Monitor Schema
-- ============================================================================
-- Migration 003: Poll regulatory sources, extract structured changes,
-- map to active matters by jurisdiction + practice area.
-- Builds on core schema (001).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- REGULATORY SOURCES
-- ----------------------------------------------------------------------------

create type source_status as enum ('active', 'paused', 'error', 'archived');
create type change_type as enum ('new_regulation', 'amendment', 'repeal', 'guidance', 'enforcement_action', 'court_decision', 'other');
create type impact_severity as enum ('critical', 'high', 'medium', 'low', 'monitor');

create table if not exists regulatory_sources (
    id                  uuid primary key default uuid_generate_v4(),
    name                text not null,
    url                 text not null,
    jurisdiction        text not null,                     -- 'US', 'UK', 'EU', 'US-CA', etc.
    agency              text not null,                     -- 'SEC', 'FTC', 'ICO', etc.
    source_type         text default 'rss',                -- 'rss', 'api', 'scrape', 'manual'
    poll_frequency      text default 'daily',              -- 'hourly', 'daily', 'weekly', 'monthly'
    last_polled_at      timestamptz,
    last_change_at      timestamptz,
    status              source_status not null default 'active',
    config              jsonb not null default '{}',       -- source-specific config (headers, XPaths, etc.)
    notes               text,
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- REGULATORY UPDATES (extracted changes)
-- ----------------------------------------------------------------------------

create table if not exists regulatory_updates (
    id                  uuid primary key default uuid_generate_v4(),
    source_id           uuid not null references regulatory_sources(id) on delete cascade,

    -- What changed
    regulation_name     text not null,
    regulation_reference text,                             -- e.g. "17 CFR § 240.14a-8"
    jurisdiction        text not null,
    agency              text,
    change_type         change_type not null,
    change_summary      text not null,                     -- one-paragraph summary from LLM
    detailed_analysis   text,                              -- full LLM extraction
    effective_date      date,
    compliance_deadline date,

    -- Metadata
    source_url          text,                              -- URL to original publication
    raw_text            text,                              -- the raw regulatory text analyzed
    affected_industries text[],                            -- 'financial_services', 'healthcare', etc.
    affected_practice_areas text[],                        -- 'corporate', 'litigation', 'employment', etc.
    keywords            text[],                            -- extracted keywords for matching

    -- Processing
    model_used          text,                              -- which LLM extracted this
    confidence           integer,                          -- 0-100 extraction confidence
    is_processed        boolean default false,             -- has it been reviewed by a human?
    duplicate_of        uuid references regulatory_updates(id), -- dedup

    -- Audit
    audit_trail_id      uuid references audit_trail(id),
    created_at          timestamptz not null default now()
);

create index idx_reg_updates_jurisdiction on regulatory_updates(jurisdiction);
create index idx_reg_updates_agency on regulatory_updates(agency);
create index idx_reg_updates_change_type on regulatory_updates(change_type);
create index idx_reg_updates_effective on regulatory_updates(effective_date);
create index idx_reg_updates_created on regulatory_updates(created_at desc);

-- ----------------------------------------------------------------------------
-- MATTER REGULATORY FLAGS (updates matched to active matters)
-- ----------------------------------------------------------------------------

create type flag_status as enum ('unreviewed', 'acknowledged', 'action_required', 'no_action', 'resolved');

create table if not exists matter_regulatory_flags (
    id                  uuid primary key default uuid_generate_v4(),
    matter_id           uuid not null references matters(id) on delete cascade,
    update_id           uuid not null references regulatory_updates(id) on delete cascade,
    client_id           uuid not null references clients(id),

    -- Impact assessment
    impact_severity     impact_severity not null,
    impact_summary      text,                              -- why this matters for this specific matter
    action_required     text,                              -- what the team needs to do
    deadline            date,                              -- when action is needed by

    -- Status
    status              flag_status not null default 'unreviewed',
    assigned_to         uuid references user_profiles(id),
    reviewed_by         uuid references user_profiles(id),
    reviewed_at         timestamptz,
    review_notes        text,

    -- Notification
    notified_at         timestamptz,
    notification_channel text,                             -- 'email', 'slack', 'webhook'

    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now()
);

create index idx_mrf_matter on matter_regulatory_flags(matter_id);
create index idx_mrf_update on matter_regulatory_flags(update_id);
create index idx_mrf_client on matter_regulatory_flags(client_id);
create index idx_mrf_status on matter_regulatory_flags(status);
create index idx_mrf_severity on matter_regulatory_flags(impact_severity);

-- ----------------------------------------------------------------------------
-- RLS
-- ----------------------------------------------------------------------------

alter table regulatory_sources enable row level security;
alter table regulatory_updates enable row level security;
alter table matter_regulatory_flags enable row level security;

-- Sources: readable by all authenticated users
create policy "Authenticated users can read regulatory sources"
    on regulatory_sources for select
    using (true);

-- Updates: readable by all authenticated users
create policy "Authenticated users can read regulatory updates"
    on regulatory_updates for select
    using (true);

-- Flags: client-scoped
create policy "Users can read flags in their client"
    on matter_regulatory_flags for select
    using (client_id = current_user_client_id());

create policy "Users can update flags in their client"
    on matter_regulatory_flags for update
    using (client_id = current_user_client_id());

-- ----------------------------------------------------------------------------
-- VIEWS
-- ----------------------------------------------------------------------------

-- Active regulatory alerts grouped by jurisdiction
create or replace view regulatory_alerts as
select
    ru.jurisdiction,
    ru.agency,
    ru.change_type,
    ru.change_summary,
    ru.effective_date,
    ru.compliance_deadline,
    rs.name as source_name,
    count(mrf.id) as flagged_matters,
    count(mrf.id) filter (where mrf.impact_severity = 'critical') as critical_flags
from regulatory_updates ru
join regulatory_sources rs on rs.id = ru.source_id
left join matter_regulatory_flags mrf on mrf.update_id = ru.id
where ru.effective_date >= current_date - interval '90 days'
   or ru.compliance_deadline >= current_date
group by ru.jurisdiction, ru.agency, ru.change_type, ru.change_summary,
         ru.effective_date, ru.compliance_deadline, rs.name
order by ru.effective_date desc;

-- ----------------------------------------------------------------------------
-- SEED: 10 key regulatory sources
-- ----------------------------------------------------------------------------

insert into regulatory_sources (name, url, jurisdiction, agency, source_type, poll_frequency) values
    ('SEC Rules & Regulations',   'https://www.sec.gov/rules',              'US',   'SEC',  'rss', 'daily'),
    ('FTC Business Guidance',     'https://www.ftc.gov/business-guidance',  'US',   'FTC',  'rss', 'daily'),
    ('ICO Updates (UK)',          'https://ico.org.uk/about-the-ico/news-and-events/', 'UK', 'ICO', 'rss', 'daily'),
    ('EU Official Journal',       'https://eur-lex.europa.eu/oj/',          'EU',   'EU',   'rss', 'daily'),
    ('FINRA Notices',             'https://www.finra.org/rules-guidance',   'US',   'FINRA','rss', 'daily'),
    ('CFPB Rulemaking',           'https://www.consumerfinance.gov/rules-policy/', 'US', 'CFPB', 'rss', 'daily'),
    ('DOJ Antitrust',             'https://www.justice.gov/atr',            'US',   'DOJ',  'rss', 'weekly'),
    ('FCA Handbook (UK)',         'https://www.handbook.fca.org.uk/',       'UK',   'FCA',  'rss', 'weekly'),
    ('EDPB Guidelines (EU)',      'https://edpb.europa.eu/',                'EU',   'EDPB', 'rss', 'weekly'),
    ('CA AG Opinions',            'https://oag.ca.gov/',                    'US-CA','CA-AG','rss', 'weekly')
on conflict do nothing;
