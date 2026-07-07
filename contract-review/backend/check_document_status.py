#!/usr/bin/env python3
"""
Quick script to check document processing status
"""
from database import get_supabase
from datetime import datetime, timezone

supabase = get_supabase()

# Get all documents
result = supabase.table('documents').select('id, filename, processed, processing_status, created_at, processed_at').order('created_at', desc=True).limit(10).execute()

print("\n📋 Recent Documents Status:\n")
print(f"{'Filename':<40} {'Processed':<12} {'Status':<15} {'Created':<25} {'Processed At':<25}")
print("-" * 120)

for doc in result.data:
    filename = doc['filename'][:37] + '...' if len(doc['filename']) > 40 else doc['filename']
    processed = '✓ Yes' if doc['processed'] else '✗ No'
    status = doc.get('processing_status', 'N/A') or 'N/A'
    created = doc.get('created_at', 'N/A')[:22] if doc.get('created_at') else 'N/A'
    processed_at = doc.get('processed_at', 'N/A')[:22] if doc.get('processed_at') else 'N/A'

    print(f"{filename:<40} {processed:<12} {status:<15} {created:<25} {processed_at:<25}")

print("\n")

# Check for stuck documents
stuck = supabase.table('documents').select('*').eq('processed', False).execute()
if stuck.data:
    print(f"⚠️  Found {len(stuck.data)} unprocessed documents:")
    for doc in stuck.data:
        print(f"   - {doc['filename']} (ID: {doc['id']}, Status: {doc.get('processing_status', 'unknown')})")
else:
    print("✓ No unprocessed documents found")

print("\n")
