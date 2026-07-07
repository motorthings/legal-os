#!/usr/bin/env python3
"""Check oauth_states table structure"""
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_KEY")
)

print("\n🔍 Checking oauth_states table structure...\n")

try:
    # Try to query the table
    result = supabase.table('oauth_states').select('*').limit(1).execute()

    if result.data:
        print("✅ oauth_states table exists!")
        print(f"\nSample record columns:")
        for key in result.data[0].keys():
            print(f"  • {key}")
    else:
        print("✅ oauth_states table exists but is empty")
        print("\nTo see column structure, let me try a different approach...")

        # Try inserting and immediately deleting to see error structure
        try:
            test_result = supabase.table('oauth_states').select('*').execute()
            print("\nTable accessible, but no records to show structure")
        except Exception as e:
            print(f"\nCould not determine structure: {e}")

except Exception as e:
    error_msg = str(e).lower()
    if 'does not exist' in error_msg or 'relation' in error_msg:
        print("❌ oauth_states table does NOT exist")
        print(f"\nError: {e}")
        print("\n📋 The table needs to be created.")
    else:
        print(f"❓ Unexpected error: {e}\n")

# Also check if there are any records
try:
    count_result = supabase.table('oauth_states').select('*', count='exact').execute()
    print(f"\n📊 Total records in oauth_states: {count_result.count}")
except Exception as e:
    print(f"\n❌ Could not count records: {e}")

print()
