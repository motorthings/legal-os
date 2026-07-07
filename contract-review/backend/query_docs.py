import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

client = create_client(supabase_url, supabase_key)

# Query documents - get all columns
response = client.table("documents").select("*").execute()

if response.data:
    print(f"✓ Found {len(response.data)} documents in your knowledge base:\n")
    for doc in response.data:
        size_kb = doc.get('file_size', 0) / 1024 if doc.get('file_size') else 0
        print(f"• {doc.get('filename', 'unknown')}")
        print(f"  Type: {doc.get('file_type', 'unknown')}")
        print(f"  Size: {size_kb:.1f} KB")
        print(f"  Uploaded: {doc.get('uploaded_at', 'unknown')}")
        print()
else:
    print("No documents found in the knowledge base.")
