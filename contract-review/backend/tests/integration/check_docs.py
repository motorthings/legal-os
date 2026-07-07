import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

client = create_client(supabase_url, supabase_key)

# Query documents with chunk count
response = client.table("documents").select("id, filename, uploaded_at, file_type").eq("filename", "untitled").execute()

print(f"Found {len(response.data)} 'untitled' documents:")
for doc in response.data:
    # Count chunks for this document
    chunks_response = client.table("document_chunks").select("id", count="exact").eq("document_id", doc['id']).execute()
    chunk_count = chunks_response.count if chunks_response.count else 0
    
    print(f"\n- ID: {doc['id']}")
    print(f"  Filename: {doc['filename']}")
    print(f"  Type: {doc.get('file_type', 'unknown')}")
    print(f"  Uploaded: {doc.get('uploaded_at', 'unknown')}")
    print(f"  Chunks: {chunk_count}")
