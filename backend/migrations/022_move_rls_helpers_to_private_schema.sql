-- ============================================================================
-- Legal AI OS — Move RLS Helpers Out of the Exposed Schema (Migration 022)
-- ============================================================================
-- Clears the last two fixable security advisor findings:
--
--   authenticated_security_definer_function_executable (lint 0029, x2)
--     public.current_user_client_id()
--     public.current_user_practice_groups()
--
-- Both must stay SECURITY DEFINER. Each reads public.user_profiles, whose own
-- SELECT policy calls current_user_client_id(), so a SECURITY INVOKER version
-- would re-enter that policy forever. And both must stay executable by
-- `authenticated`, because every one of the 56 policies below is evaluated as
-- that role. Revoking was never an option.
--
-- What was optional is WHERE they live. The lint fires because the function is
-- reachable at /rest/v1/rpc/<name>, which is a PostgREST route into the
-- `public` schema. Supabase's exposed schema list is `public` and
-- `graphql_public`; a function in any other schema has no RPC route at all, so
-- the finding disappears while `authenticated` keeps the EXECUTE it needs.
--
-- The cost is that a policy expression stores the function's OID, resolved when
-- the policy is created. Moving the function therefore requires recreating
-- every policy that calls it. That is all 56 of them, across 26 tables.
--
-- The policy bodies below were GENERATED from pg_policies, not retyped. The
-- only edit applied was substituting `private.` for the bare function name.
-- Verified by diffing pg_policies before and after inside the same transaction;
-- the only acceptable difference is that substitution.
--
-- Deliberately NOT granted: USAGE on schema private to `anon`. Anonymous
-- requests already fail closed on these tables since 020 revoked the function
-- from that role, and keeping the schema shut means they keep failing closed.
-- ============================================================================

begin;

-- ============================================================================
-- 1. The schema. Not in PostgREST's exposed list, so nothing here is routable.
-- ============================================================================

create schema if not exists private;

revoke all on schema private from public, anon;
grant usage on schema private to authenticated, service_role;

-- ============================================================================
-- 2. The helpers, bodies unchanged from 010_fix_supabase_linter.sql
-- ============================================================================

create or replace function private.current_user_client_id()
returns uuid
set search_path = ''
language sql
stable
security definer
as $$
    select client_id from public.user_profiles where id = auth.uid();
$$;

create or replace function private.current_user_practice_groups()
returns uuid[]
set search_path = ''
language sql
stable
security definer
as $$
    select practice_group_ids from public.user_profiles where id = auth.uid();
$$;

-- A new function grants EXECUTE to PUBLIC by default. Revoke it before granting
-- the roles that actually need it.
revoke execute on function private.current_user_client_id() from public, anon;
revoke execute on function private.current_user_practice_groups() from public, anon;
grant execute on function private.current_user_client_id() to authenticated, service_role;
grant execute on function private.current_user_practice_groups() to authenticated, service_role;

-- ============================================================================
-- 3. Detach the 56 policies from the public helpers
-- ============================================================================
-- The drop has to come before the function drop: a policy holds a dependency on
-- the function it calls, and PostgreSQL refuses to drop a function that other
-- objects depend on.

