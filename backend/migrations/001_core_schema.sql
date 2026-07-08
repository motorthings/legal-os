-- ============================================================================
-- Legal AI OS — Core Schema
-- ============================================================================
-- Foundation for all 8 functions. Every table supports:
--   - Multi-tenancy (client_id on every row)
--   - Practice-group scoping (practice_group_id)
--   - Immutable audit trail (append-only)
--   - Invocation-level metrics (cost, time, tokens, time_saved)
--   - Row-Level Security (RLS policies enforced at database layer)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- EXTENSIONS
-- ----------------------------------------------------------------------------
create extension if not exists "uuid-ossp";
create extension if not exists vector;            -- embedding search (KM, DD clause grouping)
create extension if not exists "pgcrypto";       -- cryptographic functions

-- ----------------------------------------------------------------------------
-- ORGANIZATIONAL MODEL (Layer 4)
-- ----------------------------------------------------------------------------

-- Client organizations (law firms, corporate legal departments)
create table if not exists clients (
    id              uuid primary key default uuid_generate_v4(),
    name            text not null,
    slug            text not null unique,                -- url-safe identifier
    industry        text,                                -- e.g. "financial_services", "healthcare"
    jurisdiction    text,                                -- primary jurisdiction
    config          jsonb not null default '{}',         -- client-specific overrides
    is_active       boolean not null default true,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

-- Practice groups / departments within a client org
create table if not exists practice_groups (
    id              uuid primary key default uuid_generate_v4(),
    client_id       uuid not null references clients(id) on delete cascade,
    name            text not null,                       -- e.g. "Corporate M&A", "Litigation", "IP"
    slug            text not null,
    description     text,
    is_active       boolean not null default true,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),

    unique(client_id, slug)
);

-- ----------------------------------------------------------------------------
-- USERS & PROFILES (extends Supabase Auth)
-- ----------------------------------------------------------------------------

