import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

client = create_client(supabase_url, supabase_key)

# Query conversations
response = client.table("conversations").select("*").eq("client_id", "4e94bfa4-d02c-4e52-b4d5-f0701f5c320b").order("created_at", desc=True).execute()

print(f"✓ Found {len(response.data)} conversations:\n")
for conv in response.data:
    print(f"• ID: {conv['id']}")
    print(f"  Title: {conv.get('title', 'No title')}")
    print(f"  Created: {conv.get('created_at', 'unknown')}")
    print(f"  Updated: {conv.get('updated_at', 'unknown')}")
    print(f"  Archived: {conv.get('is_archived', False)}")
    print()