-- 3a. drop
drop policy if exists "Users can insert adoption snapshots in their client" on public.adoption_snapshots;
drop policy if exists "Users can read adoption snapshots in their client" on public.adoption_snapshots;
drop policy if exists "Users can insert audit trail" on public.audit_trail;
drop policy if exists "Users can read audit trail in their client" on public.audit_trail;
drop policy if exists "Users can insert baseline calibrations in their client" on public.baseline_calibrations;
drop policy if exists "Users can read baseline calibrations in their client" on public.baseline_calibrations;
drop policy if exists "Users can read own client" on public.clients;
drop policy if exists "Users can read deviations in their client" on public.dd_deviations;
drop policy if exists "Users can update deviations (review decisions)" on public.dd_deviations;
drop policy if exists "Users can read DD documents in their client" on public.dd_documents;
drop policy if exists "Users can insert DD projects in their practice groups" on public.dd_projects;
drop policy if exists "Users can read DD projects in their practice groups" on public.dd_projects;
drop policy if exists "Users can update DD projects in their practice groups" on public.dd_projects;
drop policy if exists "Users can read target standards in their client" on public.dd_target_standards;
drop policy if exists "Users can delete eligible users in their client" on public.eligible_users;
drop policy if exists "Users can insert eligible users in their client" on public.eligible_users;
drop policy if exists "Users can read eligible users in their client" on public.eligible_users;
drop policy if exists "Users can update eligible users in their client" on public.eligible_users;
drop policy if exists "Users can insert function configs in their client" on public.function_configs;
drop policy if exists "Users can read function configs in their client" on public.function_configs;
drop policy if exists "Users can update function configs in their client" on public.function_configs;
drop policy if exists "Users can read knowledge docs in their practice groups" on public.knowledge_documents;
drop policy if exists "Users can insert research queries in their client" on public.legal_research_queries;
drop policy if exists "Users can read research queries in their client" on public.legal_research_queries;
drop policy if exists "Users can insert research results for their queries" on public.legal_research_results;
drop policy if exists "Users can read research results for their queries" on public.legal_research_results;
drop policy if exists "Users can insert standards in their client" on public.legal_standards;
drop policy if exists "Users can read standards in their client" on public.legal_standards;
drop policy if exists "Users can update standards in their client" on public.legal_standards;
drop policy if exists "Users can read flags in their client" on public.matter_regulatory_flags;
drop policy if exists "Users can update flags in their client" on public.matter_regulatory_flags;
drop policy if exists "Users can insert matters in their practice groups" on public.matters;
drop policy if exists "Users can read matters in their practice groups" on public.matters;
drop policy if exists "Users can update matters in their practice groups" on public.matters;
drop policy if exists "Users can insert maturity assessments in their client" on public.maturity_assessments;
drop policy if exists "Users can read maturity assessments in their client" on public.maturity_assessments;
drop policy if exists "System can insert metrics" on public.metrics;
drop policy if exists "Users can read metrics in their client" on public.metrics;
drop policy if exists "Users can insert POC feedback in their client" on public.poc_feedback;
drop policy if exists "Users can read POC feedback in their client" on public.poc_feedback;
drop policy if exists "Users can insert POC projects in their client" on public.poc_projects;
drop policy if exists "Users can read POC projects in their client" on public.poc_projects;
drop policy if exists "Users can update POC projects in their client" on public.poc_projects;
drop policy if exists "Users can read own client practice groups" on public.practice_groups;
drop policy if exists "Users can insert quality reviews in their client" on public.quality_reviews;
drop policy if exists "Users can read quality reviews in their client" on public.quality_reviews;
drop policy if exists "Users can update quality reviews in their client" on public.quality_reviews;
drop policy if exists "Users can insert quality summaries in their client" on public.quality_summaries;
drop policy if exists "Users can read quality summaries in their client" on public.quality_summaries;
drop policy if exists "Users can insert rate cards in their client" on public.rate_cards;
drop policy if exists "Users can read rate cards in their client" on public.rate_cards;
drop policy if exists "Users can update rate cards in their client" on public.rate_cards;
drop policy if exists "Users can insert time saved baselines in their client" on public.time_saved_baselines;
drop policy if exists "Users can read time saved baselines" on public.time_saved_baselines;
drop policy if exists "Users can update time saved baselines in their client" on public.time_saved_baselines;
drop policy if exists "Users can read profiles in their client" on public.user_profiles;

-- 3b. drop the public helpers
drop function if exists public.current_user_client_id();
drop function if exists public.current_user_practice_groups();

