-- ============================================================================
-- Legal AI OS — Legal Research & Citation Intelligence
-- ============================================================================
-- Adds Descrybe-powered legal research as a first-class function.
-- Every query is linked to a matter, audited, and cached.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- RESEARCH QUERIES
-- ----------------------------------------------------------------------------
create table if not exists legal_research_queries (
    id                  uuid primary key default uuid_generate_v4(),
    client_id           uuid not null references clients(id),
    matter_id           uuid references matters(id),
    function_id         uuid references functions(id),
    audit_trail_id      uuid references audit_trail(id),

    -- Query context
    query_type          text not null,                      -- concept_search | text_search | citation_lookup | law_search | verify_quote
    query_text          text not null,
    jurisdiction        text,
    practice_area       text,
    extra_filters       jsonb not null default '{}',

    -- Execution metadata
    results_count       integer default 0,
    processing_time_ms  integer,
    cost_usd            numeric(10,6) not null default 0,
    cached              boolean not null default false,

    -- Chain of custody
    initiated_by        uuid not null references user_profiles(id),
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now()
);

create index idx_research_queries_client    on legal_research_queries(client_id);
create index idx_research_queries_matter    on legal_research_queries(matter_id);
create index idx_research_queries_function  on legal_research_queries(function_id);
create index idx_research_queries_type      on legal_research_queries(query_type);
create index idx_research_queries_created   on legal_research_queries(created_at desc);

-- ----------------------------------------------------------------------------
-- RESEARCH RESULTS
-- ----------------------------------------------------------------------------
create table if not exists legal_research_results (
    id                  uuid primary key default uuid_generate_v4(),
    query_id            uuid not null references legal_research_queries(id) on delete cascade,

    -- Result identity
    source              text not null,                      -- descrybe | internal_kb | etc.
    source_id           text,                               -- Descrybe case_id, statute citation, etc.
    case_id             text,                               -- Descrybe canonical case_id when available
    title               text not null,                      -- case name, statute title, etc.
    citation            text,
    jurisdiction        text,
    decision_year       integer,
    source_url          text,

    -- Content
    snippet             text,
    full_text           text,
    summary             text,
    passages            jsonb not null default '[]',        -- array of {passage, relevance}

    -- Verification
    treatment           text,                               -- positive | negative | cautious | neutral
    is_good_law         boolean,
    verified_at         timestamptz,

    -- Ranking
    relevance_score     numeric(5,4),

    created_at          timestamptz not null default now()
);

create index idx_research_results_query     on legal_research_results(query_id);
create index idx_research_results_case      on legal_research_results(case_id);
create index idx_research_results_citation  on legal_research_results(citation);

-- ----------------------------------------------------------------------------
-- FUNCTION REGISTRY
-- ----------------------------------------------------------------------------
insert into functions (slug, name, description, status, version) values
    ('legal-research', 'Legal Research & Citation Intelligence', 'Descrybe-powered case law, statutes, and citation verification integrated with matters and the knowledge base.', 'built', '0.1.0')
on conflict (slug) do update
    set name = excluded.name,
        description = excluded.description,
        status = excluded.status;

-- Time-saved baseline: 30 min manual legal research per query
insert into time_saved_baselines (function_id, baseline_seconds, description)
    select id, 1800, '30 min — manual legal research across case law, statutes, and regulations'
    from functions where slug = 'legal-research'
on conflict (function_id, client_id) do nothing;

-- ----------------------------------------------------------------------------
-- ROW-LEVEL SECURITY
-- ----------------------------------------------------------------------------
alter table legal_research_queries enable row level security;
alter table legal_research_results enable row level security;

create policy "Users can read research queries in their client"
    on legal_research_queries for select
    using (client_id = current_user_client_id());

create policy "Users can insert research queries in their client"
    on legal_research_queries for insert
    with check (client_id = current_user_client_id());

create policy "Users can read research results for their queries"
    on legal_research_results for select
    using (
        query_id in (
            select id from legal_research_queries
            where client_id = current_user_client_id()
        )
    );

create policy "Users can insert research results for their queries"
    on legal_research_results for insert
    with check (
        query_id in (
            select id from legal_research_queries
            where client_id = current_user_client_id()
        )
    );

-- ----------------------------------------------------------------------------
-- VIEWS
-- ----------------------------------------------------------------------------
create or replace view matter_research_summary as
select
    q.matter_id,
    count(distinct q.id) as total_queries,
    count(distinct r.id) as total_results,
    count(distinct r.id) filter (where r.source = 'descrybe') as descrybe_results,
    sum(q.cost_usd) as total_cost_usd,
    max(q.created_at) as last_research_at
from legal_research_queries q
left join legal_research_results r on r.query_id = q.id
where q.matter_id is not null
group by q.matter_id;
