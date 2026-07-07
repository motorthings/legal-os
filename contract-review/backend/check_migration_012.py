#!/usr/bin/env python3
"""Check if migration 012 has been applied"""
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_KEY")
)

print("\n🔍 Checking if migration 012 has been applied...\n")

try:
    # Try to query a record with the new columns
    result = supabase.table('google_drive_tokens')\
        .select('sync_frequency, last_auto_sync, next_sync_scheduled, default_folder_id, default_folder_name')\
        .limit(1)\
        .execute()

    print("✅ Migration 012 is ALREADY APPLIED!")
    print("\nColumns found:")
    print("  • sync_frequency")
    print("  • last_auto_sync")
    print("  • next_sync_scheduled")
    print("  • default_folder_id")
    print("  • default_folder_name")
    print("\n✨ You're ready to use the sync cadence feature!\n")

except Exception as e:
    error_msg = str(e).lower()
    if 'column' in error_msg or 'does not exist' in error_msg:
        print("❌ Migration 012 is NOT applied yet")
        print(f"\nError: {e}")
        print("\n📋 You need to apply migration 012 via Supabase SQL Editor:")
        print("   1. Go to https://app.supabase.com → Your project")
        print("   2. Click 'SQL Editor'")
        print("   3. Copy/paste: backend/migrations/012_google_drive_sync_cadence.sql")
        print("   4. Click 'Run'\n")
    else:
        print(f"❓ Unexpected error: {e}\n")
