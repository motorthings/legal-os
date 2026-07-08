"""
Legal AI OS — Schema Validation Tests

Verify the core schema migration produces the expected tables, indexes, and policies.
Run against a test Supabase instance before deploying.
"""

import pytest


# ---------------------------------------------------------------------------
# These tests validate the schema design — they check that critical tables,
# columns, and RLS policies exist. Run against a real database.
#
#   DATABASE_URL=postgresql://... pytest tests/test_schema.py -v
# ---------------------------------------------------------------------------


EXPECTED_TABLES = [
    "clients",
    "practice_groups",
    "user_profiles",
    "matters",
    "functions",
    "function_configs",
    "time_saved_baselines",
    "audit_trail",
    "metrics",
    "legal_standards",
    "knowledge_documents",
    # Due diligence
    "dd_projects",
    "dd_target_standards",
    "dd_documents",
    "dd_deviations",
]

EXPECTED_ENUMS = [
    "matter_status",
    "billing_type",
    "function_status",
    "audit_event_type",
    "dd_project_status",
    "dd_document_status",
    "deviation_severity",
]

RLS_ENABLED_TABLES = [
    "clients",
    "practice_groups",
    "user_profiles",
    "matters",
    "function_configs",
    "time_saved_baselines",
    "audit_trail",
    "metrics",
    "legal_standards",
    "knowledge_documents",
    "functions",
    "dd_projects",
    "dd_target_standards",
    "dd_documents",
    "dd_deviations",
]

EXPECTED_INDEXES = [
    "idx_audit_client",
    "idx_audit_matter",
    "idx_audit_function",
    "idx_audit_event",
    "idx_audit_correlation",
    "idx_audit_created",
    "idx_metrics_client",
    "idx_metrics_function",
    "idx_metrics_matter",
    "idx_metrics_time",
    "idx_metrics_pg",
    "idx_kb_embedding",
    "idx_dd_project_client",
    "idx_dd_project_status",
    "idx_dd_doc_project",
    "idx_dd_doc_status",
    "idx_dd_dev_project",
    "idx_dd_dev_severity",
    "idx_dd_dev_group",
    "idx_dd_dev_document",
    "idx_dd_doc_embedding",
]

EXPECTED_VIEWS = [
    "metrics_monthly_rollup",
    "client_summary",
    "dd_project_report",
]


@pytest.mark.integration
class TestCoreSchema:
    """Validates the core schema (migration 001)."""

    async def test_all_tables_exist(self, db_pool):
        """Every expected table should exist."""
        async with db_pool.acquire() as conn:
            for table in EXPECTED_TABLES:
                row = await conn.fetchrow(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = $1)",
                    table,
                )
                assert row[0], f"Table '{table}' does not exist"

    async def test_all_enums_exist(self, db_pool):
        """Every expected enum type should exist."""
        async with db_pool.acquire() as conn:
            for enum in EXPECTED_ENUMS:
                row = await conn.fetchrow(
                    "SELECT EXISTS (SELECT FROM pg_type WHERE typname = $1)",
                    enum,
                )
                assert row[0], f"Enum '{enum}' does not exist"

    async def test_rls_enabled_on_all_tables(self, db_pool):
        """Every table with client data must have RLS enabled."""
        async with db_pool.acquire() as conn:
            for table in RLS_ENABLED_TABLES:
                row = await conn.fetchrow(
                    "SELECT relrowsecurity FROM pg_class "
                    "JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace "
                    "WHERE nspname = 'public' AND relname = $1",
                    table,
                )
                assert row is not None, f"Table '{table}' not found in pg_class"
                assert row[0], f"RLS NOT enabled on '{table}'"

    async def test_all_indexes_exist(self, db_pool):
        """Every expected index should exist."""
        async with db_pool.acquire() as conn:
            for index in EXPECTED_INDEXES:
                row = await conn.fetchrow(
                    "SELECT EXISTS (SELECT FROM pg_indexes WHERE indexname = $1)",
                    index,
                )
                assert row[0], f"Index '{index}' does not exist"

    async def test_all_views_exist(self, db_pool):
        """Every expected view should exist."""
        async with db_pool.acquire() as conn:
            for view in EXPECTED_VIEWS:
                row = await conn.fetchrow(
                    "SELECT EXISTS (SELECT FROM information_schema.views WHERE table_schema = 'public' AND table_name = $1)",
                    view,
                )
                assert row[0], f"View '{view}' does not exist"

    async def test_audit_trail_is_append_only(self, db_pool):
        """audit_trail table must have INSERT policy but no UPDATE/DELETE policies."""
        async with db_pool.acquire() as conn:
            # Check for UPDATE policy
            rows = await conn.fetch(
                "SELECT policyname FROM pg_policies "
                "WHERE tablename = 'audit_trail' AND cmd = 'UPDATE'"
            )
            assert len(rows) == 0, "audit_trail has UPDATE policy — should be immutable"

            # Check for DELETE policy
            rows = await conn.fetch(
                "SELECT policyname FROM pg_policies "
                "WHERE tablename = 'audit_trail' AND cmd = 'DELETE'"
            )
            assert len(rows) == 0, "audit_trail has DELETE policy — should be immutable"

    async def test_seed_functions_exist(self, db_pool):
        """All 8 functions should be seeded in the functions table."""
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT count(*) FROM functions")
            assert row[0] == 8, f"Expected 8 seeded functions, got {row[0]}"

    async def test_seed_baselines_exist(self, db_pool):
        """Time-saved baselines should be seeded for 6 functions."""
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT count(*) FROM time_saved_baselines WHERE client_id IS NULL")
            assert row[0] == 6, f"Expected 6 global baselines, got {row[0]}"


@pytest.mark.integration
class TestDueDiligenceSchema:
    """Validates the DD schema (migration 002)."""

    async def test_dd_tables_exist(self, db_pool):
        async with db_pool.acquire() as conn:
            for table in ["dd_projects", "dd_target_standards", "dd_documents", "dd_deviations"]:
                row = await conn.fetchrow(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = $1)",
                    table,
                )
                assert row[0], f"Table '{table}' does not exist"

    async def test_dd_project_report_view(self, db_pool):
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT EXISTS (SELECT FROM information_schema.views WHERE table_schema = 'public' AND table_name = 'dd_project_report')"
            )
            assert row[0], "dd_project_report view does not exist"
