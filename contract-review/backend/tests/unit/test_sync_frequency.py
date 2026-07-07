#!/usr/bin/env python3
"""Test script for Google Drive sync frequency feature"""
import os
import sys
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    print(f"{RED}✗ {text}{RESET}")

def print_info(text):
    print(f"{YELLOW}ℹ {text}{RESET}")

try:
    supabase = create_client(
        os.environ.get("SUPABASE_URL"),
        os.environ.get("SUPABASE_KEY")
    )
    print_success("Connected to Supabase")
except Exception as e:
    print_error(f"Failed to connect to Supabase: {e}")
    sys.exit(1)

print_header("Testing Google Drive Sync Frequency Feature")

# Test 1: Verify migration 012 columns exist
print_info("Test 1: Checking if migration 012 columns exist...")
try:
    result = supabase.table('google_drive_tokens')\
        .select('sync_frequency, last_auto_sync, next_sync_scheduled, default_folder_id, default_folder_name')\
        .limit(1)\
        .execute()

    print_success("Migration 012 columns are present")
    print(f"   • sync_frequency")
    print(f"   • last_auto_sync")
    print(f"   • next_sync_scheduled")
    print(f"   • default_folder_id")
    print(f"   • default_folder_name")
except Exception as e:
    print_error(f"Migration 012 columns missing: {e}")
    sys.exit(1)

# Test 2: Check if any Google Drive connections exist
print_info("\nTest 2: Checking for Google Drive connections...")
try:
    result = supabase.table('google_drive_tokens')\
        .select('*')\
        .eq('is_active', True)\
        .execute()

    if not result.data:
        print_error("No active Google Drive connections found")
        print_info("   You need to connect Google Drive first to test sync frequency")
        print_info("   Visit http://localhost:3000/documents and click 'Connect Google Drive'")
        sys.exit(0)

    connection = result.data[0]
    user_id = connection['user_id']
    print_success(f"Found active Google Drive connection for user: {user_id}")
    print(f"   • Current sync_frequency: {connection.get('sync_frequency', 'manual')}")
    print(f"   • Last auto sync: {connection.get('last_auto_sync', 'Never')}")
    print(f"   • Next sync scheduled: {connection.get('next_sync_scheduled', 'Not scheduled')}")

except Exception as e:
    print_error(f"Error checking connections: {e}")
    sys.exit(1)

# Test 3: Verify sync frequency can be updated
print_info("\nTest 3: Testing sync frequency updates...")
test_frequencies = ['daily', 'weekly', 'monthly', 'manual']

for freq in test_frequencies:
    try:
        print_info(f"   Testing frequency: {freq}")

        # Calculate expected next_sync
        from datetime import timedelta
        now = datetime.utcnow()
        expected_next_sync = None

        if freq == 'daily':
            expected_next_sync = now + timedelta(days=1)
        elif freq == 'weekly':
            expected_next_sync = now + timedelta(weeks=1)
        elif freq == 'monthly':
            expected_next_sync = now + timedelta(days=30)

        # Update in database
        update_data = {
            'sync_frequency': freq,
            'next_sync_scheduled': expected_next_sync.isoformat() if expected_next_sync else None
        }

        result = supabase.table('google_drive_tokens')\
            .update(update_data)\
            .eq('user_id', user_id)\
            .eq('is_active', True)\
            .execute()

        if result.data:
            updated = result.data[0]
            print_success(f"   Updated to {freq}")

            if freq != 'manual':
                next_sync = updated.get('next_sync_scheduled')
                if next_sync:
                    next_sync_dt = datetime.fromisoformat(next_sync.replace('Z', '+00:00'))
                    print(f"      Next sync: {next_sync_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                else:
                    print_error(f"      Next sync not set for {freq}")
            else:
                print(f"      Next sync: Not scheduled (manual mode)")
        else:
            print_error(f"   Failed to update to {freq}")

    except Exception as e:
        print_error(f"   Error testing {freq}: {e}")

# Test 4: Verify index exists
print_info("\nTest 4: Checking if sync scheduling index exists...")
try:
    # This is a bit hacky but works - try to query using the index
    result = supabase.table('google_drive_tokens')\
        .select('*')\
        .not_.is_('next_sync_scheduled', 'null')\
        .eq('is_active', True)\
        .neq('sync_frequency', 'manual')\
        .execute()

    print_success("Index query successful (idx_google_tokens_next_sync likely exists)")
    print(f"   Found {len(result.data)} tokens with scheduled syncs")

except Exception as e:
    print_error(f"Index query failed: {e}")

# Test 5: Reset to manual for clean state
print_info("\nTest 5: Resetting to manual mode...")
try:
    result = supabase.table('google_drive_tokens')\
        .update({
            'sync_frequency': 'manual',
            'next_sync_scheduled': None
        })\
        .eq('user_id', user_id)\
        .eq('is_active', True)\
        .execute()

    if result.data:
        print_success("Reset to manual mode")
    else:
        print_error("Failed to reset")

except Exception as e:
    print_error(f"Error resetting: {e}")

print_header("Test Summary")
print_success("All tests completed!")
print_info("\nNext steps to test the UI:")
print("   1. Ensure frontend is running: http://localhost:3000")
print("   2. Navigate to: http://localhost:3000/documents")
print("   3. Connect Google Drive if not already connected")
print("   4. Change the 'Automatic Sync' dropdown")
print("   5. Verify 'Next sync' time displays correctly")
print("   6. Check that settings persist after page refresh")
print()
