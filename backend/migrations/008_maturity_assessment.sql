-- ============================================================================
-- Legal AI OS — AI Maturity Assessment (008)
-- ============================================================================
-- Stores maturity assessments and links uploaded documents.
-- Reuses knowledge_documents for file storage.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- MATURITY ASSESSMENTS
-- ----------------------------------------------------------------------------
create table if not exists maturity_assessments (
    id                          uuid primary key default uuid_generate_v4(),
    client_id                   uuid not null references clients(id) on delete cascade,
    version                     int not null default 1,
    overall_level               int check (overall_level between 1 and 5),
    overall_level_label         text,                           -- "AI Aware", "AI Ready", etc.
    bottleneck_dimension        text,                           -- dimension key with lowest score
    bottleneck_why              text,                           -- why this dimension is the bottleneck
    bottleneck_what_this_means  text,                           -- plain-language impact
    dimensions                  jsonb not null default '[]',    -- [{key, name, score, rationale}, ...]
    stage_gaps                  jsonb not null default '[]',    -- [{from_level, to_level, from_label, to_label, whats_missing, what_it_unlocks}]
    summary                     text,                           -- prose summary of findings
    document_count              int not null default 0,         -- how many docs were analyzed
    document_ids                uuid[] not null default '{}',   -- references to knowledge_documents
    cost_usd                    numeric(10,6) default 0,
    created_by                  uuid not null,
    created_at                  timestamptz not null default now()
);

-- Add maturity_assessment_id to knowledge_documents for linking
alter table knowledge_documents
    add column if not exists maturity_assessment_id uuid
        references maturity_assessments(id) on delete set null;

-- Index for listing assessments by client
create index if not exists idx_maturity_assessments_client
    on maturity_assessments(client_id, created_at desc);

-- ----------------------------------------------------------------------------
-- SEED — add maturity-assessment to the functions registry
-- ----------------------------------------------------------------------------
insert into functions (slug, name, description, status, version) values
    ('maturity-assessment', 'AI Maturity Assessment', 'Upload firm documents, policies, and playbooks to get an honest AI maturity rating across five legal-specific dimensions — with bottleneck identification and stage gaps.', 'built', '1.0.0')
on conflict (slug) do update
    set name = excluded.name,
        description = excluded.description,
        status = excluded.status;

-- Global time-saved baseline (4 hours — manual maturity assessment equivalent)
insert into time_saved_baselines (function_id, baseline_seconds, description)
    select id, 14400, '4 hours — manual AI readiness assessment by consultant'
    from functions where slug = 'maturity-assessment'
on conflict (function_id, client_id) do nothing;