-- 3c. recreate, pointed at private.*
create policy "Users can insert adoption snapshots in their client" on public.adoption_snapshots for INSERT with check (client_id = private.current_user_client_id());
create policy "Users can read adoption snapshots in their client" on public.adoption_snapshots for SELECT using (client_id = private.current_user_client_id());
create policy "Users can insert audit trail" on public.audit_trail for INSERT with check (client_id = private.current_user_client_id());
create policy "Users can read audit trail in their client" on public.audit_trail for SELECT using (client_id = private.current_user_client_id());
create policy "Users can insert baseline calibrations in their client" on public.baseline_calibrations for INSERT with check (client_id = private.current_user_client_id());
create policy "Users can read baseline calibrations in their client" on public.baseline_calibrations for SELECT using (client_id = private.current_user_client_id());
create policy "Users can read own client" on public.clients for SELECT using (id = private.current_user_client_id());
create policy "Users can read deviations in their client" on public.dd_deviations for SELECT using (client_id = private.current_user_client_id());
create policy "Users can update deviations (review decisions)" on public.dd_deviations for UPDATE using (client_id = private.current_user_client_id());
create policy "Users can read DD documents in their client" on public.dd_documents for SELECT using (client_id = private.current_user_client_id());
create policy "Users can insert DD projects in their practice groups" on public.dd_projects for INSERT with check ((client_id = private.current_user_client_id()) AND (practice_group_id = ANY (private.current_user_practice_groups())));
create policy "Users can read DD projects in their practice groups" on public.dd_projects for SELECT using ((client_id = private.current_user_client_id()) AND (practice_group_id = ANY (private.current_user_practice_groups())));
create policy "Users can update DD projects in their practice groups" on public.dd_projects for UPDATE using ((client_id = private.current_user_client_id()) AND (practice_group_id = ANY (private.current_user_practice_groups())));
create policy "Users can read target standards in their client" on public.dd_target_standards for SELECT using (project_id IN ( SELECT dd_projects.id
   FROM dd_projects
  WHERE (dd_projects.client_id = private.current_user_client_id())));
create policy "Users can delete eligible users in their client" on public.eligible_users for DELETE using (client_id = private.current_user_client_id());
create policy "Users can insert eligible users in their client" on public.eligible_users for INSERT with check (client_id = private.current_user_client_id());
create policy "Users can read eligible users in their client" on public.eligible_users for SELECT using (client_id = private.current_user_client_id());
create policy "Users can update eligible users in their client" on public.eligible_users for UPDATE using (client_id = private.current_user_client_id());
create policy "Users can insert function configs in their client" on public.function_configs for INSERT with check (client_id = private.current_user_client_id());
create policy "Users can read function configs in their client" on public.function_configs for SELECT using (client_id = private.current_user_client_id());
create policy "Users can update function configs in their client" on public.function_configs for UPDATE using (client_id = private.current_user_client_id());
create policy "Users can read knowledge docs in their practice groups" on public.knowledge_documents for SELECT using ((client_id = private.current_user_client_id()) AND ((practice_group_id IS NULL) OR (practice_group_id = ANY (private.current_user_practice_groups()))));
create policy "Users can insert research queries in their client" on public.legal_research_queries for INSERT with check (client_id = private.current_user_client_id());
create policy "Users can read research queries in their client" on public.legal_research_queries for SELECT using (client_id = private.current_user_client_id());
create policy "Users can insert research results for their queries" on public.legal_research_results for INSERT with check (query_id IN ( SELECT legal_research_queries.id
   FROM legal_research_queries
  WHERE (legal_research_queries.client_id = private.current_user_client_id())));
create policy "Users can read research results for their queries" on public.legal_research_results for SELECT using (query_id IN ( SELECT legal_research_queries.id
   FROM legal_research_queries
  WHERE (legal_research_queries.client_id = private.current_user_client_id())));
