#!/usr/bin/env python3
"""Apply migration 025 - Add approval fields to interview_extractions"""
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY) must be set")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Read migration file
migration_file = "migrations/025_add_approval_fields_to_extractions.sql"
with open(migration_file, 'r') as f:
    sql = f.read()

print(f"📊 Applying migration: {migration_file}")
print("=" * 60)
print("This migration adds approved_at and approved_by columns to interview_extractions table")
print("=" * 60)

try:
    # Try to execute via RPC
    result = supabase.rpc('exec_sql', {'sql': sql}).execute()
    print("✅ Migration applied successfully via RPC!")
except Exception as e:
    print(f"⚠️  RPC method failed: {str(e)}")
    print("\n" + "=" * 60)
    print("Please apply this migration manually in Supabase SQL Editor:")
    print("1. Go to your Supabase dashboard")
    print("2. Navigate to SQL Editor")
    print("3. Create a new query and paste the following SQL:")
    print("=" * 60)
    print(f"\n{sql}\n")
    print("=" * 60)
    print("4. Run the query")
    print("=" * 60)
