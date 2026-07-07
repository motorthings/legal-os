#!/usr/bin/env python3
"""Create test user in Supabase"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

test_user = {
    "id": "00000000-0000-0000-0000-000000000001",
    "email": "test@example.com",
    "storage_used": 0,
    "storage_quota": 524288000  # 500MB
}

try:
    # Try to insert the test user
    result = supabase.table("users").insert(test_user).execute()
    print(f"✅ Successfully created test user: {result.data}")
except Exception as e:
    error_msg = str(e)
    if "duplicate key" in error_msg.lower() or "already exists" in error_msg.lower():
        print("✅ Test user already exists")
    else:
        print(f"❌ Error creating test user: {e}")
