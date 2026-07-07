#!/usr/bin/env python3
"""Apply migration 029 using Supabase client"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

print("=" * 60)
print("📋 Applying Migration 029: Contract Analysis System")
print("=" * 60)
print()

# Read migration file
with open('migrations/029_contract_analysis_system.sql', 'r') as f:
    migration_sql = f.read()

try:
    # Execute migration SQL
    # Note: Supabase Python client doesn't directly support raw SQL execution
    # We need to use the REST API
    print("⚠️  Note: This migration must be applied via Supabase Dashboard SQL Editor")
    print()
    print("Please copy the SQL from migrations/029_contract_analysis_system.sql")
    print("and run it in the Supabase Dashboard SQL Editor:")
    print()
    print(f"  1. Go to: {SUPABASE_URL.replace('https://', 'https://supabase.com/dashboard/project/')}/sql")
    print("  2. Paste the migration SQL")
    print("  3. Click 'Run'")
    print()
    print("SQL Preview (first 500 chars):")
    print("-" * 60)
    print(migration_sql[:500])
    print("...")
    print("-" * 60)

except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
