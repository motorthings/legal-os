#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
supabase = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
)

print("Checking documents table schema...")
try:
    result = supabase.table('documents').select('*').limit(0).execute()
    print("✅ documents table exists")
except Exception as e:
    print(f"❌ Error: {e}")

print("\nChecking document_chunks table...")
try:
    result = supabase.table('document_chunks').select('*').limit(0).execute()
    print("✅ document_chunks table exists")
except Exception as e:
    print(f"❌ Error: {e}")
