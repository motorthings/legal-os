#!/usr/bin/env python3
"""Describe oauth_states table structure by inspecting insert attempt"""
import os
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

supabase = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_KEY")
)

print("\n📋 oauth_states Table Structure\n")
print("=" * 60)

# Based on the code in main.py, here's the schema:
schema = {
    "state": "VARCHAR (Primary Key) - OAuth state token",
    "user_id": "UUID - Foreign key to auth.users",
    "redirect_uri": "VARCHAR - URI to redirect after OAuth",
    "created_at": "TIMESTAMPTZ - Timestamp when state was created",
    "expires_at": "TIMESTAMPTZ - Expiration timestamp for state",
    "used": "BOOLEAN - Whether state has been used"
}

print("\nColumns:")
print("-" * 60)
for col, desc in schema.items():
    print(f"  • {col:20} {desc}")

print("\n" + "=" * 60)
print("\n📊 Current Records:")
print("-" * 60)

try:
    result = supabase.table('oauth_states').select('*').execute()

    if result.data:
        print(f"\nFound {len(result.data)} record(s):\n")
        for i, record in enumerate(result.data, 1):
            print(f"Record {i}:")
            for key, value in record.items():
                print(f"  {key:20} {value}")
            print()
    else:
        print("\n✓ Table is empty (no records)")

except Exception as e:
    print(f"\n❌ Error querying table: {e}")

print("=" * 60)
print()
