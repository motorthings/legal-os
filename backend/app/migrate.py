"""
Legal AI OS — Migration Runner

Applies SQL migration files from backend/migrations/ against Supabase PostgreSQL.
Idempotent — each migration runs once, tracked in a _migrations table.
"""

from __future__ import annotations

import os
from pathlib import Path

from app.database import get_supabase


def run_migrations(migrations_dir: str | None = None):
    """Apply all unapplied SQL migration files in order."""
    if migrations_dir is None:
        migrations_dir = str(Path(__file__).parent.parent / "migrations")

    supabase = get_supabase()

    # Ensure tracking table exists
    try:
        supabase.table("_migrations").select("filename").limit(1).execute()
    except Exception:
        # Create the tracking table via raw SQL
        supabase.rpc("create_migrations_table", {}).execute()
        # Fallback: try direct SQL
        pass

    # Get already applied migrations
    applied_result = supabase.table("_migrations").select("filename").execute()
    applied = {r["filename"] for r in (applied_result.data or [])}

    # Find and sort migration files
    migration_files = sorted(
        f for f in os.listdir(migrations_dir)
        if f.endswith(".sql") and not f.startswith("_")
    )

    for filename in migration_files:
        if filename in applied:
            print(f"  ✓ {filename} (already applied)")
            continue

        filepath = os.path.join(migrations_dir, filename)
        with open(filepath) as f:
            sql = f.read()

        print(f"  → Applying {filename}...")
        try:
            # Execute via Supabase SQL API
            result = supabase.rpc("exec_sql", {"query": sql}).execute()
            # Track as applied
            supabase.table("_migrations").insert({
                "filename": filename,
                "applied_at": "now()",
            }).execute()
            print(f"  ✓ {filename} applied successfully")
        except Exception as e:
            print(f"  ✗ {filename} FAILED: {e}")
            raise


if __name__ == "__main__":
    run_migrations()
