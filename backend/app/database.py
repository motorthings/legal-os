"""
Legal AI OS — Database Service

Singleton Supabase client + asyncpg connection pool for direct SQL.
Supabase client: CRUD operations, Storage, Auth.
asyncpg pool: pgvector queries, complex aggregations, migrations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from supabase import Client, create_client

from app.config import settings

if TYPE_CHECKING:
    import asyncpg

# ---------------------------------------------------------------------------
# Supabase client (singleton)
# ---------------------------------------------------------------------------

_supabase: Client | None = None


def get_supabase() -> Client:
    """Return singleton Supabase client (service_role — bypasses RLS)."""
    global _supabase
    if _supabase is None:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set"
            )
        _supabase = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )
    return _supabase


def get_supabase_anon() -> Client:
    """Return Supabase client with anon key (respects RLS — for user-facing calls)."""
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_ANON_KEY must be set"
        )
    return create_client(settings.supabase_url, settings.supabase_anon_key)


# ---------------------------------------------------------------------------
# asyncpg pool (for pgvector, raw SQL, migrations)
# ---------------------------------------------------------------------------

_pool = None  # type: ignore


async def get_pool():
    """Return singleton asyncpg connection pool (lazy import)."""
    global _pool
    if _pool is None:
        import asyncpg
        if not settings.database_url:
            raise ValueError("DATABASE_URL must be set for direct PostgreSQL access")
        _pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=2,
            max_size=20,
            command_timeout=30,
        )
    return _pool


async def close_pool() -> None:
    """Close the asyncpg pool (called on shutdown)."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
