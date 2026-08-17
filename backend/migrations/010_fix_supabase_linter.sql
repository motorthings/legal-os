-- ============================================================================
-- Legal AI OS — Supabase Linter Fixes (Migration 010)
-- ============================================================================
-- Fixes all ERROR and WARN-level Supabase security linter findings.
--
-- Error fixes:
--   1. SECURITY DEFINER views → SECURITY INVOKER (4 views)
--   2. RLS enabled on 8 public tables + 3 tables with RLS but no policies
--
-- Warning fixes:
--   3. Function search_path set explicitly (3 functions)
--   4. Service role RLS policies scoped properly (7 tables)
--   5. anon EXECUTE revoked from SECURITY DEFINER functions (3 functions)
--
-- Not fixed here (requires dashboard or carries migration risk):
--   - Extension "vector" in public schema (WARN) — move would break dependent columns
--   - Leaked password protection (WARN) — enable in Supabase Auth dashboard
-- ============================================================================

begin;

-- ============================================================================
-- 1. SECURITY DEFINER VIEWS → SECURITY INVOKER
-- ============================================================================
-- These views were created with SECURITY DEFINER, which means they enforce
-- the view creator's permissions rather than the querying user's RLS policies.
-- Recreating them as SECURITY INVOKER (the default) fixes this.

-- metrics_monthly_rollup (from 001_core_schema.sql)
drop view if exists metrics_monthly_rollup;
create or replace view metrics_monthly_rollup with (security_invoker = true) as
select
    client_id,
    function_id,
    date_trunc('month', created_at) as month,
    count(*) as invocations,
    sum(total_tokens) as total_tokens,
    sum(cost_usd) as total_cost_usd,
    sum(time_saved_ms) / 3600000.0 as hours_saved,
    avg(processing_time_ms) as avg_processing_ms,
    avg(confidence) as avg_confidence
from metrics
group by client_id, function_id, date_trunc('month', created_at);

-- client_summary (from 001_core_schema.sql)
drop view if exists client_summary;
create or replace view client_summary with (security_invoker = true) as
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

-- dd_project_report (from 002_due_diligence.sql)
drop view if exists dd_project_report;
create or replace view dd_project_report with (security_invoker = true) as
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

-- regulatory_alerts (from 003_regulatory_monitor.sql)
drop view if exists regulatory_alerts;
create or replace view regulatory_alerts with (security_invoker = true) as
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

-- ============================================================================
-- 2. RLS ENABLED ON UNPROTECTED PUBLIC TABLES
-- ============================================================================

-- 2a. rate_cards (006_roi_framework.sql)
alter table rate_cards enable row level security;
create policy "Users can read rate cards in their client"
    on rate_cards for select
    using (client_id = current_user_client_id());
create policy "Users can insert rate cards in their client"
    on rate_cards for insert
    with check (client_id = current_user_client_id());
create policy "Users can update rate cards in their client"
    on rate_cards for update
    using (client_id = current_user_client_id());

-- 2b. baseline_calibrations (006_roi_framework.sql)
alter table baseline_calibrations enable row level security;
create policy "Users can read baseline calibrations in their client"
    on baseline_calibrations for select
    using (client_id = current_user_client_id());
create policy "Users can insert baseline calibrations in their client"
    on baseline_calibrations for insert
    with check (client_id = current_user_client_id());

-- 2c. quality_reviews (006_roi_framework.sql)
alter table quality_reviews enable row level security;
create policy "Users can read quality reviews in their client"
    on quality_reviews for select
    using (client_id = current_user_client_id());
create policy "Users can insert quality reviews in their client"
    on quality_reviews for insert
    with check (client_id = current_user_client_id());
create policy "Users can update quality reviews in their client"
    on quality_reviews for update
    using (client_id = current_user_client_id());

-- 2d. quality_summaries (006_roi_framework.sql)
alter table quality_summaries enable row level security;
create policy "Users can read quality summaries in their client"
    on quality_summaries for select
    using (client_id = current_user_client_id());
create policy "Users can insert quality summaries in their client"
    on quality_summaries for insert
    with check (client_id = current_user_client_id());

-- 2e. eligible_users (006_roi_framework.sql)
alter table eligible_users enable row level security;
create policy "Users can read eligible users in their client"
    on eligible_users for select
    using (client_id = current_user_client_id());
create policy "Users can insert eligible users in their client"
    on eligible_users for insert
    with check (client_id = current_user_client_id());
create policy "Users can update eligible users in their client"
    on eligible_users for update
    using (client_id = current_user_client_id());
create policy "Users can delete eligible users in their client"
    on eligible_users for delete
    using (client_id = current_user_client_id());

-- 2f. adoption_snapshots (006_roi_framework.sql)
alter table adoption_snapshots enable row level security;
create policy "Users can read adoption snapshots in their client"
    on adoption_snapshots for select
    using (client_id = current_user_client_id());
create policy "Users can insert adoption snapshots in their client"
    on adoption_snapshots for insert
    with check (client_id = current_user_client_id());

-- 2g. poc_projects (007_poc_pipeline.sql)
alter table poc_projects enable row level security;
create policy "Users can read POC projects in their client"
    on poc_projects for select
    using (client_id = current_user_client_id());
create policy "Users can insert POC projects in their client"
    on poc_projects for insert
    with check (client_id = current_user_client_id());
create policy "Users can update POC projects in their client"
    on poc_projects for update
    using (client_id = current_user_client_id());

