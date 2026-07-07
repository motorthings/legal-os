#!/usr/bin/env python3
"""
Comprehensive Knowledge Base Diagnostic Suite
Tests the entire KB search pipeline from database to response
"""
import os
import sys
from database import get_supabase
from document_processor import generate_embeddings
from dotenv import load_dotenv

load_dotenv()

supabase = get_supabase()

print("=" * 80)
print("KNOWLEDGE BASE COMPREHENSIVE DIAGNOSTICS")
print("=" * 80)

# ============================================================================
# TEST 1: Database Connection
# ============================================================================
print("\n" + "=" * 80)
print("TEST 1: DATABASE CONNECTION")
print("=" * 80)

try:
    result = supabase.table('documents').select('id').limit(1).execute()
    print("✅ Database connection successful")
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    sys.exit(1)

# ============================================================================
# TEST 2: Check Documents Table
# ============================================================================
print("\n" + "=" * 80)
print("TEST 2: DOCUMENTS TABLE")
print("=" * 80)

try:
    docs_result = supabase.table('documents').select(
        'id, filename, processed, chunk_count, source_platform, created_at'
    ).order('created_at', desc=True).limit(10).execute()

    print(f"Total documents found: {len(docs_result.data)}")

    if docs_result.data:
        print("\nRecent documents:")
        for i, doc in enumerate(docs_result.data[:5], 1):
            print(f"\n{i}. {doc['filename']}")
            print(f"   ID: {doc['id']}")
            print(f"   Processed: {doc.get('processed', False)}")
            print(f"   Chunk count: {doc.get('chunk_count', 0)}")
            print(f"   Source: {doc.get('source_platform', 'manual')}")
    else:
        print("⚠️  No documents found in database")

except Exception as e:
    print(f"❌ Error querying documents: {e}")

# ============================================================================
# TEST 3: Check Document Chunks Table
# ============================================================================
print("\n" + "=" * 80)
print("TEST 3: DOCUMENT CHUNKS TABLE")
print("=" * 80)

try:
    # Count total chunks
    chunks_result = supabase.table('document_chunks').select(
        'id, document_id, content, source_type, embedding'
    ).limit(1000).execute()

    total_chunks = len(chunks_result.data)
    chunks_with_embeddings = sum(1 for c in chunks_result.data if c.get('embedding') is not None)

    print(f"Total chunks: {total_chunks}")
    print(f"Chunks with embeddings: {chunks_with_embeddings}")
    print(f"Chunks without embeddings: {total_chunks - chunks_with_embeddings}")

    if chunks_result.data:
        # Get unique document IDs
        unique_docs = set(c['document_id'] for c in chunks_result.data)
        print(f"Unique documents with chunks: {len(unique_docs)}")

        # Show sample chunks
        print("\nSample chunks:")
        for i, chunk in enumerate(chunks_result.data[:3], 1):
            content = chunk.get('content', '')
            print(f"\n{i}. Chunk ID: {chunk['id']}")
            print(f"   Document ID: {chunk['document_id']}")
            print(f"   Source type: {chunk.get('source_type', 'unknown')}")
            print(f"   Has embedding: {'Yes' if chunk.get('embedding') else 'No'}")
            print(f"   Content length: {len(content)} chars")
            print(f"   Content preview: {content[:100]}...")

            # Check if content is readable
            if content:
                printable_ratio = sum(c.isprintable() or c.isspace() for c in content) / len(content)
                print(f"   Printable ratio: {printable_ratio:.2%}")
                if printable_ratio < 0.9:
                    print(f"   ⚠️  WARNING: Content may be corrupted!")
    else:
        print("⚠️  No chunks found in database")
        print("   This is the problem! Documents need to be processed.")

except Exception as e:
    print(f"❌ Error querying chunks: {e}")

# ============================================================================
# TEST 4: Check match_document_chunks Function
# ============================================================================
print("\n" + "=" * 80)
print("TEST 4: MATCH_DOCUMENT_CHUNKS FUNCTION")
print("=" * 80)

try:
    # Check if function exists
    func_check = supabase.rpc('exec_sql', {
        'sql': """
            SELECT proname, pg_get_function_arguments(oid) as args
            FROM pg_proc
            WHERE proname = 'match_document_chunks'
        """
    }).execute()

    print("Checking function existence...")
    # Note: exec_sql may not exist, so we'll try direct function call instead

except Exception as e:
    print(f"Note: Could not check function via exec_sql: {e}")

# Try to call the function directly
try:
    print("\nTesting function with dummy embedding...")

    # Get a real embedding from the database first
    sample_chunk = supabase.table('document_chunks').select('embedding').limit(1).execute()

    if sample_chunk.data and sample_chunk.data[0].get('embedding'):
        test_embedding = sample_chunk.data[0]['embedding']
        print(f"Using sample embedding (length: {len(test_embedding)})")

        # Test the function
        result = supabase.rpc('match_document_chunks', {
            'query_embedding': test_embedding,
            'match_count': 5
        }).execute()

        print(f"✅ Function executed successfully!")
        print(f"   Results returned: {len(result.data)}")

        if result.data:
            print("\n   Top results:")
            for i, match in enumerate(result.data[:3], 1):
                print(f"\n   {i}. Similarity: {match.get('similarity', 0):.4f}")
                print(f"      Content: {match.get('content', '')[:100]}...")
        else:
            print("   ⚠️  No results returned from function")
    else:
        print("⚠️  No embeddings found to test with")

