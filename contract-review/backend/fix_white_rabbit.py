#!/usr/bin/env python3
"""
Fix the White Rabbit Document

This script:
1. Identifies the corrupted "white rabbits" document
2. Deletes its corrupted chunks
3. Resets its processing status
4. Triggers reprocessing from the source file

Usage:
    python fix_white_rabbit.py
"""

from dotenv import load_dotenv
load_dotenv()

from database import get_supabase
from logger_config import get_logger

logger = get_logger(__name__)
supabase = get_supabase()

# The problematic document
DOC_ID = '1ccc278a-57f0-473a-a640-99bb1bb9f48d'
DOC_NAME = 'all about white rabbits'


def analyze_document():
    """Analyze the current state of the document."""
    logger.info(f"\n🔍 Analyzing document: {DOC_NAME}")

    # Get document info
    doc = supabase.table('documents').select('*').eq('id', DOC_ID).execute().data[0]

    logger.info(f"   Status: processed={doc['processed']}, status={doc.get('processing_status')}")
    logger.info(f"   Chunk count: {doc.get('chunk_count')}")
    logger.info(f"   Error: {doc.get('processing_error')}")

    # Check chunks
    chunks = supabase.table('document_chunks').select('id, content').eq('document_id', DOC_ID).limit(3).execute()

    logger.info(f"\n   Sample chunks (first 3 of {doc.get('chunk_count')}):")
    for i, chunk in enumerate(chunks.data, 1):
        content = chunk['content']
        printable_ratio = sum(1 for c in content if c.isprintable() or c.isspace()) / len(content)
        is_binary = content.startswith('PK') or '<' in content[:50]

        logger.info(f"   {i}. Printable: {printable_ratio:.1%}, Binary markers: {is_binary}")
        logger.info(f"      Preview: {content[:80]}...")

    return doc


def delete_corrupted_chunks():
    """Delete all corrupted chunks for this document."""
    logger.info(f"\n🗑️  Deleting corrupted chunks...")

    result = supabase.table('document_chunks').delete().eq('document_id', DOC_ID).execute()

    logger.info(f"   ✅ Deleted chunks")
    return True


def reset_document_status():
    """Reset document processing status to trigger reprocessing."""
    logger.info(f"\n🔄 Resetting document status...")

    supabase.table('documents').update({
        'processed': False,
        'processing_status': 'pending',
        'processing_error': None,
        'chunk_count': 0,
        'processed_at': None
    }).eq('id', DOC_ID).execute()

    logger.info(f"   ✅ Document status reset to pending")
    return True


def trigger_reprocessing():
    """Trigger document reprocessing."""
    logger.info(f"\n⚙️  Triggering reprocessing...")

    from document_processor import process_document

    try:
        result = process_document(DOC_ID)
        logger.info(f"   ✅ Reprocessing completed!")
        logger.info(f"   Chunks created: {result.get('chunk_count')}")
        logger.info(f"   Status: {result.get('status')}")
        return result
    except Exception as e:
        logger.error(f"   ❌ Reprocessing failed: {e}")
        return None


def verify_fix():
    """Verify the document is now properly processed."""
    logger.info(f"\n✓ Verifying fix...")

    # Get updated document
    doc = supabase.table('documents').select('*').eq('id', DOC_ID).execute().data[0]

    logger.info(f"   Status: {doc.get('processing_status')}")
    logger.info(f"   Chunk count: {doc.get('chunk_count')}")

    # Test search
    from document_processor import search_similar_chunks

    results = search_similar_chunks(
        query='white rabbits',
        client_id=doc['client_id'],
        limit=3,
        min_similarity=0.0
    )

    logger.info(f"\n   Search test for 'white rabbits':")
    logger.info(f"   Found {len(results)} results")

    if results:
        for i, chunk in enumerate(results, 1):
            logger.info(f"   {i}. Similarity: {chunk.get('similarity', 0):.3f}")
            logger.info(f"      Content: {chunk.get('content', '')[:150]}...")

    return len(results) > 0


def main(auto_confirm=False):
    """Main execution."""
    logger.info("="*80)
    logger.info("FIX WHITE RABBIT DOCUMENT")
    logger.info("="*80)

    # Step 1: Analyze
    doc = analyze_document()

    # Step 2: Confirm
    logger.info(f"\n⚠️  This will:")
    logger.info(f"   1. Delete {doc.get('chunk_count')} corrupted chunks")
    logger.info(f"   2. Reset processing status")
    logger.info(f"   3. Reprocess from source file")

    if not auto_confirm:
        response = input("\n   Continue? (yes/no): ")
        if response.lower() != 'yes':
            logger.info("   ❌ Aborted")
            return
    else:
        logger.info("\n   Auto-confirming (--yes flag)")

    # Step 3: Delete chunks
    delete_corrupted_chunks()

    # Step 4: Reset status
    reset_document_status()

    # Step 5: Reprocess
    result = trigger_reprocessing()

    if result:
        # Step 6: Verify
        search_works = verify_fix()

        logger.info("\n" + "="*80)
        if search_works:
            logger.info("✅ SUCCESS! Document fixed and searchable!")
        else:
            logger.info("⚠️  Document reprocessed but search may need time to update")
        logger.info("="*80)
    else:
        logger.info("\n" + "="*80)
        logger.info("❌ FAILED - Check errors above")
        logger.info("="*80)


if __name__ == "__main__":
    import sys
    auto_confirm = '--yes' in sys.argv or '-y' in sys.argv
    main(auto_confirm=auto_confirm)
