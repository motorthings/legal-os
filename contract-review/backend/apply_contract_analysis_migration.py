#!/usr/bin/env python3
"""Apply contract_analysis table migration using Supabase client"""
import os
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    exit(1)

print("=" * 70)
print("📋 Applying Migration: Contract Analysis System")
print("=" * 70)
print()

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Read migration SQL
with open('migrations/029_contract_analysis_system.sql', 'r') as f:
    migration_sql = f.read()

try:
    # Execute migration using raw SQL
    print("🔧 Creating contract_analysis table and related objects...")
    result = supabase.rpc('exec_sql', {'sql_query': migration_sql}).execute()

    print()
    print("✅ Migration applied successfully!")
    print()
    print("Created:")
    print("  ✓ contract_analysis table")
    print("  ✓ contract_chat_history table")
    print("  ✓ Performance indexes")
    print("  ✓ RLS policies")
    print("  ✓ get_contract_stats() function")
    print()
    print("🎉 Your contract review system is ready!")
    print()

except Exception as e:
    print(f"❌ Error applying migration: {e}")
    print()
    print("ℹ️  The Supabase client doesn't support direct SQL execution.")
    print("Let me try an alternative approach using PostgreSQL adapter...")

    # Alternative: Use PostgreSQL adapter
    try:
        import psycopg2
        from urllib.parse import urlparse

        # Parse DATABASE_URL
        DATABASE_URL = os.environ.get("DATABASE_URL")
        if not DATABASE_URL:
            DATABASE_URL = f"postgresql://postgres:{os.environ.get('SUPABASE_DB_PASSWORD', 'SBPQxRHSy8OMOttZ')}@db.iyugbpnxfbhqjxrvmnij.supabase.co:5432/postgres"

        print(f"🔌 Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        print("🔧 Executing migration SQL...")
        cursor.execute(migration_sql)
        conn.commit()

        cursor.close()
        conn.close()

        print()
        print("✅ Migration applied successfully!")
        print()
        print("Created:")
        print("  ✓ contract_analysis table")
        print("  ✓ contract_chat_history table")
        print("  ✓ Performance indexes")
        print("  ✓ RLS policies")
        print("  ✓ get_contract_stats() function")
        print()
        print("🎉 Your contract review system is ready!")
        print()

    except ImportError:
        print()
        print("❌ psycopg2 is not installed.")
        print()
        print("To apply the migration, please run:")
        print("  1. Install psycopg2: pip install psycopg2-binary")
        print("  2. Run this script again")
        print()
        exit(1)
    except Exception as e2:
        print(f"❌ Error with alternative approach: {e2}")
        exit(1)