except Exception as e:
    print(f"❌ Error calling match_document_chunks: {e}")
    print(f"   Error type: {type(e).__name__}")
    print(f"   This might indicate the UUID fix wasn't applied correctly")

# ============================================================================
# TEST 5: Test Embedding Generation
# ============================================================================
print("\n" + "=" * 80)
print("TEST 5: EMBEDDING GENERATION")
print("=" * 80)

try:
    test_text = "This is a test query about artificial intelligence and machine learning"
    print(f"Test text: {test_text}")
    print("Generating embedding with Voyage AI...")

    embeddings = generate_embeddings([test_text])

    if embeddings and len(embeddings) > 0:
        embedding = embeddings[0]
        print(f"✅ Embedding generated successfully")
        print(f"   Dimensions: {len(embedding)}")
        print(f"   First 5 values: {embedding[:5]}")

        # Verify it's the right dimension
        if len(embedding) == 1024:
            print(f"   ✅ Correct dimension (1024)")
        else:
            print(f"   ❌ Wrong dimension! Expected 1024, got {len(embedding)}")
    else:
        print("❌ Failed to generate embedding")

except Exception as e:
    print(f"❌ Error generating embedding: {e}")

# ============================================================================
# TEST 6: Test Vector Search with Real Query
# ============================================================================
print("\n" + "=" * 80)
print("TEST 6: VECTOR SEARCH WITH REAL QUERY")
print("=" * 80)

try:
    test_query = "What documents are in the knowledge base?"
    print(f"Test query: {test_query}")

    # Generate embedding for query
    print("Generating query embedding...")
    query_embeddings = generate_embeddings([test_query])

    if query_embeddings and len(query_embeddings) > 0:
        query_embedding = query_embeddings[0]
        print(f"✅ Query embedding generated (dim: {len(query_embedding)})")

        # Search for similar chunks
        print("Searching for similar chunks...")
        search_result = supabase.rpc('match_document_chunks', {
            'query_embedding': query_embedding,
            'match_count': 5
        }).execute()

        print(f"✅ Search completed")
        print(f"   Results found: {len(search_result.data)}")

        if search_result.data:
            print("\n   Search results:")
            for i, match in enumerate(search_result.data, 1):
                print(f"\n   {i}. Similarity: {match.get('similarity', 0):.4f}")
                print(f"      Source: {match.get('source_type', 'unknown')}")
                print(f"      Content preview: {match.get('content', '')[:150]}...")
        else:
            print("   ⚠️  No results found for query")
            print("   This suggests either no chunks exist or embeddings don't match")
    else:
        print("❌ Failed to generate query embedding")

except Exception as e:
    print(f"❌ Error during vector search: {e}")

# ============================================================================
# TEST 7: Check Client ID Filtering
# ============================================================================
print("\n" + "=" * 80)
print("TEST 7: CLIENT ID FILTERING")
print("=" * 80)

try:
    # Get client IDs from chunks
    chunks_with_client = supabase.table('document_chunks').select('client_id').limit(100).execute()

    if chunks_with_client.data:
        unique_clients = set(c.get('client_id') for c in chunks_with_client.data if c.get('client_id'))
        print(f"Unique client IDs in chunks: {len(unique_clients)}")

        if unique_clients:
            print(f"Client IDs: {list(unique_clients)[:5]}")

            # Test with client filter
            test_client_id = list(unique_clients)[0]
            print(f"\nTesting search with client filter: {test_client_id}")

            if query_embeddings and len(query_embeddings) > 0:
                filtered_result = supabase.rpc('match_document_chunks', {
                    'query_embedding': query_embeddings[0],
                    'match_count': 5,
                    'filter_client_id': test_client_id
                }).execute()

                print(f"✅ Filtered search completed")
                print(f"   Results: {len(filtered_result.data)}")
        else:
            print("⚠️  No client IDs found in chunks")
    else:
        print("⚠️  No chunks to check client IDs")

except Exception as e:
    print(f"❌ Error testing client filtering: {e}")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("DIAGNOSTIC SUMMARY")
print("=" * 80)

print("\n📊 Key Findings:")
print(f"   Documents in DB: {len(docs_result.data) if 'docs_result' in locals() else 'Unknown'}")
print(f"   Chunks in DB: {total_chunks if 'total_chunks' in locals() else 'Unknown'}")
print(f"   Chunks with embeddings: {chunks_with_embeddings if 'chunks_with_embeddings' in locals() else 'Unknown'}")

print("\n🔍 Next Steps:")
if 'total_chunks' in locals() and total_chunks == 0:
    print("   1. ❌ NO CHUNKS FOUND - Upload or sync documents first")
elif 'chunks_with_embeddings' in locals() and chunks_with_embeddings == 0:
    print("   1. ❌ NO EMBEDDINGS - Documents need to be processed")
    print("   2. Re-process existing documents or upload new ones")
elif 'search_result' in locals() and len(search_result.data) == 0:
    print("   1. ⚠️  Chunks exist but search returns no results")
    print("   2. Check if embeddings are valid")
    print("   3. Check if client_id filtering is too restrictive")
else:
    print("   1. ✅ KB infrastructure appears functional")
    print("   2. Test with actual chat interface")
    print("   3. Check backend logs for errors")

print("\n" + "=" * 80)
