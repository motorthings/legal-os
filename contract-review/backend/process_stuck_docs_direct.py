#!/usr/bin/env python3
"""
Directly process stuck documents without going through the API
"""
from database import get_supabase
from document_processor import process_document
from dotenv import load_dotenv

load_dotenv()

def process_stuck_documents():
    """Find and process all pending documents directly"""
    supabase = get_supabase()

    # Find all documents stuck in 'pending' status
    result = supabase.table('documents')\
        .select('id, filename')\
        .eq('processing_status', 'pending')\
        .execute()

    pending_docs = result.data

    if not pending_docs:
        print("✅ No stuck documents found!")
        return

    print(f"📋 Found {len(pending_docs)} stuck document(s):")
    for doc in pending_docs:
        print(f"   - {doc['filename']} (ID: {doc['id']})")

    print("\n🔄 Processing documents...")

    for doc in pending_docs:
        try:
            print(f"\n   Processing: {doc['filename']}")
            process_document(doc['id'])
            print(f"   ✅ Processed: {doc['filename']}")
        except Exception as e:
            print(f"   ❌ Error processing {doc['filename']}: {e}")

    print("\n✅ Done! All documents processed.")

if __name__ == "__main__":
    process_stuck_documents()
