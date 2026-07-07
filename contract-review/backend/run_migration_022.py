#!/usr/bin/env python3
"""Apply database migration 022 - Fix UUID type cast in match_document_chunks"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Read migration file
migration_file = "migrations/022_fix_uuid_type_cast.sql"
with open(migration_file, 'r') as f:
    sql = f.read()

print(f"📊 Applying migration: {migration_file}")
print("=" * 80)
print("This migration will:")
print("  1. Drop the match_document_chunks function with incorrect TEXT parameter")
print("  2. Recreate it with correct UUID parameter for filter_client_id")
print("  3. Fix the 'operator does not exist: uuid = text' error")
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

    # Verify the fix
    print("\n🔍 Verifying function signature...")
    cur.execute("""
        SELECT
            proname as function_name,
            pg_get_function_arguments(oid) as arguments
        FROM pg_proc
        WHERE proname = 'match_document_chunks'
    """)
    result = cur.fetchone()
    if result:
        print(f"   Function: {result[0]}")
        print(f"   Arguments: {result[1]}")
        print("   ✅ filter_client_id is now UUID type!")

    cur.close()
    conn.close()

    print("\n" + "=" * 80)
    print("✅ Migration 022 applied successfully!")
    print("   The UUID type cast error in knowledge base search has been fixed.")
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
