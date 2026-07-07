#!/usr/bin/env python3
"""
Process KB Document and Insert into Supabase with Embeddings
This script chunks the legal KB document and generates Voyage AI embeddings
"""
import os
import re
import sys
from typing import List, Dict
from dotenv import load_dotenv
from supabase import create_client, Client
import voyageai

# Load environment variables
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    sys.exit(1)

if not VOYAGE_API_KEY:
    print("❌ Error: VOYAGE_API_KEY must be set")
    sys.exit(1)

# KB document path
KB_DOC_PATH = "/Users/motorthings/Documents/Obsidian Vault/Career/Contentful/Presentation/legal-kb-doc.md"

def chunk_document_by_sections(content: str, max_chunk_size: int = 1500) -> List[Dict[str, str]]:
    """
    Chunk the document by major sections and subsections
    Preserves context by keeping related content together
    """
    chunks = []

    # Split by major headings (##)
    sections = re.split(r'\n(## \*\*.*?\*\*)', content)

    current_section_title = "Introduction"

    for i, section in enumerate(sections):
        # Check if this is a heading
        if section.startswith("## "):
            current_section_title = section.strip()
            continue

        # Skip empty sections
        if not section.strip():
            continue

        # Split by subsections (###)
        subsections = re.split(r'\n(### \*\*.*?\*\*)', section)

        current_subsection_title = ""

        for j, subsection in enumerate(subsections):
            if subsection.startswith("### "):
                current_subsection_title = subsection.strip()
                continue

            if not subsection.strip():
                continue

            # If subsection is too large, split by paragraphs
            if len(subsection) > max_chunk_size:
                paragraphs = subsection.split('\n\n')
                current_chunk = ""

                for para in paragraphs:
                    if len(current_chunk) + len(para) < max_chunk_size:
                        current_chunk += para + "\n\n"
                    else:
                        if current_chunk:
                            chunk_title = f"{current_section_title}"
                            if current_subsection_title:
                                chunk_title += f" > {current_subsection_title}"

                            chunks.append({
                                "title": chunk_title,
                                "content": current_chunk.strip()
                            })
                        current_chunk = para + "\n\n"

                # Add remaining content
                if current_chunk.strip():
                    chunk_title = f"{current_section_title}"
                    if current_subsection_title:
                        chunk_title += f" > {current_subsection_title}"

                    chunks.append({
                        "title": chunk_title,
                        "content": current_chunk.strip()
                    })
            else:
                # Subsection is small enough, add as single chunk
                chunk_title = f"{current_section_title}"
                if current_subsection_title:
                    chunk_title += f" > {current_subsection_title}"

                chunks.append({
                    "title": chunk_title,
                    "content": subsection.strip()
                })

    return chunks

def generate_embeddings(texts: List[str], voyage_client: voyageai.Client) -> List[List[float]]:
    """
    Generate Voyage AI embeddings for a list of texts
    """
    print(f"  📊 Generating embeddings for {len(texts)} chunks...")

    try:
        result = voyage_client.embed(
            texts=texts,
            model="voyage-3",  # 1024 dimensions
            input_type="document"
        )
        return result.embeddings
    except Exception as e:
        print(f"  ❌ Error generating embeddings: {str(e)}")
        raise

