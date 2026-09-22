-- ============================================================================
-- Legal AI OS — Security Advisor Fixes, Round 3 (Migration 021)
-- ============================================================================
-- Clears the two ERROR-level findings that 010 and 020 left standing.
--
--   1. matter_research_summary — SECURITY DEFINER view (lint 0010)
--   2. _migrations             — RLS disabled in an exposed schema (lint 0013)
--
-- Both were found by re-running the advisor after 020, not by reading the
-- round-1 list: neither appeared in it.
-- ============================================================================

begin;

-- ============================================================================
-- 1. matter_research_summary — SECURITY DEFINER view
-- ============================================================================
-- The view is owned by `postgres`, which also owns legal_research_queries and
-- legal_research_results, and neither table has FORCE ROW LEVEL SECURITY set.
-- A view without `security_invoker` therefore executes as its owner, and the
-- owner is exempt from RLS on tables it owns. So the view bypassed row-level
-- security completely: it aggregated across every client with no tenant filter.
--
-- It was additionally SELECT-granted to `anon` and `authenticated`, which made
-- it reachable at GET /rest/v1/matter_research_summary with nothing more than
-- the public anon key. One client and one row existed when this was written, so
-- nothing had actually leaked. A second client would have been a live
-- cross-tenant data exposure, and this repo's stated position is that RLS at
-- the database is the governance enforcement point, not a policy document.
--
-- `security_invoker = true` makes the view run as the querying user, so the
-- tenant policies on the underlying tables apply. The application reads this
-- view through the service-role client (backend/app/api/routes/legal_research.py),
-- and service_role bypasses RLS, so its results are unchanged.
--
-- 010 converted four views to security_invoker. This is the fifth; it was
-- created in 003_legal_research.sql and the round-1 list did not reach it.

alter view public.matter_research_summary set (security_invoker = true);

-- Revoke the PostgREST surface outright. Nothing but the service-role client
-- reads this view, so the grant buys nothing and the policies would otherwise
-- be the only thing standing between an anon key and the aggregate.

revoke all on public.matter_research_summary from anon, authenticated;

-- ============================================================================
-- 2. _migrations — RLS disabled in an exposed schema
-- ============================================================================
-- The migration ledger created by backend/app/migrate.py. It sits in `public`,
-- which PostgREST exposes, with RLS off and no policies.
--
-- Enabling RLS with no policy is deny-all: no role except the owner and
-- service_role can read it. That is the intended end state, not an oversight.
-- The runner reads it through get_supabase() (backend/app/database.py), which
-- uses the service-role key and bypasses RLS, so applying migrations still
-- works. This will report as an INFO-level rls_enabled_no_policy finding
-- afterwards, the same as public.descrybe_connections.

alter table public._migrations enable row level security;

commit;

-- ============================================================================
-- VERIFY AFTER APPLYING
-- ============================================================================
--   select reloptions from pg_class where relname = 'matter_research_summary';
--     -- {security_invoker=true}
--   select relrowsecurity from pg_class where relname = '_migrations';
--     -- true
--   select has_table_privilege('anon','public.matter_research_summary','SELECT');
--     -- false
--   select count(*) from public.matter_research_summary;
--     -- unchanged; the service-role path still reads it
-- ============================================================================
