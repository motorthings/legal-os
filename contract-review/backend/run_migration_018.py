#!/usr/bin/env python3
"""Apply database migration 018 - Fix storage calculation for external sources"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Read migration file
migration_file = "migrations/018_fix_storage_external_sources.sql"
with open(migration_file, 'r') as f:
    sql = f.read()

print(f"📊 Applying migration: {migration_file}")
print("=" * 80)
print("This migration will:")
print("  1. Fix the storage trigger to exclude Google Drive and Notion documents")
print("  2. Recalculate all user storage_used values correctly")
print("=" * 80)

# Try using psycopg2 for direct database connection
try:
    import psycopg2
    from urllib.parse import urlparse

    # Get database URL from environment (Supabase provides this)
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")

    if not db_url:
        print("❌ No DATABASE_URL found. Please run this SQL manually in Supabase SQL Editor:")
        print(f"\n{sql}\n")
        sys.exit(1)

    print("\n🔄 Connecting to database...")

    # Connect to database
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    print("✅ Connected successfully")
    print("\n🔄 Executing migration SQL...")

    # Execute the entire SQL as one transaction
    cur.execute(sql)
    conn.commit()

    print("✅ Migration executed successfully!")

    cur.close()
    conn.close()

    print("\n" + "=" * 80)
    print("✅ Migration 018 applied successfully!")
    print("   Storage calculations have been fixed and recalculated for all users.")
    print("=" * 80)

except ImportError:
    print("⚠️  psycopg2 not available. Please apply this SQL manually in Supabase SQL Editor:")
    print(f"\n{sql}\n")
    print("=" * 80)
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nPlease apply this SQL manually in Supabase SQL Editor:")
    print(f"\n{sql}\n")
    print("=" * 80)
    sys.exit(1)