create policy "Users can insert standards in their client" on public.legal_standards for INSERT with check (client_id = private.current_user_client_id());
create policy "Users can read standards in their client" on public.legal_standards for SELECT using (client_id = private.current_user_client_id());
create policy "Users can update standards in their client" on public.legal_standards for UPDATE using (client_id = private.current_user_client_id());
create policy "Users can read flags in their client" on public.matter_regulatory_flags for SELECT using (client_id = private.current_user_client_id());
create policy "Users can update flags in their client" on public.matter_regulatory_flags for UPDATE using (client_id = private.current_user_client_id());
create policy "Users can insert matters in their practice groups" on public.matters for INSERT with check ((client_id = private.current_user_client_id()) AND (practice_group_id = ANY (private.current_user_practice_groups())));
create policy "Users can read matters in their practice groups" on public.matters for SELECT using ((client_id = private.current_user_client_id()) AND (practice_group_id = ANY (private.current_user_practice_groups())));
create policy "Users can update matters in their practice groups" on public.matters for UPDATE using ((client_id = private.current_user_client_id()) AND (practice_group_id = ANY (private.current_user_practice_groups())));
create policy "Users can insert maturity assessments in their client" on public.maturity_assessments for INSERT with check (client_id = private.current_user_client_id());
create policy "Users can read maturity assessments in their client" on public.maturity_assessments for SELECT using (client_id = private.current_user_client_id());
create policy "System can insert metrics" on public.metrics for INSERT with check (client_id = private.current_user_client_id());
create policy "Users can read metrics in their client" on public.metrics for SELECT using (client_id = private.current_user_client_id());
create policy "Users can insert POC feedback in their client" on public.poc_feedback for INSERT with check (poc_project_id IN ( SELECT poc_projects.id
   FROM poc_projects
  WHERE (poc_projects.client_id = private.current_user_client_id())));
create policy "Users can read POC feedback in their client" on public.poc_feedback for SELECT using (poc_project_id IN ( SELECT poc_projects.id
   FROM poc_projects
  WHERE (poc_projects.client_id = private.current_user_client_id())));
create policy "Users can insert POC projects in their client" on public.poc_projects for INSERT with check (client_id = private.current_user_client_id());
create policy "Users can read POC projects in their client" on public.poc_projects for SELECT using (client_id = private.current_user_client_id());
create policy "Users can update POC projects in their client" on public.poc_projects for UPDATE using (client_id = private.current_user_client_id());
create policy "Users can read own client practice groups" on public.practice_groups for SELECT using (client_id = private.current_user_client_id());
create policy "Users can insert quality reviews in their client" on public.quality_reviews for INSERT with check (client_id = private.current_user_client_id());
create policy "Users can read quality reviews in their client" on public.quality_reviews for SELECT using (client_id = private.current_user_client_id());
create policy "Users can update quality reviews in their client" on public.quality_reviews for UPDATE using (client_id = private.current_user_client_id());
create policy "Users can insert quality summaries in their client" on public.quality_summaries for INSERT with check (client_id = private.current_user_client_id());
create policy "Users can read quality summaries in their client" on public.quality_summaries for SELECT using (client_id = private.current_user_client_id());
create policy "Users can insert rate cards in their client" on public.rate_cards for INSERT with check (client_id = private.current_user_client_id());
create policy "Users can read rate cards in their client" on public.rate_cards for SELECT using (client_id = private.current_user_client_id());
create policy "Users can update rate cards in their client" on public.rate_cards for UPDATE using (client_id = private.current_user_client_id());
create policy "Users can insert time saved baselines in their client" on public.time_saved_baselines for INSERT with check (client_id = private.current_user_client_id());
create policy "Users can read time saved baselines" on public.time_saved_baselines for SELECT using ((client_id = private.current_user_client_id()) OR (client_id IS NULL));
create policy "Users can update time saved baselines in their client" on public.time_saved_baselines for UPDATE using (client_id = private.current_user_client_id());
create policy "Users can read profiles in their client" on public.user_profiles for SELECT using (client_id = private.current_user_client_id());

-- Rebuild PostgREST's schema cache against the new function locations.
notify pgrst, 'reload schema';

commit;

-- ============================================================================
-- VERIFY AFTER APPLYING
-- ============================================================================
--   select count(*) from pg_proc p join pg_namespace n on n.oid = p.pronamespace
--    where n.nspname = 'public' and p.prosecdef;                       -- 0
--   select count(*) from pg_policies where schemaname = 'public'
--    and (qual like '%private.current_user%'
--      or with_check like '%private.current_user%');                   -- 56
--   select count(*) from pg_proc p join pg_namespace n on n.oid = p.pronamespace
--    where n.nspname = 'private';                                      -- 2
--
-- Then confirm a tenant query still scopes correctly. The advisor should drop
-- to a single WARN: auth_leaked_password_protection, which is Pro-plan only.
-- ============================================================================
