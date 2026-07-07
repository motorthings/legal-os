#!/usr/bin/env python3
"""
Sync contract_analysis created_at timestamps to match document upload dates
This makes the trend charts show realistic data spread over time
"""
from database import get_supabase
from logger_config import get_logger
from dotenv import load_dotenv
from datetime import timedelta
import random

load_dotenv()
logger = get_logger(__name__)

def sync_timestamps():
    """Update contract_analysis timestamps to match document dates with slight variation"""
    supabase = get_supabase()

    print("=" * 80)
    print("SYNC ANALYSIS TIMESTAMPS")
    print("=" * 80)
    print("\nUpdating contract_analysis timestamps to match document upload dates...\n")

    # Get all contract analyses with their document timestamps
    result = supabase.table('contract_analysis')\
        .select('id, document_id, documents!inner(uploaded_at, filename)')\
        .execute()

    analyses = result.data
    if not analyses:
        print("✅ No analyses found!")
        return

    print(f"📋 Found {len(analyses)} analysis record(s) to update\n")

    success_count = 0
    for i, analysis in enumerate(analyses, 1):
        filename = analysis['documents']['filename']
        doc_uploaded_at = analysis['documents']['uploaded_at']

        # Add a small random delay (5-60 minutes) to simulate processing time
        processing_minutes = random.randint(5, 60)

        try:
            # Parse the timestamp and add processing delay
            from datetime import datetime
            upload_time = datetime.fromisoformat(doc_uploaded_at.replace('Z', '+00:00'))
            analysis_time = upload_time + timedelta(minutes=processing_minutes)

            # Update the analysis timestamp
            supabase.table('contract_analysis').update({
                'created_at': analysis_time.isoformat()
            }).eq('id', analysis['id']).execute()

            print(f"[{i}/{len(analyses)}] Updated: {filename}")
            print(f"    Upload: {upload_time.strftime('%Y-%m-%d %H:%M')}")
            print(f"    Analysis: {analysis_time.strftime('%Y-%m-%d %H:%M')} (+{processing_minutes}min)")
            success_count += 1

        except Exception as e:
            print(f"  ❌ ERROR updating {filename}: {e}")
            logger.error(f"Failed to update {filename}: {e}", exc_info=True)

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✅ Successfully updated: {success_count}/{len(analyses)}")
    print("\n✅ Done! Analysis timestamps now spread across the past week.")

if __name__ == "__main__":
    try:
        sync_timestamps()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
