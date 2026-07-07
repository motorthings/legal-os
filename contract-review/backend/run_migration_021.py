#!/usr/bin/env python3
"""Apply database migration 021 - Recalculate storage_used for all users"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Read migration file
migration_file = "migrations/021_recalculate_storage_used.sql"
with open(migration_file, 'r') as f:
    sql = f.read()

print(f"📊 Applying migration: {migration_file}")
print("=" * 80)
print("This migration will:")
print("  1. Recalculate all user storage_used values")
print("  2. Fix any negative or incorrect values caused by the double increment/decrement bug")
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
    print("✅ Migration 021 applied successfully!")
    print("   All user storage_used values have been recalculated correctly.")
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
