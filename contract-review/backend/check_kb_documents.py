#!/usr/bin/env python3
"""
Diagnostic script to check knowledge base documents for corrupted content
"""
import os
from database import get_supabase
from dotenv import load_dotenv

load_dotenv()

supabase = get_supabase()

print("=" * 80)
print("KNOWLEDGE BASE DOCUMENT DIAGNOSTICS")
print("=" * 80)

# Get all document chunks
print("\n📊 Fetching document chunks...")
result = supabase.table('document_chunks').select('id, document_id, content, source_type').limit(10).execute()

if not result.data:
    print("❌ No document chunks found in knowledge base")
    exit(0)

print(f"✅ Found {len(result.data)} chunks (showing first 10)")

# Analyze each chunk
for idx, chunk in enumerate(result.data, 1):
    content = chunk.get('content', '')
    print(f"\n--- Chunk {idx} ---")
    print(f"ID: {chunk['id']}")
    print(f"Document ID: {chunk['document_id']}")
    print(f"Source: {chunk.get('source_type', 'unknown')}")
    print(f"Content length: {len(content)} chars")

    # Check if content is text or binary
    try:
        # Check for printable characters
        printable_ratio = sum(c.isprintable() or c.isspace() for c in content) / len(content) if content else 0
        print(f"Printable ratio: {printable_ratio:.2%}")

        # Show first 200 characters
        preview = content[:200].replace('\n', '\\n')
        print(f"Preview: {preview}...")

        if printable_ratio < 0.9:
            print("⚠️  WARNING: Content appears to be binary or corrupted!")

    except Exception as e:
        print(f"❌ Error analyzing content: {e}")

# Get document metadata
print("\n" + "=" * 80)
print("DOCUMENT METADATA")
print("=" * 80)

doc_result = supabase.table('documents').select(
    'id, filename, source_platform, google_drive_file_id, processed, chunk_count'
).limit(10).execute()

for doc in doc_result.data:
    print(f"\n📄 {doc['filename']}")
    print(f"   ID: {doc['id']}")
    print(f"   Source: {doc.get('source_platform', 'manual')}")
    print(f"   Processed: {doc.get('processed', False)}")
    print(f"   Chunks: {doc.get('chunk_count', 0)}")
    if doc.get('google_drive_file_id'):
        print(f"   Google Drive ID: {doc['google_drive_file_id']}")

print("\n" + "=" * 80)
print("RECOMMENDATIONS")
print("=" * 80)
print("""
If you see binary/corrupted content:
1. The Google Drive export may be failing for Google Docs/Sheets/Slides
2. Try re-syncing the documents after applying the fix
3. Check that the llama-index-readers-google library is properly handling exports

To fix:
- Update document sync to better validate text content before saving
- Add MIME type handling for XLSX and PPTX files (not just DOCX)
- Improve error logging for failed exports
""")