-- 2h. poc_feedback (007_poc_pipeline.sql) — scoped via poc_projects join
alter table poc_feedback enable row level security;
create policy "Users can read POC feedback in their client"
    on poc_feedback for select
    using (
        poc_project_id in (
            select id from poc_projects where client_id = current_user_client_id()
        )
    );
create policy "Users can insert POC feedback in their client"
    on poc_feedback for insert
    with check (
        poc_project_id in (
            select id from poc_projects where client_id = current_user_client_id()
        )
    );

-- ============================================================================
-- 3. RLS POLICIES FOR TABLES WITH RLS ENABLED BUT NO POLICIES
-- ============================================================================

-- 3a. function_configs (001_core_schema.sql — RLS enabled, no policies)
create policy "Users can read function configs in their client"
    on function_configs for select
    using (client_id = current_user_client_id());
create policy "Users can insert function configs in their client"
    on function_configs for insert
    with check (client_id = current_user_client_id());
create policy "Users can update function configs in their client"
    on function_configs for update
    using (client_id = current_user_client_id());

-- 3b. time_saved_baselines (001_core_schema.sql — RLS enabled, no policies)
-- Client-specific rows are scoped; global defaults (client_id null) are readable by all
create policy "Users can read time saved baselines"
    on time_saved_baselines for select
    using (
        client_id = current_user_client_id()
        or client_id is null  -- global defaults visible to all
    );
create policy "Users can insert time saved baselines in their client"
    on time_saved_baselines for insert
    with check (client_id = current_user_client_id());
create policy "Users can update time saved baselines in their client"
    on time_saved_baselines for update
    using (client_id = current_user_client_id());

-- 3c. maturity_assessments (008_maturity_assessment.sql — RLS enabled, no policies)
create policy "Users can read maturity assessments in their client"
    on maturity_assessments for select
    using (client_id = current_user_client_id());
create policy "Users can insert maturity assessments in their client"
    on maturity_assessments for insert
    with check (client_id = current_user_client_id());

-- ============================================================================
-- 4. FUNCTION search_path — explicit to prevent injection
-- ============================================================================

-- 4a. handle_new_user — trigger function, must run as SECURITY DEFINER to insert into user_profiles
--     Revoke direct execution; only the trigger should call it.
create or replace function handle_new_user()
returns trigger
set search_path = ''
language plpgsql
security definer
as $$
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
$$;

revoke execute on function handle_new_user() from anon, authenticated;

-- 4b. current_user_client_id — used by RLS policies, must stay SECURITY DEFINER
--     but should not be callable by anon.
create or replace function current_user_client_id()
returns uuid
set search_path = ''
language sql
stable
security definer
as $$
    select client_id from public.user_profiles where id = auth.uid();
$$;

revoke execute on function current_user_client_id() from anon;

-- 4c. current_user_practice_groups — used by RLS policies, must stay SECURITY DEFINER
--     but should not be callable by anon.
create or replace function current_user_practice_groups()
returns uuid[]
set search_path = ''
language sql
stable
security definer
as $$
    select practice_group_ids from public.user_profiles where id = auth.uid();
$$;

revoke execute on function current_user_practice_groups() from anon;

-- ============================================================================
-- 5. SERVICE ROLE RLS POLICIES — replace USING (true) with proper scoping
-- ============================================================================
-- The old policies granted ALL roles (anon/authenticated/service_role) full
-- access via USING (true). Service role already bypasses RLS, so these policies
-- were effectively granting public access. Drop them and add TO service_role
-- versions (self-documenting, though redundant since service_role bypasses RLS).

-- 5a. harvey_agents
drop policy if exists "Service role full access on harvey_agents" on harvey_agents;
create policy "Service role full access on harvey_agents"
    on harvey_agents for all
    to service_role
    using (true)
    with check (true);

-- 5b. harvey_evaluations
drop policy if exists "Service role full access on harvey_evaluations" on harvey_evaluations;
create policy "Service role full access on harvey_evaluations"
    on harvey_evaluations for all
    to service_role
    using (true)
    with check (true);

-- 5c. harvey_drift_alerts
drop policy if exists "Service role full access on harvey_drift_alerts" on harvey_drift_alerts;
create policy "Service role full access on harvey_drift_alerts"
    on harvey_drift_alerts for all
    to service_role
    using (true)
    with check (true);

-- 5d. help_documents
drop policy if exists "Service role full access on help_documents" on help_documents;
create policy "Service role full access on help_documents"
    on help_documents for all
    to service_role
    using (true)
    with check (true);

-- 5e. help_chunks
drop policy if exists "Service role full access on help_chunks" on help_chunks;
create policy "Service role full access on help_chunks"
    on help_chunks for all
    to service_role
    using (true)
    with check (true);

-- 5f. help_conversations
drop policy if exists "Service role full access on help_conversations" on help_conversations;
create policy "Service role full access on help_conversations"
    on help_conversations for all
    to service_role
    using (true)
    with check (true);

-- 5g. help_messages
drop policy if exists "Service role full access on help_messages" on help_messages;
create policy "Service role full access on help_messages"
    on help_messages for all
    to service_role
    using (true)
    with check (true);

commit;

-- ============================================================================
-- MANUAL FOLLOW-UP (dashboard-only changes)
-- ============================================================================
-- 1. Leaked password protection: enable in Supabase Dashboard →
--    Authentication → Settings → Password Strength
-- 2. Extension "vector" in public schema: cannot be moved without breaking
--    dependent vector columns on knowledge_documents and dd_documents.
--    Acceptable as WARN — vector is a trusted pgvector extension, and the
--    risk is low since no SQL injection paths reference it directly.
-- ============================================================================
