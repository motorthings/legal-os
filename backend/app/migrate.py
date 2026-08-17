"""
Legal AI OS — Migration Runner

Applies SQL migration files against Supabase via the Supabase CLI's Management
API (``supabase db query --linked``). Idempotent — each migration runs once,
tracked in the ``_migrations`` table.

Run from the repo root: ``cd backend && python -m app.migrate``
Requires the Supabase CLI to be installed and linked to the project.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from app.database import get_supabase


def run_migrations(migrations_dir: str | None = None):
    if migrations_dir is None:
        migrations_dir = str(Path(__file__).parent.parent / "migrations")

    # Repo root (where supabase/ is linked)
    repo_root = str(Path(__file__).parent.parent.parent)

    supabase = get_supabase()

    try:
        applied_result = supabase.table("_migrations").select("filename").execute()
        applied = {r["filename"] for r in (applied_result.data or [])}
    except Exception:
        print("  ! Could not read _migrations — run the bootstrap first.")
        applied = set()

    migration_files = sorted(
        f for f in os.listdir(migrations_dir)
        if f.endswith(".sql") and not f.startswith("_")
    )

    for filename in migration_files:
        if filename in applied:
            print(f"  ✓ {filename} (already applied)")
            continue

        filepath = os.path.join(migrations_dir, filename)
        print(f"  → Applying {filename}...")
        result = subprocess.run(
            ["supabase", "db", "query", "--linked", "-f", filepath],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"  ✗ {filename} FAILED: {result.stderr or result.stdout}")
            raise SystemExit(1)

        supabase.table("_migrations").insert({"filename": filename}).execute()
        print(f"  ✓ {filename} applied")


if __name__ == "__main__":
    run_migrations()