def main():
    print("🔍 Processing Legal KB Document for RAG")
    print("=" * 60)

    # Check if KB document exists
    if not os.path.exists(KB_DOC_PATH):
        print(f"❌ Error: KB document not found at {KB_DOC_PATH}")
        sys.exit(1)

    # Read KB document
    print(f"\n📄 Reading KB document: {KB_DOC_PATH}")
    with open(KB_DOC_PATH, 'r', encoding='utf-8') as f:
        kb_content = f.read()

    print(f"  ✅ Read {len(kb_content)} characters")

    # Chunk document
    print("\n✂️  Chunking document by sections...")
    chunks = chunk_document_by_sections(kb_content)
    print(f"  ✅ Created {len(chunks)} chunks")

    # Show sample chunks
    print("\n📋 Sample chunks:")
    for i, chunk in enumerate(chunks[:3]):
        print(f"  {i+1}. {chunk['title'][:60]}... ({len(chunk['content'])} chars)")
    print(f"  ... ({len(chunks) - 3} more chunks)")

    # Initialize Voyage AI client
    print("\n🚀 Initializing Voyage AI client...")
    voyage_client = voyageai.Client(api_key=VOYAGE_API_KEY)

    # Generate embeddings in batches (Voyage AI has rate limits)
    batch_size = 50  # Process 50 chunks at a time
    all_embeddings = []

    print(f"\n🧠 Generating embeddings in batches of {batch_size}...")
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        batch_texts = [f"{c['title']}\n\n{c['content']}" for c in batch]

        print(f"  Batch {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1}...")
        batch_embeddings = generate_embeddings(batch_texts, voyage_client)
        all_embeddings.extend(batch_embeddings)

    print(f"  ✅ Generated {len(all_embeddings)} embeddings")

    # Connect to Supabase
    print("\n🔌 Connecting to Supabase...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    # Create a special document record for the KB
    print("\n📝 Creating KB document record...")

    # First, get or create default client and admin user
    # Check if default client exists
    client_result = supabase.table('clients').select('*').eq('id', '00000000-0000-0000-0000-000000000001').execute()

    if not client_result.data:
        print("  ℹ️  Default client not found, creating...")
        supabase.table('clients').insert({
            'id': '00000000-0000-0000-0000-000000000001',
            'name': 'Default Client'
        }).execute()

    # Check if admin user exists, if not create one
    user_result = supabase.table('users').select('*').limit(1).execute()

    if not user_result.data:
        print("  ℹ️  No users found, creating admin user...")
        user_insert = supabase.table('users').insert({
            'email': 'admin@contentful-demo.com',
            'name': 'Demo Admin',
            'role': 'admin',
            'client_id': '00000000-0000-0000-0000-000000000001'
        }).execute()
        admin_user_id = user_insert.data[0]['id']
    else:
        admin_user_id = user_result.data[0]['id']

    # Create KB document record (using only essential columns)
    kb_doc_result = supabase.table('documents').insert({
        'client_id': '00000000-0000-0000-0000-000000000001',
        'uploaded_by': admin_user_id,
        'filename': 'Legal Contract Review Knowledge Base',
        'storage_path': 'kb/legal-kb-doc.md',
        'storage_url': KB_DOC_PATH,
        'file_size': len(kb_content)
    }).execute()

    kb_document_id = kb_doc_result.data[0]['id']
    print(f"  ✅ Created KB document record: {kb_document_id}")

    # Insert chunks with embeddings
    print(f"\n💾 Inserting {len(chunks)} chunks into database...")

    for i, (chunk, embedding) in enumerate(zip(chunks, all_embeddings)):
        try:
            chunk_content = f"# {chunk['title']}\n\n{chunk['content']}"

            supabase.table('document_chunks').insert({
                'document_id': kb_document_id,
                'client_id': '00000000-0000-0000-0000-000000000001',
                'chunk_index': i,
                'content': chunk_content,
                'embedding': embedding
            }).execute()

            if (i + 1) % 10 == 0:
                print(f"  Inserted {i + 1}/{len(chunks)} chunks...")

        except Exception as e:
            print(f"  ❌ Error inserting chunk {i}: {str(e)}")
            continue

    print(f"  ✅ Successfully inserted all {len(chunks)} chunks")

    # Verify insertion
    print("\n🔍 Verifying insertion...")
    verify_result = supabase.table('document_chunks').select('id').eq('document_id', kb_document_id).execute()

    print(f"  ✅ Verified {len(verify_result.data)} chunks in database")

    # Test RAG query
    print("\n🧪 Testing RAG query...")
    test_query = "What are the key risk factors for liability clauses?"

    print(f"  Query: '{test_query}'")
    test_embedding = voyage_client.embed(
        texts=[test_query],
        model="voyage-3",
        input_type="query"
    ).embeddings[0]

    # Use the match_document_chunks function
    try:
        match_result = supabase.rpc('match_document_chunks', {
            'query_embedding': test_embedding,
            'match_threshold': 0.5,
            'match_count': 3,
            'filter_document_ids': [kb_document_id]
        }).execute()

        print(f"  ✅ Found {len(match_result.data)} relevant chunks:")
        for i, match in enumerate(match_result.data):
            print(f"    {i+1}. Similarity: {match['similarity']:.3f}")
            print(f"       {match['content'][:100]}...")

    except Exception as e:
        print(f"  ⚠️  RAG query test failed: {str(e)}")
        print("     This is normal if you haven't created the match_document_chunks function yet")

    print("\n" + "=" * 60)
    print("🎉 KB Document Processing Complete!")
    print("\nSummary:")
    print(f"  - Document ID: {kb_document_id}")
    print(f"  - Total chunks: {len(chunks)}")
    print(f"  - Embeddings generated: {len(all_embeddings)}")
    print(f"  - Database records inserted: {len(verify_result.data)}")
    print("\nThe RAG system is now ready to use for contract analysis!")

if __name__ == "__main__":
    main()
