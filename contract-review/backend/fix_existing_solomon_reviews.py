#!/usr/bin/env python3
"""Fix existing solomon_reviews that should be 'deployed' but are still 'pending'"""
import os
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

print("🔍 Finding solomon_reviews that need status update...")

# Get all solomon_reviews with their extraction status
reviews = supabase.table('solomon_reviews')\
    .select('id, extraction_id, status, reviewed_by, deployed_at')\
    .execute()

print(f"Found {len(reviews.data)} total solomon_reviews")

# For each review, check if the extraction is approved
updates_needed = []
for review in reviews.data:
    extraction = supabase.table('interview_extractions')\
        .select('status, approved_at, approved_by')\
        .eq('id', review['extraction_id'])\
        .single()\
        .execute()

    if extraction.data and extraction.data.get('status') == 'approved':
        # If extraction is approved but review is not deployed
        if review.get('status') != 'deployed':
            updates_needed.append({
                'review_id': review['id'],
                'extraction_id': review['extraction_id'],
                'current_status': review.get('status'),
                'approved_by': extraction.data.get('approved_by'),
                'approved_at': extraction.data.get('approved_at')
            })

print(f"\n📊 Found {len(updates_needed)} reviews that need updating:")
for item in updates_needed:
    print(f"  - Review {item['review_id'][:8]}... (extraction: {item['extraction_id'][:8]}...)")
    print(f"    Current status: {item['current_status']} → Should be: deployed")

if updates_needed:
    print("\n🔧 Updating statuses...")
    for item in updates_needed:
        result = supabase.table('solomon_reviews')\
            .update({
                'status': 'deployed',
                'reviewed_by': item['approved_by'],
                'reviewed_at': item['approved_at'],
                'deployed_at': item['approved_at']
            })\
            .eq('id', item['review_id'])\
            .execute()

        print(f"  ✅ Updated review {item['review_id'][:8]}...")

    print(f"\n✅ Successfully updated {len(updates_needed)} solomon_reviews!")
else:
    print("\n✅ All solomon_reviews are already up to date!")
