"""
Test script to verify Voyage AI embeddings integration
"""
import os
from dotenv import load_dotenv
import voyageai
from supabase import create_client

# Load environment variables
load_dotenv()

def test_voyage_embeddings():
    """Test Voyage AI embedding generation"""

    # Load API key
    api_key = os.environ.get("VOYAGE_API_KEY")

    if not api_key:
        print("❌ ERROR: VOYAGE_API_KEY not found in environment")
        return False

    print(f"✓ Voyage AI key found: {api_key[:20]}...")

    # Initialize Voyage client
    vo = voyageai.Client(api_key=api_key)

    # Test text to embed
    test_texts = [
        "This is a test document about innovation and efficiency.",
        "SuperAssistant helps executives make better decisions.",
        "The PB_Magic framework measures leadership effectiveness."
    ]

    print(f"\n🤖 Generating embeddings for {len(test_texts)} test texts...")

    try:
        # Generate embeddings using voyage-3
        result = vo.embed(
            test_texts,
            model="voyage-3",
            input_type="document"
        )

        embeddings = result.embeddings

        print(f"\n✅ SUCCESS! Generated {len(embeddings)} embeddings")
        print(f"   Embedding dimension: {len(embeddings[0])}")
        print(f"   Expected dimension: 1024")

        # Verify dimension matches database
        if len(embeddings[0]) == 1024:
            print(f"   ✓ Dimension matches database VECTOR(1024)!")
        else:
            print(f"   ❌ WARNING: Dimension mismatch! Database expects 1024.")
            return False

        # Show sample embedding values
        print(f"\n📊 Sample embedding (first 10 values):")
        print(f"   {embeddings[0][:10]}")

        return embeddings[0]  # Return first embedding for database test

    except Exception as e:
        print(f"\n❌ ERROR generating embeddings:")
        print(f"   {str(e)}")
        return False

def test_database_storage(embedding):
    """Test storing embedding in database"""

    print(f"\n🗄️ Testing database storage...")

    # Load Supabase credentials
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("❌ ERROR: Supabase credentials not found")
        return False

    print(f"✓ Supabase URL: {supabase_url}")

    # Initialize Supabase client
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Insert test document chunk with embedding
        # Using the test client ID from Day 2: 1c9351f8-9053-4ce0-a793-d260573afa04

        # First, create a test document
        # Note: uploaded_by should be set, but for test we'll use a placeholder
        doc_result = supabase.table('documents').insert({
            'client_id': '1c9351f8-9053-4ce0-a793-d260573afa04',
            'uploaded_by': '00000000-0000-0000-0000-000000000001',  # Test user placeholder
            'filename': 'test_voyage_embedding.txt',
            'storage_url': 'test://voyage-test',
            'file_type': 'text/plain',
            'processed': True
        }).execute()

        document_id = doc_result.data[0]['id']
        print(f"✓ Created test document: {document_id}")

        # Insert chunk with embedding
        chunk_result = supabase.table('document_chunks').insert({
            'document_id': document_id,
            'client_id': '1c9351f8-9053-4ce0-a793-d260573afa04',
            'content': 'This is a test document about innovation and efficiency.',
            'embedding': embedding,
            'chunk_index': 0,
            'metadata': {'test': True}
        }).execute()

        chunk_id = chunk_result.data[0]['id']
        print(f"✓ Stored chunk with embedding: {chunk_id}")

        # Verify we can retrieve it
        verify_result = supabase.table('document_chunks').select('*').eq('id', chunk_id).execute()

        if verify_result.data and verify_result.data[0]['embedding']:
            print(f"✓ Successfully retrieved embedding from database")
            print(f"   Retrieved dimension: {len(verify_result.data[0]['embedding'])}")
            return True
        else:
            print(f"❌ Failed to retrieve embedding")
            return False

    except Exception as e:
        print(f"\n❌ ERROR storing in database:")
        print(f"   {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("SuperAssistant MVP - Voyage AI Embeddings Test")
    print("=" * 60)

    # Test embedding generation
    embedding = test_voyage_embeddings()

    if embedding:
        # Test database storage
        db_success = test_database_storage(embedding)

        print("\n" + "=" * 60)
        if db_success:
            print("✅ All tests passed! Voyage AI + Database integration working!")
            print("   Ready for document processing pipeline.")
        else:
            print("⚠️ Embeddings work but database storage failed.")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ Embedding generation failed. Check error messages above.")
        print("=" * 60)