-- User profiles — one row per auth.users entry, created via trigger
create table if not exists user_profiles (
    id              uuid primary key,                     -- matches auth.users.id
    client_id       uuid not null references clients(id),
    display_name    text not null,
    email           text,
    role            text not null default 'attorney',     -- 'admin', 'partner', 'attorney', 'paralegal', 'client'
    practice_group_ids uuid[] not null default '{}',      -- which groups they can access
    is_active       boolean not null default true,
    preferences     jsonb not null default '{}',
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

-- Trigger: auto-create profile when a new auth.users row is inserted
create or replace function handle_new_user()
returns trigger as $$
begin
    insert into public.user_profiles (id, client_id, display_name, email, role)
    values (
        new.id,
        (new.raw_user_meta_data->>'client_id')::uuid,
        coalesce(new.raw_user_meta_data->>'display_name', new.email),
        new.email,
        coalesce(new.raw_user_meta_data->>'role', 'attorney')
    );
    return new;
end;
$$ language plpgsql security definer;

-- Drop if exists for idempotency, then create
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function handle_new_user();

-- ----------------------------------------------------------------------------
-- MATTERS (central entity — everything relates to a matter)
-- ----------------------------------------------------------------------------

create type matter_status as enum (
    'intake',           -- initial evaluation
    'conflict_check',   -- conflicts being reviewed
    'active',           -- matter is open
    'on_hold',          -- paused
    'closed',           -- completed
    'rejected'          -- declined
);

create type billing_type as enum (
    'hourly',
    'fixed_fee',
    'contingency',
    'subscription',
    'pro_bono'
);

create table if not exists matters (
    id                  uuid primary key default uuid_generate_v4(),
    client_id           uuid not null references clients(id),
    practice_group_id   uuid not null references practice_groups(id),

    -- Core matter data
    name                text not null,
    description         text,
    matter_number       text,                              -- firm's internal reference
    jurisdiction        text,
    practice_area       text,                              -- free-text for flexibility
    status              matter_status not null default 'intake',

    -- Financial
    billing_type        billing_type,
    estimated_hours     integer,
    estimated_budget    numeric(12,2),                     -- in client's currency
    currency            text default 'USD',

    -- Parties
    client_contact      text,                              -- name/email of client POC
    adverse_parties     text[],                            -- array of adverse party names
    key_dates           jsonb not null default '{}',       -- {filing_deadline, trial_date, etc.}

    -- AI metadata
    intake_evaluation_id uuid,                             -- FK to audit_trail (created later)
    risk_level          text,                              -- 'high' | 'medium' | 'low'
    risk_score          integer,                           -- 0-100
    confidence          integer,                           -- 0-100 from router

    -- Tracking
    created_by          uuid not null references user_profiles(id),
    assigned_to         uuid references user_profiles(id),
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- FUNCTIONS REGISTRY (Layer 2 — what functions are available)
-- ----------------------------------------------------------------------------

create type function_status as enum ('built', 'configured', 'roadmap', 'deprecated');

create table if not exists functions (
    id              uuid primary key default uuid_generate_v4(),
    slug            text not null unique,                  -- 'matter-intake', 'contract-review', etc.
    name            text not null,                         -- display name
    description     text,
    status          function_status not null default 'roadmap',
    version         text not null default '0.1.0',
    config_schema   jsonb not null default '{}',           -- JSON Schema for function config
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

-- Per-client, per-function configuration
create table if not exists function_configs (
    id              uuid primary key default uuid_generate_v4(),
    function_id     uuid not null references functions(id) on delete cascade,
    client_id       uuid not null references clients(id) on delete cascade,
    is_enabled      boolean not null default false,
    config          jsonb not null default '{}',           -- function-specific settings
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),

    unique(function_id, client_id)
);

-- Human time-saved baselines per function (configurable per client)
create table if not exists time_saved_baselines (
    id              uuid primary key default uuid_generate_v4(),
    function_id     uuid not null references functions(id),
    client_id       uuid references clients(id),           -- null = global default
    baseline_seconds integer not null,                     -- e.g. 1800 = 30 min for matter intake
    description     text,                                  -- how the baseline is derived
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),

    unique(function_id, client_id)
);

-- ----------------------------------------------------------------------------
-- AUDIT TRAIL (Layer 1 — the non-negotiable pillar)
-- ============================================================================
-- Immutable. Append-only. Every AI decision captured.
-- RLS policy: INSERT only, no UPDATE/DELETE.
-- ----------------------------------------------------------------------------

create type audit_event_type as enum (
    'function_invocation',      -- a function was called
    'router_classification',    -- router stage output
    'evaluator_reasoning',      -- evaluator stage output
    'programmatic_score',       -- final scoring (deterministic)
    'human_override',           -- attorney overrode the AI
    'human_review',             -- attorney reviewed, no override
    'escalation',               -- auto-escalated (low confidence)
    'configuration_change'      -- config or standard changed
);

create table if not exists audit_trail (
    id                  uuid primary key default uuid_generate_v4(),
    client_id           uuid not null references clients(id),
    matter_id           uuid references matters(id),
    function_id         uuid references functions(id),

    -- What happened
    event_type          audit_event_type not null,
    event_summary       text,                              -- human-readable one-liner

    -- Full prompt/response capture
    prompt_raw          text,                              -- the full prompt sent to LLM
    response_raw        text,                              -- the full response from LLM
    reasoning_chain     text,                              -- extracted reasoning (explainability)

    -- Scoring (deterministic, replayable)
    dimension_scores    jsonb,                             -- [{dimension, score, weight, reasoning}]
    overall_score       integer,                           -- 0-100 weighted
    rubric_snapshot     jsonb,                             -- rubric version at time of evaluation
    rubric_version      text,                              -- semver of rubric used

    -- Model metadata
    model_used          text not null,                     -- e.g. 'claude-opus-4-8'
    model_version       text,                              -- specific model version
    provider            text,                              -- 'anthropic', 'azure_openai', 'bedrock'
    temperature         numeric(3,2),                      -- LLM temperature used

    -- Cost & performance
    prompt_tokens       integer,
    completion_tokens   integer,
    total_tokens        integer,
    cost_usd            numeric(10,6),                     -- computed cost in USD
    processing_time_ms  integer,                           -- total pipeline time

    -- Override tracking (traceability)
    overridden_by       uuid references user_profiles(id), -- who overrode
    override_reason     text,                              -- why they overrode
    original_score      integer,                           -- what the score was before override

    -- Who
    initiated_by        uuid not null references user_profiles(id),

    -- Chain of custody
    correlation_id      uuid,                              -- ties multiple audit rows into one invocation
    parent_audit_id     uuid references audit_trail(id),   -- for override chains

    created_at          timestamptz not null default now()
);

-- Indexes for audit queries
create index idx_audit_client      on audit_trail(client_id);
create index idx_audit_matter      on audit_trail(matter_id);
create index idx_audit_function    on audit_trail(function_id);
create index idx_audit_event       on audit_trail(event_type);
create index idx_audit_correlation on audit_trail(correlation_id);
create index idx_audit_created     on audit_trail(created_at desc);

-- ----------------------------------------------------------------------------
-- METRICS TELEMETRY (ROI Pipeline)
-- ============================================================================
-- Every function invocation writes one row.
-- ROI reporting is a query against this table.
-- ----------------------------------------------------------------------------

create table if not exists metrics (
    id                  uuid primary key default uuid_generate_v4(),
    client_id           uuid not null references clients(id),
    matter_id           uuid references matters(id),
    function_id         uuid not null references functions(id),
    audit_trail_id      uuid references audit_trail(id),   -- links to full audit context

    -- Timing
    started_at          timestamptz not null,
    completed_at        timestamptz not null,
    processing_time_ms  integer not null,

    -- Token usage
    prompt_tokens       integer not null default 0,
    completion_tokens   integer not null default 0,
    total_tokens        integer not null default 0,

    -- Cost
    cost_usd            numeric(10,6) not null default 0,
    model_used          text not null,

    -- Time saved (the ROI number)
    human_time_equivalent_ms integer not null default 0,   -- baseline from time_saved_baselines
    time_saved_ms       integer not null default 0,        -- human_time_equivalent_ms - processing_time_ms

    -- Outcome
    result_quality      text,                              -- 'pass', 'flag', 'escalate', 'review'
    confidence          integer,                           -- 0-100 from router

    -- Attribution
    initiated_by        uuid not null references user_profiles(id),
    practice_group_id   uuid references practice_groups(id),

    -- Tags for aggregation
    tags                jsonb not null default '{}',       -- flexible tagging for custom reporting

    created_at          timestamptz not null default now()
);

-- Indexes for aggregation queries (reporting)
create index idx_metrics_client     on metrics(client_id);
create index idx_metrics_function   on metrics(function_id);
create index idx_metrics_matter     on metrics(matter_id);
create index idx_metrics_time       on metrics(created_at desc);
create index idx_metrics_pg         on metrics(practice_group_id);

-- ----------------------------------------------------------------------------
-- LEGAL STANDARDS (shared across contract-review, DD, regulatory)
-- ----------------------------------------------------------------------------

create table if not exists legal_standards (
    id              uuid primary key default uuid_generate_v4(),
    client_id       uuid not null references clients(id),
    name            text not null,
    category        text not null,                         -- 'contract_term', 'compliance', 'regulatory'
    description     text,
    jurisdiction    text,
    acceptable_values text[],                              -- what passes
    severity        text not null default 'medium',        -- 'critical', 'high', 'medium', 'low'
    is_active       boolean not null default true,
    version         text not null default '1.0.0',
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- KNOWLEDGE BASE (Layer 0 — shared across KM, DD, contract-review)
-- ----------------------------------------------------------------------------

create table if not exists knowledge_documents (
    id              uuid primary key default uuid_generate_v4(),
    client_id       uuid not null references clients(id),
    practice_group_id uuid references practice_groups(id),

    title           text not null,
    document_type   text,                                  -- 'contract', 'brief', 'memo', 'opinion', 'research'
    source_url      text,
    source_file     text,                                  -- original filename

    -- Content
    raw_text        text,                                  -- extracted text
    chunk_count     integer default 0,
    metadata        jsonb not null default '{}',

    -- Embedding (pgvector)
    embedding       vector(1024),                          -- Voyage AI embedding dimension

    -- Version tracking
    version         text default '1.0.0',
    is_active       boolean not null default true,

    created_by      uuid references user_profiles(id),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

create index idx_kb_embedding on knowledge_documents
    using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);

-- ----------------------------------------------------------------------------
-- SEED DATA — the 8 functions
-- ----------------------------------------------------------------------------

insert into functions (slug, name, description, status, version) values
    ('matter-intake',           'Matter Intake & Triage',           'Structured evaluation of new matters in under 10 seconds — practice area, conflicts, risk, staffing, data integrity.', 'built', '1.0.0'),
    ('contract-review',         'Contract Review & Analysis',       'Upload a contract, get a structured risk analysis with clause-level flagging and human-in-the-loop review.', 'built', '1.0.0'),
    ('employment-agents',       'Employment Legal Agents',          'AI agents for employment law — policy review, compliance checking, and worker classification analysis.', 'built', '1.0.0'),
    ('cowork-legal-plugin',     'Cowork Legal Plugin',              'Legal AI plugin for the Cowork knowledge work platform — inline contract review and matter evaluation.', 'built', '1.0.0'),
    ('due-diligence',           'Due Diligence Accelerator',        'Bulk document ingestion, deal-specific target standards, deviation-only reporting with clause grouping.', 'roadmap', '0.1.0'),
    ('regulatory-monitor',      'Regulatory Change Monitor',        'Poll regulatory sources, extract structured changes, map to active matters by jurisdiction, notify responsible teams.', 'roadmap', '0.1.0'),
    ('km-intelligence',         'KM & Precedent Intelligence',      'Semantic search across all firm documents, precedent matching, "have we done this before?" with citations.', 'roadmap', '0.1.0'),
    ('client-value-reporting',  'Client Value Reporting',           'Per-client quarterly reports: total matters, time saved, risk distribution, governance artifacts. Math to back it up.', 'roadmap', '0.1.0')
on conflict (slug) do update
    set name = excluded.name,
        description = excluded.description,
        status = excluded.status;

-- Global time-saved baselines (seconds per manual equivalent)
insert into time_saved_baselines (function_id, baseline_seconds, description)
    select id, 1800,  '30 min — manual intake evaluation by partner'
    from functions where slug = 'matter-intake'
on conflict (function_id, client_id) do nothing;

insert into time_saved_baselines (function_id, baseline_seconds, description)
    select id, 7200,  '2 hours — manual contract review by associate + partner'
    from functions where slug = 'contract-review'
on conflict (function_id, client_id) do nothing;

insert into time_saved_baselines (function_id, baseline_seconds, description)
    select id, 54000, '15 hours — manual due diligence per document set'
    from functions where slug = 'due-diligence'
on conflict (function_id, client_id) do nothing;

insert into time_saved_baselines (function_id, baseline_seconds, description)
    select id, 3600,  '1 hour — manual regulatory change review per jurisdiction'
    from functions where slug = 'regulatory-monitor'
on conflict (function_id, client_id) do nothing;

insert into time_saved_baselines (function_id, baseline_seconds, description)
    select id, 1800,  '30 min — manual precedent search per query'
    from functions where slug = 'km-intelligence'
on conflict (function_id, client_id) do nothing;

insert into time_saved_baselines (function_id, baseline_seconds, description)
    select id, 14400, '4 hours — manual quarterly report preparation per client'
    from functions where slug = 'client-value-reporting'
on conflict (function_id, client_id) do nothing;

-- ----------------------------------------------------------------------------
-- ROW-LEVEL SECURITY (RLS) — THE WALLS
-- ============================================================================
-- These policies enforce data isolation at the database layer.
-- Application code CANNOT bypass them (only service_role key can).
-- ----------------------------------------------------------------------------

-- Enable RLS on all core tables
alter table clients enable row level security;
alter table practice_groups enable row level security;
alter table user_profiles enable row level security;
alter table matters enable row level security;
alter table function_configs enable row level security;
alter table time_saved_baselines enable row level security;
alter table audit_trail enable row level security;
alter table metrics enable row level security;
alter table legal_standards enable row level security;
alter table knowledge_documents enable row level security;

-- Helper: get the current user's client_id from their profile
create or replace function current_user_client_id()
returns uuid as $$
    select client_id from public.user_profiles where id = auth.uid();
$$ language sql stable security definer;

-- Helper: get the current user's practice_group_ids
create or replace function current_user_practice_groups()
returns uuid[] as $$
    select practice_group_ids from public.user_profiles where id = auth.uid();
$$ language sql stable security definer;

-- CLIENTS: users can read their own client
create policy "Users can read own client"
    on clients for select
    using (id = current_user_client_id());

-- PRACTICE GROUPS: users can read groups in their client
create policy "Users can read own client practice groups"
    on practice_groups for select
    using (client_id = current_user_client_id());

-- USER PROFILES: users can read profiles in their client, update their own
create policy "Users can read profiles in their client"
    on user_profiles for select
    using (client_id = current_user_client_id());

create policy "Users can update own profile"
    on user_profiles for update
    using (id = auth.uid());

-- MATTERS: client-scoped + practice-group-scoped
create policy "Users can read matters in their practice groups"
    on matters for select
    using (
        client_id = current_user_client_id()
        and practice_group_id = any(current_user_practice_groups())
    );

create policy "Users can insert matters in their practice groups"
    on matters for insert
    with check (
        client_id = current_user_client_id()
        and practice_group_id = any(current_user_practice_groups())
    );

create policy "Users can update matters in their practice groups"
    on matters for update
    using (
        client_id = current_user_client_id()
        and practice_group_id = any(current_user_practice_groups())
    );

-- AUDIT TRAIL: append-only for application users
create policy "Users can read audit trail in their client"
    on audit_trail for select
    using (client_id = current_user_client_id());

create policy "Users can insert audit trail"
    on audit_trail for insert
    with check (client_id = current_user_client_id());

-- No UPDATE/DELETE on audit_trail — immutable

-- METRICS: read-only for application users (system writes via service_role)
create policy "Users can read metrics in their client"
    on metrics for select
    using (client_id = current_user_client_id());

create policy "System can insert metrics"
    on metrics for insert
    with check (client_id = current_user_client_id());

-- LEGAL STANDARDS: read for practice groups, write for partners/admins
create policy "Users can read standards in their client"
    on legal_standards for select
    using (client_id = current_user_client_id());

create policy "Users can insert standards in their client"
    on legal_standards for insert
    with check (client_id = current_user_client_id());

create policy "Users can update standards in their client"
    on legal_standards for update
    using (client_id = current_user_client_id());

-- KNOWLEDGE DOCUMENTS: practice-group scoped
create policy "Users can read knowledge docs in their practice groups"
    on knowledge_documents for select
    using (
        client_id = current_user_client_id()
        and (
            practice_group_id is null
            or practice_group_id = any(current_user_practice_groups())
        )
    );

-- FUNCTIONS: readable by all authenticated users
alter table functions enable row level security;
create policy "Authenticated users can read functions"
    on functions for select
    using (true);

-- ----------------------------------------------------------------------------
-- VIEWS — convenient aggregations
-- ----------------------------------------------------------------------------

-- Metrics rollup by client, function, month (powers the portfolio dashboard)
create or replace view metrics_monthly_rollup as
select
    client_id,
    function_id,
    date_trunc('month', created_at) as month,
    count(*) as invocations,
    sum(total_tokens) as total_tokens,
    sum(cost_usd) as total_cost_usd,
    sum(time_saved_ms) / 3600000.0 as hours_saved,        -- convert ms → hours
    avg(processing_time_ms) as avg_processing_ms,
    avg(confidence) as avg_confidence
from metrics
group by client_id, function_id, date_trunc('month', created_at);

-- Client summary (powers client value reporting)
create or replace view client_summary as
select
    c.id as client_id,
    c.name as client_name,
    count(distinct m.id) as total_matters,
    count(distinct m.id) filter (where m.status = 'active') as active_matters,
    count(distinct mt.function_id) as functions_used,
    sum(mt.cost_usd) as total_ai_cost_usd,
    sum(mt.time_saved_ms) / 3600000.0 as total_hours_saved,
    min(mt.created_at) as first_invocation,
    max(mt.created_at) as last_invocation
from clients c
left join matters m on m.client_id = c.id
left join metrics mt on mt.client_id = c.id
group by c.id, c.name;
