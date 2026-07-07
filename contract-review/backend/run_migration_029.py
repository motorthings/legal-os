#!/usr/bin/env python3
"""Apply database migration 029 - Contract Analysis System"""
import os
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
DB_PASSWORD = "SBPQxRHSy8OMOttZ"

if not SUPABASE_URL:
    print("❌ Error: SUPABASE_URL must be set")
    exit(1)

# Extract database connection details
DB_HOST = "db.iyugbpnxfbhqjxrvmnij.supabase.co"
DB_PORT = "5432"
DB_NAME = "postgres"
DB_USER = "postgres"

print("=" * 60)
print("📋 Applying Migration 029: Contract Analysis System")
print("=" * 60)
print()

# Set PostgreSQL password environment variable
env = os.environ.copy()
env['PGPASSWORD'] = DB_PASSWORD

try:
    # Apply migration using psql
    subprocess.run([
        'psql',
        '-h', DB_HOST,
        '-p', DB_PORT,
        '-U', DB_USER,
        '-d', DB_NAME,
        '-f', 'migrations/029_contract_analyses_table.sql'
    ], env=env, check=True)

    print()
    print("✅ Migration 029 applied successfully!")
    print()
    print("Created:")
    print("  - contract_analyses table")
    print("  - 6 performance indexes")
    print("  - updated_at trigger")
    print("  - get_contract_stats() function")
    print("  - RLS policies (admin + user)")
    print()

except subprocess.CalledProcessError as e:
    print(f"❌ Error applying migration: {e}")
    exit(1)
except FileNotFoundError:
    print("❌ Error: psql command not found. Please install PostgreSQL client.")
    exit(1)
