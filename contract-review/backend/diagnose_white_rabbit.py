#!/usr/bin/env python3
"""
Diagnostic script to investigate why white rabbit document isn't being retrieved.

This script will:
1. Find the white rabbit document in the database
2. Check if it has been processed and has embeddings
3. Test the search function with the query "white rabbits"
4. Show similarity scores and explain why it might not be retrieved
"""

import sys
from database import get_supabase
from document_processor import search_similar_chunks, preprocess_query, detect_query_type
from logger_config import get_logger

logger = get_logger(__name__)

def main():
    print("=" * 80)
    print("WHITE RABBIT DOCUMENT DIAGNOSTIC")
    print("=" * 80)

    supabase = get_supabase()

    # Step 1: Find documents with "white rabbit" in content
    print("\n[STEP 1] Searching for documents containing 'white rabbit'...")
    docs_result = supabase.table('documents').select('*').ilike('filename', '%rabbit%').execute()

    if docs_result.data:
        print(f"✓ Found {len(docs_result.data)} document(s) with 'rabbit' in filename:")
        for doc in docs_result.data:
            print(f"\n  Document ID: {doc['id']}")
            print(f"  Filename: {doc['filename']}")
            print(f"  Client ID: {doc['client_id']}")
            print(f"  Processed: {doc.get('processed', False)}")
            print(f"  Processing Status: {doc.get('processing_status', 'unknown')}")
            print(f"  Chunk Count: {doc.get('chunk_count', 0)}")
            print(f"  Uploaded: {doc.get('uploaded_at', 'unknown')}")
    else:
        print("✗ No documents found with 'rabbit' in filename")
        print("\nTrying broader search in all documents...")
        all_docs = supabase.table('documents').select('*').order('uploaded_at', desc=True).limit(10).execute()
        print(f"\nLast 10 uploaded documents:")
        for doc in all_docs.data:
            print(f"  - {doc['filename']} (ID: {doc['id'][:8]}..., Chunks: {doc.get('chunk_count', 0)})")

    # Step 2: Search document_chunks for white rabbit content
    print("\n[STEP 2] Searching chunks table for 'white rabbit' content...")
    chunks_result = supabase.table('document_chunks').select('*').ilike('content', '%white rabbit%').execute()

    if chunks_result.data:
        print(f"✓ Found {len(chunks_result.data)} chunk(s) containing 'white rabbit':")
        for i, chunk in enumerate(chunks_result.data[:3]):  # Show first 3 chunks
            print(f"\n  Chunk {i+1}:")
            print(f"    Chunk ID: {chunk['id']}")
            print(f"    Document ID: {chunk.get('document_id', 'N/A')}")
            print(f"    Client ID: {chunk['client_id']}")
            print(f"    Content preview: {chunk['content'][:200]}...")
            print(f"    Has embedding: {chunk.get('embedding') is not None}")
            print(f"    Source type: {chunk.get('source_type', 'unknown')}")
            print(f"    Chunk index: {chunk.get('chunk_index', 'N/A')}")
    else:
        print("✗ No chunks found containing 'white rabbit'")
        print("\nThis means the document either:")
        print("  1. Was not uploaded yet")
        print("  2. Failed to process")
        print("  3. Was deleted")
        print("  4. Content doesn't actually contain 'white rabbit'")

    # Step 3: Get client_id to test search
    if chunks_result.data:
        test_client_id = chunks_result.data[0]['client_id']
        print(f"\n[STEP 3] Testing search function with client_id: {test_client_id}")

        # Test the actual query
        test_query = "what can you tell me about white rabbits?"
        print(f"\nOriginal query: '{test_query}'")

        # Show preprocessing
        query_type = detect_query_type(test_query)
        preprocessed = preprocess_query(test_query)
        print(f"Query type: {query_type}")
        print(f"Preprocessed query: '{preprocessed}'")

        # Test search
        print("\nExecuting search...")
        try:
            results = search_similar_chunks(
                query=test_query,
                client_id=test_client_id,
                limit=5,
                min_similarity=0.0  # Show all results regardless of similarity
            )

            print(f"\n✓ Search returned {len(results)} results:")
            for i, result in enumerate(results):
                print(f"\n  Result {i+1}:")
                print(f"    Similarity: {result.get('similarity', 0.0):.4f}")
                print(f"    Content preview: {result['content'][:150]}...")
                print(f"    Source type: {result.get('source_type', 'unknown')}")
                print(f"    Metadata: {result.get('metadata', {})}")

            # Check if any results would pass the threshold
            print("\n[ANALYSIS] Threshold Check:")
            factual_threshold = 0.50
            exploratory_threshold = 0.40

            above_factual = [r for r in results if r.get('similarity', 0.0) >= factual_threshold]
            above_exploratory = [r for r in results if r.get('similarity', 0.0) >= exploratory_threshold]

            print(f"  Results >= 0.50 (factual threshold): {len(above_factual)}")
            print(f"  Results >= 0.40 (exploratory threshold): {len(above_exploratory)}")

            if not above_factual:
                print("\n  ⚠️  WARNING: No results pass factual threshold!")
                print(f"  This query is detected as '{query_type}' type")
                if query_type == 'factual':
                    print(f"  It needs similarity >= {factual_threshold} to be used")
                    print(f"  Highest similarity found: {results[0].get('similarity', 0.0):.4f}" if results else "No results")
                    print("\n  POSSIBLE SOLUTIONS:")
                    print("  1. Lower the factual similarity threshold in config/constants.py")
                    print("  2. Improve the document content to be more specific")
                    print("  3. Use more specific keywords in the query")

        except Exception as e:
            print(f"\n✗ Search failed with error: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n[STEP 3] Skipped - no chunks found to test with")

    # Step 4: Check for any filtering issues
    print("\n[STEP 4] Checking for potential filtering issues...")

    # Check total chunks for client
    if chunks_result.data:
        client_id = chunks_result.data[0]['client_id']
        total_chunks = supabase.table('document_chunks').select('id', count='exact').eq('client_id', client_id).execute()
        print(f"  Total chunks for client {client_id[:8]}...: {total_chunks.count}")

        chunks_with_embeddings = supabase.table('document_chunks').select('id', count='exact').eq('client_id', client_id).not_.is_('embedding', 'null').execute()
        print(f"  Chunks with embeddings: {chunks_with_embeddings.count}")

        if total_chunks.count != chunks_with_embeddings.count:
            print(f"  ⚠️  WARNING: {total_chunks.count - chunks_with_embeddings.count} chunks missing embeddings!")

    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
