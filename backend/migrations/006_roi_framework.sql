-- ============================================================================
-- Legal AI OS — ROI Framework Schema
-- ============================================================================
-- Powers the JD requirement: "Develop frameworks to track AI solution
-- performance, including time saved, cost impact, and quality metrics."
--
-- Four sub-systems:
--   1. Rate cards — time saved × rate = cost avoided
--   2. Calibrated baselines — defensible "this used to take X hours" methodology
--   3. Quality metrics — override rate, accuracy, reviewer agreement
--   4. Adoption tracking — eligible users denominator for adoption %
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. RATE CARDS
-- ----------------------------------------------------------------------------
-- Cost impact = time saved × the right rate. Different practice groups
-- and clients may use different rates (blended, partner, associate).

create table if not exists rate_cards (
    id                  uuid primary key default uuid_generate_v4(),
    client_id           uuid not null references clients(id) on delete cascade,
    practice_group_id   uuid references practice_groups(id) on delete set null,
    rate_type           text not null default 'blended',    -- 'blended', 'partner', 'associate', 'paralegal'
    hourly_rate_usd     numeric(10,2) not null,
    effective_from      date not null default current_date,
    effective_to        date,                                -- null = currently active
    created_by          uuid not null references user_profiles(id),
    created_at          timestamptz not null default now(),

    -- Only one active rate per client/group/type at a time
    unique(client_id, practice_group_id, rate_type, effective_from)
);

-- Default blended rate per client (practice_group_id null = firm-wide default)
create index idx_rate_cards_active on rate_cards(client_id, practice_group_id)
    where effective_to is null;

-- ----------------------------------------------------------------------------
-- 2. CALIBRATED BASELINES
-- ----------------------------------------------------------------------------
-- Extends the existing time_saved_baselines table with methodology metadata
-- so "this used to take 2 hours" is defensible, not an assertion.

-- Add methodology columns to existing time_saved_baselines table
alter table if exists time_saved_baselines
    add column if not exists methodology text,
    add column if not exists calibrated_by uuid references user_profiles(id),
    add column if not exists calibrated_at timestamptz,
    add column if not exists sample_size integer,
    add column if not exists confidence_level text default 'medium';  -- 'low', 'medium', 'high'

-- Baseline change log — tracks who changed what and why
create table if not exists baseline_calibrations (
    id                  uuid primary key default uuid_generate_v4(),
    function_id         uuid not null references functions(id) on delete cascade,
    client_id           uuid not null references clients(id) on delete cascade,
    old_baseline_seconds integer,
    new_baseline_seconds integer not null,
    methodology         text,
    sample_size         integer,
    confidence_level    text default 'medium',
    reason              text not null,                       -- why this was changed
    calibrated_by       uuid not null references user_profiles(id),
    calibrated_at       timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- 3. QUALITY METRICS
-- ----------------------------------------------------------------------------
-- Structured quality measurement. Currently only a free-text result_quality
-- string in the metrics table. This gives us: override rate, accuracy rate,
-- false positive rate, reviewer agreement — the "quality metrics" the JD asks for.

create table if not exists quality_reviews (
    id                  uuid primary key default uuid_generate_v4(),
    invocation_id       uuid not null,                       -- matches metrics.id
    audit_trail_id      uuid,                                -- matches audit_trail.id if override
    function_id         uuid not null references functions(id) on delete cascade,
    client_id           uuid not null references clients(id) on delete cascade,
    practice_group_id   uuid references practice_groups(id),
    reviewer_id         uuid not null references user_profiles(id),

    -- Quality classification
    accuracy            text not null,                       -- 'correct', 'minor_issues', 'major_issues', 'incorrect'
    false_positive      boolean not null default false,      -- was the AI flag incorrect?
    false_negative      boolean not null default false,      -- did the AI miss something?
    human_overrode      boolean not null default false,      -- did the reviewer change the AI output?
    override_reason     text,                                -- why they overrode (free-text)
    agreement_score     integer check (agreement_score between 0 and 100),  -- 0-100 reviewer agreement with AI

    -- Dimensions rated (flexible JSON for function-specific quality dimensions)
    dimension_scores    jsonb,                               -- e.g. {"clause_accuracy": 85, "risk_flagging": 90}

    reviewer_notes      text,
    review_time_ms      integer,                             -- how long the human spent reviewing
    created_at          timestamptz not null default now()
);

create index idx_quality_reviews_fn on quality_reviews(function_id, created_at);
create index idx_quality_reviews_client on quality_reviews(client_id, function_id);

-- Aggregated quality summary (materialized by a periodic job or on-demand)
create table if not exists quality_summaries (
    id                  uuid primary key default uuid_generate_v4(),
    function_id         uuid not null references functions(id) on delete cascade,
    client_id           uuid not null references clients(id) on delete cascade,
    period_start         date not null,
    period_end           date not null,

    total_reviews        integer not null default 0,
    correct_count        integer not null default 0,
    minor_issues_count   integer not null default 0,
    major_issues_count   integer not null default 0,
    incorrect_count      integer not null default 0,
    accuracy_rate        numeric(5,2),                       -- (correct + minor) / total × 100
    override_rate        numeric(5,2),                       -- human_overrode / total × 100
    false_positive_rate  numeric(5,2),
    false_negative_rate  numeric(5,2),
    avg_agreement_score  numeric(5,2),

    generated_at         timestamptz not null default now(),

    unique(function_id, client_id, period_start, period_end)
);

-- ----------------------------------------------------------------------------
-- 4. ADOPTION TRACKING
-- ----------------------------------------------------------------------------
-- Adoption rate = active users / eligible users. Without the denominator,
-- "50 lawyers used it" is meaningless.

create table if not exists eligible_users (
    id                  uuid primary key default uuid_generate_v4(),
    client_id           uuid not null references clients(id) on delete cascade,
    practice_group_id   uuid references practice_groups(id) on delete cascade,
    user_id             uuid not null references user_profiles(id) on delete cascade,
    function_id         uuid,                                -- null = eligible for all functions
    eligible_since      date not null default current_date,
    eligible_until      date,                                -- null = currently eligible
    created_by          uuid not null references user_profiles(id),
    created_at          timestamptz not null default now(),

    unique(user_id, function_id, practice_group_id)
);

-- Adoption snapshots (computed periodically for trend analysis)
create table if not exists adoption_snapshots (
    id                  uuid primary key default uuid_generate_v4(),
    client_id           uuid not null references clients(id) on delete cascade,
    practice_group_id   uuid references practice_groups(id),
    function_id         uuid references functions(id),
    snapshot_date       date not null,
    eligible_count      integer not null,
    active_count        integer not null,                    -- at least 1 invocation in prior 30 days
    adoption_pct        numeric(5,2) not null,
    created_at          timestamptz not null default now(),

    unique(client_id, practice_group_id, function_id, snapshot_date)
);
