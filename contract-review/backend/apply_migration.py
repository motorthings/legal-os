#!/usr/bin/env python3
"""Apply database migration"""
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Read migration file
migration_file = "migrations/007_add_organization_and_system_instructions.sql"
with open(migration_file, 'r') as f:
    sql = f.read()

print(f"📊 Applying migration: {migration_file}")
print("=" * 60)

try:
    # Execute the migration SQL
    result = supabase.rpc('exec_sql', {'sql': sql}).execute()
    print("✅ Migration applied successfully!")
except Exception as e:
    # Try alternative method - using postgrest directly
    print(f"⚠️  Direct RPC failed, trying alternative method...")
    print(f"Error was: {str(e)}")
    print("\nPlease apply this migration manually in Supabase SQL Editor:")
    print(f"\n{sql}\n")
    print("=" * 60)
