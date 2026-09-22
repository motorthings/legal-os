-- ============================================================================
-- Legal AI OS — Security Advisor Fixes, Round 2 (Migration 020)
-- ============================================================================
-- Clears the WARN-level findings that 010_fix_supabase_linter.sql left behind.
--
-- Why 010 did not finish the job: it revoked EXECUTE from `anon` on the RLS
-- helpers but never revoked the default PUBLIC grant, and every role inherits
-- EXECUTE from PUBLIC. Revoking from a named role alone therefore removed
-- nothing, and the advisor kept reporting all three functions.
--
-- The two grants are independent. Supabase's default privileges create an
-- EXPLICIT grant per function for anon, authenticated and service_role, on top
-- of the PUBLIC default. So revoking from PUBLIC strips `anon` (which had no
-- explicit grant after 010) while `authenticated` keeps working. Verified
-- against the live database before this file was applied.
--
-- Fixed here:
--   1. set_updated_at                — search_path pinned; 010 never covered it
--   2. handle_new_user               — default PUBLIC grant revoked
--   3. current_user_client_id        — PUBLIC + anon revoked, authenticated kept
--   4. current_user_practice_groups  — same
--   5. vector                        — public -> extensions schema
--   6. match_help_chunks             — search_path re-pinned; the move breaks it
--
-- Accepted and documented, not fixed:
--
--   a. current_user_client_id / current_user_practice_groups stay executable
--      by `authenticated` (advisor lint 0029, 2 findings).
--      They must stay SECURITY DEFINER: both read public.user_profiles, whose
--      own SELECT policy calls current_user_client_id(), so a SECURITY INVOKER
--      version recurses through that policy forever. All 56 policies that call
--      them are evaluated as `authenticated`, so that role needs EXECUTE.
--      Each returns only the caller's own client_id / practice_group_ids,
--      keyed on auth.uid(), so the residual surface discloses nothing. The
--      alternative — moving both into a non-exposed `private` schema — clears
--      these two warnings but requires regenerating all 56 tenancy policies.
--
--   b. auth_leaked_password_protection (1 finding).
--      HaveIBeenPwned checking is Pro-plan only. This project's org is on the
--      free plan and the Management API returns 402 Payment Required. It is a
--      billing change, not a SQL one.
--
-- Note on 001_core_schema.sql:16 — it still runs a bare
-- `create extension if not exists vector;`, so a fresh bootstrap installs to
-- public and this migration moves it again. That is deliberate. Editing an
-- applied migration would make an already-migrated database differ from a
-- freshly built one.
-- ============================================================================

begin;

-- ============================================================================
-- 1. set_updated_at — trigger function for public.firms and public.runs
-- ============================================================================
-- The body is `new.updated_at = now();` and nothing else. now() lives in
-- pg_catalog, which is searched implicitly ahead of any explicit search_path,
-- so pinning to empty cannot break it. Never callable via RPC.

alter function public.set_updated_at() set search_path = '';
revoke execute on function public.set_updated_at() from public, anon, authenticated;

-- ============================================================================
-- 2. handle_new_user — AFTER INSERT trigger on auth.users
-- ============================================================================
-- Trigger-only. Postgres checks EXECUTE when a trigger is created, not when it
-- fires, so revoking costs nothing. 010 had already revoked anon and
-- authenticated; the surviving PUBLIC grant is what kept the advisor
-- reporting it.

revoke execute on function public.handle_new_user() from public, anon, authenticated;

-- ============================================================================
-- 3 & 4. current_user_client_id / current_user_practice_groups
-- ============================================================================
-- Revoke PUBLIC and anon. `authenticated` keeps its explicit grant and
-- service_role is untouched, because every RLS policy on the 26 tenant tables
-- is evaluated as one of those two roles.

revoke execute on function public.current_user_client_id() from public, anon;
revoke execute on function public.current_user_practice_groups() from public, anon;

-- ============================================================================
-- 5. match_help_chunks — re-pin BEFORE the extension moves
-- ============================================================================
-- The body computes `hc.embedding <=> query_embedding`. PostgreSQL resolves
-- operators through search_path, not through the operand's type, so a bare
-- `<=>` needs the schema holding the operator on the path. The existing pin is
-- `search_path = public` alone, which stops resolving the moment vector leaves
-- public. Repin first so the function is never briefly broken.

alter function public.match_help_chunks(vector, double precision, integer, text[])
    set search_path to 'public', 'extensions';

-- ============================================================================
-- 6. vector — public -> extensions
-- ============================================================================
-- Column types and the three ivfflat indexes survive untouched: a column's
-- type is stored as an OID, and moving the extension changes the namespace but
-- not the OID. Only unqualified operator and opclass references are affected,
-- and both paths that issue them already carry `extensions` on their
-- search_path:
--   - the asyncpg pool in backend/app/database.py connects as `postgres`,
--     whose role-level search_path is "$user", public, extensions
--   - PostgREST resolves through Supabase's db-extra-search-path

alter extension vector set schema extensions;

-- Have PostgREST rebuild its schema cache against the new layout.
notify pgrst, 'reload schema';

commit;

-- ============================================================================
-- VERIFY AFTER APPLYING
-- ============================================================================
--   select has_function_privilege('anon','public.current_user_client_id()','EXECUTE');           -- false
--   select has_function_privilege('authenticated','public.current_user_client_id()','EXECUTE');  -- true
--   select extnamespace::regnamespace from pg_extension where extname = 'vector';                -- extensions
--   select proconfig from pg_proc where proname = 'set_updated_at';                              -- {search_path=""}
--
-- Then exercise the semantic-search path, because backend/app/api/routes/km.py
-- swallows its own errors and would degrade silently:
--   GET /api/km/search must still report "method": "semantic",
--   not "method": "text_fallback".
-- ============================================================================
