import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

client = create_client(supabase_url, supabase_key)

# The corrupted document ID
corrupted_doc_id = "439e400c-acec-4b2f-a02b-0a29504a7325"

print(f"Attempting to delete corrupted document: {corrupted_doc_id}")

# First, delete all chunks for this document
print("Deleting document chunks...")
chunks_response = client.table("document_chunks").delete().eq("document_id", corrupted_doc_id).execute()
print(f"✓ Deleted {len(chunks_response.data) if chunks_response.data else 0} chunks")

# Then delete the document record itself
print("Deleting document record...")
doc_response = client.table("documents").delete().eq("id", corrupted_doc_id).execute()
print(f"✓ Deleted document: {doc_response.data}")

print("\n✅ Corrupted document removed successfully!")
print("\nVerifying deletion...")

# Verify it's gone
check_response = client.table("documents").select("*").eq("id", corrupted_doc_id).execute()
if not check_response.data or len(check_response.data) == 0:
    print("✓ Confirmed: Document no longer exists in database")
else:
    print("⚠️  Warning: Document still exists in database")
