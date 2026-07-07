#!/usr/bin/env python3
"""Create Supabase storage bucket for contracts"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

try:
    # Create the documents bucket
    result = supabase.storage.create_bucket(
        "documents",
        options={"public": True}  # Make it public so we can access files
    )
    print(f"✅ Successfully created 'documents' bucket: {result}")
except Exception as e:
    if "already exists" in str(e).lower():
        print("✅ Bucket 'documents' already exists")
    else:
        print(f"❌ Error creating bucket: {e}")
