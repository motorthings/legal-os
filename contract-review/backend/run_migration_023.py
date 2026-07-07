#!/usr/bin/env python3
"""
Migration 023: Add core document flag
Adds is_core_document column to mark system/core documents that cannot be deleted
"""
import os
from dotenv import load_dotenv
from database import get_supabase

load_dotenv()

supabase = get_supabase()

print("=" * 80)
print("MIGRATION 023: Add Core Document Flag")
print("=" * 80)
print()

# Step 1: Add column via direct Supabase admin client
print("Step 1: Adding is_core_document column...")
try:
    # Using the Supabase REST API to add column
    # Note: This requires direct database access or manual SQL execution
    print("⚠️  Note: Column addition requires manual SQL execution in Supabase")
    print("   Please run this SQL in Supabase SQL Editor:")
    print()
    print("   ALTER TABLE documents ADD COLUMN IF NOT EXISTS is_core_document BOOLEAN DEFAULT false;")
    print("   CREATE INDEX IF NOT EXISTS idx_documents_is_core ON documents(is_core_document);")
    print()
    input("Press Enter after you've run the SQL above...")
    print("✅ Column should now be added")
except Exception as e:
    print(f"❌ Error: {e}")
    print("   Please add the column manually in Supabase SQL Editor")
    exit(1)

print()

# Step 2: Mark core documents
print("Step 2: Marking core documents...")
try:
    # Get all documents for the client
    client_id = '4e94bfa4-d02c-4e52-b4d5-f0701f5c320b'
    core_filenames = [
        'FOR_PAIGE.md',
        'DEPLOYMENT_AND_TESTING_GUIDE.md',
        'IMPLEMENTATION_CHECKLIST.md',
        'WEEK_2_SPRINT_SUMMARY.md',
        'README.md'
    ]

    docs_result = supabase.table('documents').select('id, filename').eq('client_id', client_id).execute()

    if docs_result.data:
        for doc in docs_result.data:
            if doc['filename'] in core_filenames:
                # Mark as core
                supabase.table('documents').update({'is_core_document': True}).eq('id', doc['id']).execute()
                print(f"   ✅ Marked as core: {doc['filename']}")

    print(f"\n✅ Marked {len(core_filenames)} documents as core")

except Exception as e:
    print(f"❌ Error marking core documents: {e}")
    exit(1)

print()

# Step 3: Verify
print("Step 3: Verifying migration...")
try:
    result = supabase.table('documents').select('filename, is_core_document').eq('client_id', client_id).execute()

    if result.data:
        print("\nCore document status:")
        for doc in result.data:
            core_status = '✅ CORE' if doc.get('is_core_document') else '   Regular'
            print(f"  {core_status}: {doc['filename']}")

    core_count = sum(1 for doc in result.data if doc.get('is_core_document'))
    print(f"\n✅ Total core documents: {core_count}/{len(result.data)}")

except Exception as e:
    print(f"❌ Error verifying: {e}")

print()
print("=" * 80)
print("MIGRATION 023 COMPLETE")
print("=" * 80)
