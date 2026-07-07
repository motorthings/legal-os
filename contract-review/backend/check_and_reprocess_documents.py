#!/usr/bin/env python3
"""
Check documents for missing embeddings and optionally reprocess them

Usage:
    python check_and_reprocess_documents.py                    # Interactive mode
    python check_and_reprocess_documents.py --auto-fix          # Auto-reprocess all
    python check_and_reprocess_documents.py --client-id <id>    # Filter by client
"""
import os
import sys
import argparse
from database import get_supabase
from document_processor import process_document
from dotenv import load_dotenv

load_dotenv()

# Parse command line arguments
parser = argparse.ArgumentParser(description='Check and reprocess documents without embeddings')
parser.add_argument('--auto-fix', action='store_true', help='Automatically reprocess all documents without embeddings')
parser.add_argument('--client-id', type=str, help='Filter documents by client ID')
args = parser.parse_args()

supabase = get_supabase()

print("=" * 80)
print("DOCUMENT EMBEDDING CHECK")
print("=" * 80)

# Get all documents
if args.client_id:
    print(f"\n📊 Fetching documents for client: {args.client_id}...")
    docs_query = supabase.table('documents').select(
        'id, filename, client_id, processed, chunk_count, source_platform, uploaded_at'
    ).eq('client_id', args.client_id).order('uploaded_at', desc=True)
else:
    print("\n📊 Fetching all documents...")
    docs_query = supabase.table('documents').select(
        'id, filename, client_id, processed, chunk_count, source_platform, uploaded_at'
    ).order('uploaded_at', desc=True)

docs_result = docs_query.execute()

if not docs_result.data:
    print("❌ No documents found in database")
    sys.exit(0)

print(f"✅ Found {len(docs_result.data)} documents\n")

# Check each document for embeddings
documents_without_embeddings = []
documents_with_embeddings = []

for doc in docs_result.data:
    doc_id = doc['id']
    filename = doc['filename']
    client_id = doc.get('client_id', 'unknown')
    processed = doc.get('processed', False)

    # Check if this document has chunks with embeddings
    chunks_result = supabase.table('document_chunks').select(
        'id, embedding'
    ).eq('document_id', doc_id).execute()

    chunk_count = len(chunks_result.data)
    chunks_with_embeddings = sum(1 for c in chunks_result.data if c.get('embedding'))

    print(f"📄 {filename}")
    print(f"   ID: {doc_id}")
    print(f"   Client ID: {client_id}")
    print(f"   Processed: {processed}")
    print(f"   Chunks: {chunk_count}")
    print(f"   Chunks with embeddings: {chunks_with_embeddings}")

    if chunk_count == 0 or chunks_with_embeddings == 0:
        print(f"   ⚠️  MISSING EMBEDDINGS")
        documents_without_embeddings.append(doc)
    else:
        print(f"   ✅ Has embeddings")
        documents_with_embeddings.append(doc)

    print()

# Summary
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Documents with embeddings: {len(documents_with_embeddings)}")
print(f"Documents without embeddings: {len(documents_without_embeddings)}")

if documents_without_embeddings:
    print("\n⚠️  The following documents need processing:")
    for doc in documents_without_embeddings:
        print(f"   - {doc['filename']} (ID: {doc['id']})")

    # Determine whether to reprocess
    should_reprocess = False

    if args.auto_fix:
        print("\n🔄 Auto-fix mode enabled - reprocessing all documents...")
        should_reprocess = True
    else:
        # Ask if user wants to reprocess
        print("\n" + "=" * 80)
        print("REPROCESSING OPTIONS")
        print("=" * 80)
        print("\nWould you like to reprocess these documents?")
        print("1. Yes, reprocess all documents without embeddings")
        print("2. No, just show the report")
        print()

        choice = input("Enter choice (1 or 2): ").strip()
        should_reprocess = (choice == "1")

    if should_reprocess:
        print("\n🔄 Reprocessing documents...")
        success_count = 0
        error_count = 0
        errors = []

        for doc in documents_without_embeddings:
            try:
                print(f"\n📄 Processing: {doc['filename']}")
                result = process_document(doc['id'])
                print(f"   ✅ Success: {result.get('chunks_stored', 0)} chunks stored")
                success_count += 1
            except Exception as e:
                error_msg = f"{doc['filename']}: {str(e)}"
                print(f"   ❌ Error: {str(e)}")
                errors.append(error_msg)
                error_count += 1

        print("\n" + "=" * 80)
        print("REPROCESSING COMPLETE")
        print("=" * 80)
        print(f"Successfully processed: {success_count}")
        print(f"Errors: {error_count}")

        if errors:
            print("\n⚠️  Errors encountered:")
            for err in errors:
                print(f"   - {err}")
    else:
        print("\n✅ Report complete. No documents were reprocessed.")
else:
    print("\n✅ All documents have embeddings!")

print("\n" + "=" * 80)
