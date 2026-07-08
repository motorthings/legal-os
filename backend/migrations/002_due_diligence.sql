-- ============================================================================
-- Legal AI OS — Due Diligence Accelerator Schema
-- ============================================================================
-- Migration 002: Deal-level document grouping, target standards, deviation tracking.
-- Builds on core schema (001).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- DEAL PROJECTS
-- ----------------------------------------------------------------------------

create type dd_project_status as enum (
    'draft',            -- being configured
    'uploading',        -- documents being added
    'analyzing',        -- batch analysis running
    'review',           -- results ready for attorney review
    'completed',        -- review done, report finalized
    'archived'
);

create table if not exists dd_projects (
    id                  uuid primary key default uuid_generate_v4(),
    client_id           uuid not null references clients(id),
    matter_id           uuid references matters(id),       -- optional link to a matter
    practice_group_id   uuid not null references practice_groups(id),

    name                text not null,
    description         text,
    deal_type           text,                              -- 'merger', 'acquisition', 'financing', 'ipo', etc.
    counterparty        text,                              -- who the deal is with
    jurisdiction        text,

    status              dd_project_status not null default 'draft',
    document_count      integer default 0,
    deviation_count     integer default 0,                 -- total deviations found
    critical_count      integer default 0,                 -- critical severity deviations

    created_by          uuid not null references user_profiles(id),
    assigned_to         uuid references user_profiles(id),
    completed_at        timestamptz,
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- TARGET STANDARDS (deal-specific)
-- ----------------------------------------------------------------------------

create table if not exists dd_target_standards (
    id                  uuid primary key default uuid_generate_v4(),
    project_id          uuid not null references dd_projects(id) on delete cascade,
    category            text not null,                     -- clause type
    standard_text       text,                              -- what the ideal clause says
    acceptable_values   text[],                            -- what's acceptable
    severity            text not null default 'medium',    -- 'critical', 'high', 'medium', 'low'
    is_active           boolean not null default true,
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- DOCUMENTS IN A DEAL
-- ----------------------------------------------------------------------------

create type dd_document_status as enum (
    'pending',          -- queued for processing
    'extracting',       -- text extraction in progress
    'analyzing',        -- LLM analysis in progress
    'analyzed',         -- analysis complete, deviations flagged
    'reviewed',         -- attorney reviewed
    'error'             -- processing failed
);

create table if not exists dd_documents (
    id                  uuid primary key default uuid_generate_v4(),
    project_id          uuid not null references dd_projects(id) on delete cascade,
    client_id           uuid not null references clients(id),

    filename            text not null,
    file_size_bytes     bigint,
    file_type           text,                              -- 'pdf', 'docx', 'xlsx'
    storage_path        text,                              -- Supabase Storage path

    status              dd_document_status not null default 'pending',
    extracted_text      text,                              -- raw extracted text
    extracted_at        timestamptz,
    analyzed_at         timestamptz,

    -- Clause grouping (embedding-based)
    embedding           vector(1024),                      -- document-level embedding for similarity
    clause_hash         text,                              -- hash of clause text for dedup

    reviewed_by         uuid references user_profiles(id),
    reviewed_at         timestamptz,
    review_notes        text,

    -- Error tracking
    error_message       text,
    retry_count         integer default 0,

    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- DEVIATIONS (flagged clause-by-clause)
-- ----------------------------------------------------------------------------

create type deviation_severity as enum ('critical', 'high', 'medium', 'low', 'info');

create table if not exists dd_deviations (
    id                  uuid primary key default uuid_generate_v4(),
    document_id         uuid not null references dd_documents(id) on delete cascade,
    project_id          uuid not null references dd_projects(id) on delete cascade,
    client_id           uuid not null references clients(id),

    -- What was found
    clause_type         text not null,                     -- 'indemnification', 'limitation_of_liability', etc.
    clause_text         text,                              -- the actual clause text found
    clause_location     text,                              -- section/page reference

    -- What it should be
    target_standard_id  uuid references dd_target_standards(id),
    expected_text       text,                              -- what the standard says

    -- Assessment
    severity            deviation_severity not null,
    deviation_summary   text,                              -- one-line description of the gap
    detailed_analysis   text,                              -- full LLM reasoning
    recommendation      text,                              -- suggested fix

    -- Clause grouping key (identical clauses across docs get same key)
    clause_group_key    text,                              -- hash or embedding cluster ID

    -- Review
    reviewed_by         uuid references user_profiles(id),
    reviewed_at         timestamptz,
    review_decision     text,                              -- 'accept_risk', 'must_fix', 'noted', 'false_positive'
    review_notes        text,

    -- Audit
    audit_trail_id      uuid references audit_trail(id),   -- links to full prompt/response capture
    model_used          text,
    confidence          integer,                           -- 0-100

    created_at          timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- INDEXES
-- ----------------------------------------------------------------------------

create index idx_dd_project_client    on dd_projects(client_id);
create index idx_dd_project_status    on dd_projects(status);
create index idx_dd_doc_project       on dd_documents(project_id);
create index idx_dd_doc_status        on dd_documents(status);
create index idx_dd_dev_project       on dd_deviations(project_id);
create index idx_dd_dev_severity      on dd_deviations(severity);
create index idx_dd_dev_group         on dd_deviations(clause_group_key);
create index idx_dd_dev_document      on dd_deviations(document_id);

-- Embedding index for clause similarity grouping
create index idx_dd_doc_embedding on dd_documents
    using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);

-- ----------------------------------------------------------------------------
-- RLS
-- ----------------------------------------------------------------------------

alter table dd_projects enable row level security;
alter table dd_target_standards enable row level security;
alter table dd_documents enable row level security;
alter table dd_deviations enable row level security;

create policy "Users can read DD projects in their practice groups"
    on dd_projects for select
    using (
        client_id = current_user_client_id()
        and practice_group_id = any(current_user_practice_groups())
    );

create policy "Users can insert DD projects in their practice groups"
    on dd_projects for insert
    with check (
        client_id = current_user_client_id()
        and practice_group_id = any(current_user_practice_groups())
    );

create policy "Users can update DD projects in their practice groups"
    on dd_projects for update
    using (
        client_id = current_user_client_id()
        and practice_group_id = any(current_user_practice_groups())
    );

create policy "Users can read target standards in their client"
    on dd_target_standards for select
    using (
        project_id in (select id from dd_projects where client_id = current_user_client_id())
    );

create policy "Users can read DD documents in their client"
    on dd_documents for select
    using (client_id = current_user_client_id());

create policy "Users can read deviations in their client"
    on dd_deviations for select
    using (client_id = current_user_client_id());

create policy "Users can update deviations (review decisions)"
    on dd_deviations for update
    using (client_id = current_user_client_id());

-- ----------------------------------------------------------------------------
-- VIEW — consolidated deviation report
-- ----------------------------------------------------------------------------

create or replace view dd_project_report as
select
    p.id as project_id,
    p.name as project_name,
    p.deal_type,
    p.status as project_status,
    p.document_count,
    count(dv.id) as total_deviations,
    count(dv.id) filter (where dv.severity = 'critical') as critical,
    count(dv.id) filter (where dv.severity = 'high') as high,
    count(dv.id) filter (where dv.severity = 'medium') as medium,
    count(dv.id) filter (where dv.severity = 'low') as low,
    count(dv.id) filter (where dv.review_decision is null) as unreviewed,
    count(distinct dv.clause_group_key) as unique_clause_issues,
    min(dv.created_at) as first_deviation_at,
    max(dv.created_at) as last_deviation_at
from dd_projects p
left join dd_deviations dv on dv.project_id = p.id
group by p.id, p.name, p.deal_type, p.status, p.document_count;
