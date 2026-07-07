#!/usr/bin/env python3
"""
Quick script to check if quick prompts were generated
"""
import os
from supabase import create_client

# Initialize Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://iyugbpnxfbhqjxrvmnij.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_KEY:
    print("❌ SUPABASE_SERVICE_ROLE_KEY not set")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("🔍 Checking Quick Prompts...\n")

# Get total prompts
all_prompts = supabase.table('user_prompts').select('*').execute()
total_prompts = len(all_prompts.data)

# Get auto-generated prompts
auto_prompts = supabase.table('user_prompts').select('*').eq('is_auto_generated', True).execute()
auto_generated_count = len(auto_prompts.data)

print(f"📊 Total Prompts: {total_prompts}")
print(f"🤖 Auto-Generated: {auto_generated_count}")
print(f"✍️  User-Created: {total_prompts - auto_generated_count}\n")

if auto_generated_count > 0:
    print("✅ Auto-generated prompts found!\n")
    print("Recent auto-generated prompts:")
    print("-" * 80)

    # Show latest 10 auto-generated prompts
    for prompt in auto_prompts.data[:10]:
        user_id = prompt.get('user_id', 'N/A')
        title = prompt.get('title', 'N/A')
        category = prompt.get('category', 'N/A')
        metadata = prompt.get('metadata', {})
        function = metadata.get('function', 'N/A') if isinstance(metadata, dict) else 'N/A'

        print(f"User: {user_id[:8]}... | Category: {category:15} | Function: {function[:30]:30}")
        print(f"  → {title[:70]}")
        print()
else:
    print("⚠️  No auto-generated prompts found yet.")
    print("\nPossible reasons:")
    print("1. Approval hasn't been processed yet")
    print("2. Migration didn't run (check if columns exist)")
    print("3. Error during generation (check logs)")

    # Check if columns exist
    print("\n🔍 Checking if migration columns exist...")
    try:
        test = supabase.table('user_prompts').select('is_auto_generated, metadata').limit(1).execute()
        print("✅ Columns exist (migration successful)")
    except Exception as e:
        print(f"❌ Columns missing: {e}")

# Get recent extractions to see what was approved
print("\n" + "="*80)
print("📋 Recent Approved Extractions:")
print("="*80)

extractions = supabase.table('interview_extractions')\
    .select('id, user_id, status, created_at')\
    .eq('status', 'approved')\
    .order('created_at', desc=True)\
    .limit(5)\
    .execute()

if extractions.data:
    for ext in extractions.data:
        ext_id = ext['id'][:8]
        user_id = ext.get('user_id', 'N/A')[:8] if ext.get('user_id') else 'N/A'
        created = ext['created_at'][:10]
        status = ext.get('status', 'N/A')
        print(f"  {ext_id}... | User: {user_id}... | Status: {status} | Date: {created}")
else:
    print("  No deployed extractions found")

print("\n" + "="*80)
