-- ============================================================================
-- Legal AI OS — POC Pipeline Schema
-- ============================================================================
-- Tracks AI proof-of-concept projects through their lifecycle.
-- Maps to JD: "Lead end-to-end delivery of AI-enabled client projects
-- from concept through implementation."

create table if not exists poc_projects (
    id                  uuid primary key default uuid_generate_v4(),
    client_id           uuid not null references clients(id) on delete cascade,
    practice_group_id   uuid references practice_groups(id) on delete set null,
    name                text not null,
    description         text,
    function_type       text not null,                       -- e.g. 'contract_review', 'due_diligence', 'matter_intake', 'regulatory_monitor', 'km_search', 'custom'
    status              text not null default 'discovery',   -- 'discovery', 'build', 'review', 'graduated', 'cancelled'
    champion_id         uuid references user_profiles(id),   -- practice group champion
    target_completion   date,
    started_at          date,
    completed_at        date,
    notes               text,
    created_by          uuid not null references user_profiles(id),
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now()
);

-- Feedback log for continuous improvement (JD: "Capture feedback for continuous improvement")
create table if not exists poc_feedback (
    id                  uuid primary key default uuid_generate_v4(),
    poc_project_id      uuid not null references poc_projects(id) on delete cascade,
    author_id           uuid not null references user_profiles(id),
    feedback_type       text not null default 'general',     -- 'bug', 'feature_request', 'usability', 'accuracy', 'general'
    body                text not null,
    resolved            boolean not null default false,
    created_at          timestamptz not null default now()
);

create index idx_poc_status on poc_projects(client_id, status);
create index idx_poc_practice_group on poc_projects(practice_group_id);
create index idx_poc_feedback_project on poc_feedback(poc_project_id);
