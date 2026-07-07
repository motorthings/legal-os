#!/usr/bin/env python3
"""Apply migration 037: Add feedback count to stats"""
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ Error: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Read migration file
migration_file = "migrations/037_add_feedback_count_to_stats.sql"
with open(migration_file, 'r') as f:
    sql = f.read()

print(f"📊 Applying migration: {migration_file}")
print("=" * 60)

try:
    # Execute the migration SQL directly
    result = supabase.postgrest.rpc('exec_sql', {'sql': sql}).execute()
    print("✅ Migration applied successfully!")
except Exception as e:
    print(f"⚠️  Trying direct SQL execution...")
    print(f"First error: {str(e)}")

    # Try executing directly via psql if available
    import subprocess
    try:
        # Use environment variables for connection
        env = os.environ.copy()
        result = subprocess.run(
            ['psql', '-h', 'db.kwxngptwzllzlifpwvns.supabase.co', '-p', '5432', '-U', 'postgres', '-d', 'postgres', '-f', migration_file],
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("✅ Migration applied successfully via psql!")
            print(result.stdout)
        else:
            print("❌ Migration failed:")
            print(result.stderr)
    except Exception as e2:
        print(f"❌ Could not run migration: {str(e2)}")
        print("\nPlease apply this migration manually in Supabase SQL Editor:")
        print(f"\n{sql}\n")
        print("=" * 60)
