#!/usr/bin/env python3
"""
Quick script to verify document status in the database.
Shows recent documents and their processing status.

Usage:
    python verify_document_status.py
"""

import sys
from database import get_supabase
from logger_config import get_logger

logger = get_logger(__name__)

def main():
    print("=" * 80)
    print("DOCUMENT STATUS VERIFICATION")
    print("=" * 80)

    try:
        supabase = get_supabase()

        # Get recent documents
        print("\n📄 Recent Documents (last 10):")
        docs = supabase.table('documents').select(
            'id, filename, processing_status, chunk_count, uploaded_at'
        ).order('uploaded_at', desc=True).limit(10).execute()

        if docs.data:
            for i, doc in enumerate(docs.data, 1):
                status = doc.get('processing_status', 'unknown')
                chunks = doc.get('chunk_count', 0)
                status_icon = "✅" if status == 'completed' else "⏳" if status == 'processing' else "❌"

                print(f"\n{i}. {status_icon} {doc['filename']}")
                print(f"   ID: {doc['id'][:8]}...")
                print(f"   Status: {status}")
                print(f"   Chunks: {chunks}")
                print(f"   Uploaded: {doc.get('uploaded_at', 'unknown')[:19]}")
        else:
            print("   No documents found")

        # Check for rabbit-related documents specifically
        print("\n\n🐰 Searching for documents with 'rabbit' in filename...")
        rabbit_docs = supabase.table('documents').select('*').ilike('filename', '%rabbit%').execute()

        if rabbit_docs.data:
            print(f"   ✅ Found {len(rabbit_docs.data)} document(s):")
            for doc in rabbit_docs.data:
                print(f"\n   📄 {doc['filename']}")
                print(f"      Status: {doc.get('processing_status')}")
                print(f"      Chunks: {doc.get('chunk_count', 0)}")

                # Check if chunks exist
                if doc.get('chunk_count', 0) > 0:
                    doc_id = doc['id']
                    chunks = supabase.table('document_chunks').select(
                        'id, content, embedding'
                    ).eq('document_id', doc_id).limit(1).execute()

                    if chunks.data:
                        chunk = chunks.data[0]
                        has_embedding = chunk.get('embedding') is not None
                        print(f"      Sample chunk: {chunk['content'][:100]}...")
                        print(f"      Has embedding: {'✅' if has_embedding else '❌'}")
        else:
            print("   ❌ No documents with 'rabbit' in filename found")
            print("\n   This might mean:")
            print("   1. Document not uploaded yet")
            print("   2. Document has different filename")
            print("   3. Document was deleted")

        # Check total chunks
        print("\n\n📊 Database Statistics:")
        total_docs = supabase.table('documents').select('id', count='exact').execute()
        total_chunks = supabase.table('document_chunks').select('id', count='exact').execute()
        chunks_with_embeddings = supabase.table('document_chunks').select(
            'id', count='exact'
        ).not_.is_('embedding', 'null').execute()

        print(f"   Total documents: {total_docs.count}")
        print(f"   Total chunks: {total_chunks.count}")
        print(f"   Chunks with embeddings: {chunks_with_embeddings.count}")

        print("\n" + "=" * 80)
        print("VERIFICATION COMPLETE")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
