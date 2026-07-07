#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
supabase = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
)

# Delete the KB document (will cascade delete chunks)
result = supabase.table('documents').delete().eq('filename', 'Legal Contract Review Knowledge Base').execute()
print(f"✅ Deleted {len(result.data)} KB document(s)")
